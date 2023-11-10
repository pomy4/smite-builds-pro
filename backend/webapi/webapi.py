import datetime
import email.utils
import functools
import hashlib
import hmac
import json
import logging
import sys
import typing as t

import bottle
import pydantic as pd
import pydantic.types as pdt

from backend.config import get_webapi_config
from backend.shared import setup_logging
from backend.webapi.exceptions import MyValidationError
from backend.webapi.get_builds import WhereStrat, get_builds
from backend.webapi.get_options import get_options
from backend.webapi.models import STR_MAX_LEN, db_session
from backend.webapi.post_builds.auto_fixes_logger import setup_auto_fixes_logging
from backend.webapi.post_builds.post_builds import post_builds
from backend.webapi.simple_queries import (
    get_last_checked,
    get_last_modified,
    get_match_ids,
    update_last_checked,
    update_last_modified,
)

# --------------------------------------------------------------------------------------
# APP & LOGGING & HOOKS & DECORATORS
# --------------------------------------------------------------------------------------


app = bottle.Bottle()
app.config["json.enable"] = False

logger = logging.getLogger(__name__)
ACCESS_LOG_NAME = "access"
access_logger = logging.getLogger(ACCESS_LOG_NAME)


def setup_webapi_logging() -> None:
    setup_logging("webapi")
    setup_logging(ACCESS_LOG_NAME, is_root=False)
    setup_auto_fixes_logging()


# @app.hook("before_request")
# def before() -> None:
# Currently not needed.


@app.hook("after_request")
def after() -> None:
    # Also calls close, which also calls rollback.
    db_session.remove()
    log_access()


def log_access() -> None:
    """
    Logs accesess to the access log using the Apache Combined Log Format.

    Bottle doesn't provide an easy way to log accesses. It does log accesses to stderr
    using something in the standard library, but I think it does that only in the case
    when the run method is used.

    This means the cleanest solution would be to write/use a WSGI middleware, but using
    the after_request hook should be less work, though it has a few disadvantages.

    One of them is that bottle does some sort of unicode check on the path of the
    request in the Bottle._handle() method, and if the request doesn't pass it, it will
    not be even started, and thus it will not be logged here.

    Some more issues are described in the comments of this method.

    Another option would be to write a Bottle plugin, but the outcome would be almost
    the same as the after_request hook, except 404 Not Found and 405 Invalid Method
    responses would also not be logged, since these are checked in route.match(), which
    is called before route.call() in Bottle._handle(), and plugins are basically
    decorators around route.call().
    """
    req, resp = bottle.request, bottle.response

    # REMOTE_ADDR is always the address of a PythonAnywhere load balancer,
    # but bottle.request.remote_addr also checks HTTP_X_FORWARDED_FOR,
    # so we don't have to do anything extra here.
    host = req.remote_addr or "-"

    identity = user = "-"

    now = datetime.datetime.now().astimezone()
    now_str = now.strftime("%d/%b/%Y:%H:%M:%S %z")

    protocol = req.environ.get("SERVER_PROTOCOL", "-")
    method_url_and_protocol = f"{req.method} {req.url} {protocol}"

    # Slightly hackish way to get response status code:
    _, e, _ = sys.exc_info()
    if e is None:
        # The route ended without an exception, hence the status
        # code can be retrieved from the global response object.
        status_code = resp.status_code
    else:
        # The route has ended with an exception - bottle updates the global response
        # object with the status code from the exception, if it is a bottle specific
        # exception, or with a 500, if it is not, but it does this right after this
        # hook finishes, so here we have to do it ourselves.
        if isinstance(e, bottle.HTTPResponse):
            status_code = e.status_code
        else:
            status_code = 500

    # Bottle computes content-length after this hook, so we have no easy way to get it.
    size = "-"

    referer = req.headers.get("Referer", "-")

    user_agent = req.headers.get("User-Agent", "-")

    msg1 = f'{host} {identity} {user} [{now_str}] "{method_url_and_protocol}"'
    msg2 = f' {status_code} {size} "{referer}" "{user_agent}"'
    access_logger.info(msg1 + msg2)


@app.error(500)
def error500(error: bottle.HTTPError) -> str:
    """Send plain string instead of a html page for unexpected exceptions."""
    bottle.response.content_type = "text/plain"
    return f"{error.body}\n{error.traceback}" if bottle.DEBUG else error.body


