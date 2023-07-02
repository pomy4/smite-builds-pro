import datetime
import email.utils
import functools
import hashlib
import hmac
import json
import typing as t

import bottle
import pydantic as pd
import pydantic.types as pdt

from backend.config import get_webapi_config
from backend.webapi.exceptions import MyValidationError
from backend.webapi.get_builds import WhereStrat, get_builds
from backend.webapi.get_options import get_options
from backend.webapi.loggers import (
    cache_logger,
    error_logger,
    setup_auto_fixes_logger,
    setup_cache_logger,
    setup_error_logger,
)
from backend.webapi.models import STR_MAX_LEN, db
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


def setup_logging() -> None:
    setup_auto_fixes_logger()
    setup_cache_logger()
    setup_error_logger()


@app.hook("before_request")
def before() -> None:
    db.connect()


@app.hook("after_request")
def after() -> None:
    db.close()


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
                error_logger.warning(ret)
                # All expected errors return plain strings,
                # so this decorator is also used to fix the Content-Type.
                bottle.response.content_type = "text/plain"
            return ret
        except Exception:
            error_logger.exception("Internal Server Error")
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
        cache_logger.info(f"IfModifiedSince is invalid: {if_modified_since_s}")
        return False

    if if_modified_since.tzinfo is None:
        cache_logger.info(f"IfModifiedSince with -0000 tz: {if_modified_since_s}")
        if_modified_since = if_modified_since.replace(tzinfo=datetime.timezone.utc)

    if last_modified > if_modified_since:
        return False
    elif last_modified == if_modified_since:
        return True

    cache_logger.info(
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
    season: t.Annotated[list[MyInt] | None, WhereStrat.match]
    league: t.Annotated[list[MyStr] | None, WhereStrat.match]
    phase: t.Annotated[list[MyStr] | None, WhereStrat.match]
    date: t.Annotated[tuple[datetime.date, datetime.date] | None, WhereStrat.range]
    game_i: t.Annotated[list[MyInt] | None, WhereStrat.match]
    game_length: t.Annotated[
        tuple[datetime.time, datetime.time] | None, WhereStrat.range
    ]
    win: t.Annotated[list[bool] | None, WhereStrat.match]
    kda_ratio: t.Annotated[tuple[float, float] | None, WhereStrat.range]
    kills: t.Annotated[tuple[int, int] | None, WhereStrat.range]
    deaths: t.Annotated[tuple[int, int] | None, WhereStrat.range]
    assists: t.Annotated[tuple[int, int] | None, WhereStrat.range]
    role: t.Annotated[list[MyStr] | None, WhereStrat.match]
    player1: t.Annotated[list[MyStr] | None, WhereStrat.match]
    god1: t.Annotated[list[MyStr] | None, WhereStrat.match]
    team1: t.Annotated[list[MyStr] | None, WhereStrat.match]
    player2: t.Annotated[list[MyStr] | None, WhereStrat.match]
    god2: t.Annotated[list[MyStr] | None, WhereStrat.match]
    team2: t.Annotated[list[MyStr] | None, WhereStrat.match]
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
    return None


def what_time_is_it() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def format_last_checked(d: datetime.datetime) -> str:
    return d.strftime("%d %b %Y %I:%M:%S %p (%Z)")