def log_errors(func: t.Callable) -> t.Callable:
    @functools.wraps(func)
    def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        try:
            ret = func(*args, **kwargs)
            if bottle.response.status_code >= 400:
                logger.warning(ret)
                # All expected errors return plain strings,
                # so this decorator is also used to fix the Content-Type.
                bottle.response.content_type = "text/plain"
            return ret
        except Exception:
            logger.exception("Internal Server Error")
            # And also to remove caching from 500 responses
            # (not sure if they can even be cached, but just to make sure).
            if "Last-Modified" in bottle.response.headers:
                del bottle.response.headers["Last-Modified"]
            raise

    return wrapper


def verify_integrity(func: t.Callable) -> t.Callable:
    @functools.wraps(func)
    def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        key = bytearray.fromhex(get_webapi_config().hmac_key_hex)

        header_name = "X-HMAC-DIGEST-HEX"
        if not (digest_header := bottle.request.get_header(header_name)):
            bottle.response.status = 400
            return f"HMAC digest was not included in the {header_name} header"

        hmac_obj = hmac.new(key, bottle.request.body.read(), hashlib.sha256)
        digest_body = hmac_obj.hexdigest()
        if not hmac.compare_digest(digest_header, digest_body):
            bottle.response.status = 403
            return "Wrong HMAC digest"

        return func(*args, **kwargs)

    return wrapper


def validate_request_body(model: type[pd.BaseModel]) -> t.Callable:
    def outer_wrapper(func: t.Callable) -> t.Callable:
        @functools.wraps(func)
        def inner_wrapper() -> t.Any:
            try:
                body_bytes: bytes = bottle.request.body.read()
                body_str = body_bytes.decode("utf-8")
                body_json = json.loads(body_str)
                body = model.parse_obj(body_json)
                body = getattr(body, "__root__", body)
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                pd.ValidationError,
            ) as e:
                bottle.response.status = 400
                return str(e)
            return func(body)

        return inner_wrapper

    return outer_wrapper


def cache_with_last_modified(func: t.Callable) -> t.Callable:
    @functools.wraps(func)
    def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        last_modified = get_last_modified()
        if last_modified is None:
            return func(*args, **kwargs)
        if if_modified_since_s := bottle.request.get_header("If-Modified-Since"):
            if is_cached(last_modified, if_modified_since_s):
                bottle.response.status = 304
                return
        result = func(*args, **kwargs)
        if bottle.response.status_code < 400:
            bottle.response.add_header("Last-Modified", format_rfc(last_modified))
            # This is also needed I think, since otherwise browsers try to guess
            # on their own whether the cached value is fresh or stale
            # instead of always revalidating with If-Modified-Since.
            bottle.response.add_header("Cache-Control", "no-cache")
        return result

    return wrapper


def is_cached(last_modified: datetime.datetime, if_modified_since_s: str) -> bool:
    try:
        if_modified_since = email.utils.parsedate_to_datetime(if_modified_since_s)
    except ValueError:
        logger.info(f"IfModifiedSince is invalid: {if_modified_since_s}")
        return False

    if if_modified_since.tzinfo is None:
        logger.info(f"IfModifiedSince with -0000 tz: {if_modified_since_s}")
        if_modified_since = if_modified_since.replace(tzinfo=datetime.timezone.utc)

    if last_modified > if_modified_since:
        return False
    elif last_modified == if_modified_since:
        return True

    logger.info(
        f"IfModifiedSince from the future: {if_modified_since_s} > "
        + f"LastModified: {repr(last_modified)}"
    )
    return False


def format_rfc(my_datetime: datetime.datetime) -> str:
    return email.utils.format_datetime(my_datetime, usegmt=True)


def jsonify(func: t.Callable) -> t.Callable:
    @functools.wraps(func)
    def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        result = func(*args, **kwargs)
        if bottle.response.status_code < 400 and result is not None:
            result = json.dumps(result, indent=2, cls=BytesEncoder)
            bottle.response.content_type = "application/json"
        return result

    return wrapper


class BytesEncoder(json.JSONEncoder):
    def default(self, obj: t.Any) -> t.Any:
        if isinstance(obj, bytes):
            return obj.decode("ascii")
        return json.JSONEncoder.default(self, obj)


# --------------------------------------------------------------------------------------
# FRONTEND ROUTES
# --------------------------------------------------------------------------------------


@app.get("/api/options")
@log_errors
@cache_with_last_modified
@jsonify
def get_options_endpoint() -> dict:
    return get_options()


@app.get("/api/last_check")
@log_errors
@jsonify
def get_last_check_endpoint() -> dict:
    value, tooltip = get_last_checked()
    return {"value": value or "unknown", "tooltip": tooltip or "Unknown"}


if t.TYPE_CHECKING:
    MyStr = str
    MyInt = int
    MyFloat = float
else:
    MyStr = pdt.constr(min_length=1, max_length=STR_MAX_LEN, strict=False)
    MyInt = pdt.conint(ge=0, strict=False)
    MyFloat = pdt.confloat(ge=0.0, strict=False)


class GetBuildsRequest(pd.BaseModel):
    page: tuple[MyInt]
    season: t.Annotated[list[MyInt] | None, WhereStrat.MATCH]
    league: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    phase: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    date: t.Annotated[tuple[datetime.date, datetime.date] | None, WhereStrat.RANGE]
    game_i: t.Annotated[list[MyInt] | None, WhereStrat.MATCH]
    game_length: t.Annotated[
        tuple[datetime.time, datetime.time] | None, WhereStrat.RANGE
    ]
    win: t.Annotated[list[bool] | None, WhereStrat.MATCH]
    kda_ratio: t.Annotated[tuple[float, float] | None, WhereStrat.RANGE]
    kills: t.Annotated[tuple[int, int] | None, WhereStrat.RANGE]
    deaths: t.Annotated[tuple[int, int] | None, WhereStrat.RANGE]
    assists: t.Annotated[tuple[int, int] | None, WhereStrat.RANGE]
    role: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    god1: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    player1: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    team1: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    god2: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    player2: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    team2: t.Annotated[list[MyStr] | None, WhereStrat.MATCH]
    relic: list[MyStr] | None
    item: list[MyStr] | None


@app.get("/api/builds")
@log_errors
@cache_with_last_modified
@jsonify
def get_builds_endpoint() -> t.Any:
    form_dict = bottle.request.query.decode()
    dict_with_lists = {key: form_dict.getall(key) for key in form_dict.keys()}

    try:
        builds_query = GetBuildsRequest.parse_obj(dict_with_lists)
    except pd.ValidationError as e:
        bottle.response.status = 400
        return str(e)

    return get_builds(builds_query)


# --------------------------------------------------------------------------------------
# UPDATER ROUTES
# --------------------------------------------------------------------------------------


class PhasesRequest(pd.BaseModel):
    __root__: list[MyStr]


@app.post("/api/phases")
@log_errors
@validate_request_body(PhasesRequest)
@jsonify
def post_phases_endpoint(phases: list[MyStr]) -> list[list[int]]:
    return [get_match_ids(phase) for phase in phases]


MyItem = tuple[MyStr, MyStr]
if t.TYPE_CHECKING:
    MyRelics = list[MyItem]
    MyItems = list[MyItem]
else:
    MyRelics = pdt.conlist(MyItem, min_items=0, max_items=2)
    MyItems = pdt.conlist(MyItem, min_items=0, max_items=6)


class PostBuildRequest(pd.BaseModel):
    season: MyStr | None
    league: MyStr
    phase: MyStr
    year: MyInt | None
    month: MyInt
    day: MyInt
    match_id: MyInt
    game_i: MyInt
    win: pdt.StrictBool
    hours: MyInt
    minutes: MyInt
    seconds: MyInt
    kda_ratio: MyFloat
    kills: MyInt
    deaths: MyInt
    assists: MyInt
    role: MyStr
    player1: MyStr
    god1: MyStr
    team1: MyStr
    player2: MyStr
    god2: MyStr
    team2: MyStr
    relics: MyRelics
    items: MyItems


class PostBuildsRequest(pd.BaseModel):
    builds: list[PostBuildRequest]
    last_checked_tooltip: str


@app.post("/api/builds")
@log_errors
@verify_integrity
@validate_request_body(PostBuildsRequest)
def post_builds_endpoint(request: PostBuildsRequest) -> str | None:
    if not request.builds:
        bottle.response.status = 204
    else:
        try:
            bottle.response.status = 201
            post_builds(request.builds)
        except MyValidationError as e:
            bottle.response.status = 400
            return str(e)

    now = what_time_is_it()
    update_last_checked(format_last_checked(now), request.last_checked_tooltip)
    if request.builds:
        update_last_modified(now)
    db_session.commit()
    return None


def what_time_is_it() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def format_last_checked(d: datetime.datetime) -> str:
    return d.strftime("%d %b %Y %I:%M:%S %p (%Z)")
