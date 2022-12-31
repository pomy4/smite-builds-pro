import datetime
import email.utils
import functools
import hashlib
import hmac
import json
import os
from typing import TYPE_CHECKING, Annotated, Any, Callable, Optional, Type

import bottle
import pydantic as pd
import pydantic.types as pdt

import be.models
import shared
from be.models import MyError, WhereStrat

# --------------------------------------------------------------------------------------
# APP & LOGGING & HOOKS & DECORATORS
# --------------------------------------------------------------------------------------


app = bottle.Bottle()
app.config["json.enable"] = False


def setup_logging() -> None:
    be.models.setup_auto_fixes_logger()
    be.models.setup_cache_logger()
    be.models.setup_error_logger()


@app.hook("before_request")
def before() -> None:
    be.models.db.connect()


@app.hook("after_request")
def after() -> None:
    be.models.db.close()


@app.error(500)
def error500(error: bottle.HTTPError) -> str:
    """Send plain string instead of a html page for unexpected exceptions."""
    bottle.response.content_type = "text/plain"
    return f"{error.body}\n{error.traceback}" if bottle.DEBUG else error.body


def log_errors(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            ret = func(*args, **kwargs)
            if bottle.response.status_code >= 400:
                be.models.error_logger.warning(ret)
                # All expected errors return plain strings,
                # so this decorator is also used to fix the Content-Type.
                bottle.response.content_type = "text/plain"
            return ret
        except Exception:
            be.models.error_logger.exception("Internal Server Error")
            # And also to remove caching from 500 responses
            # (not sure if they can even be cached, but just to make sure).
            if "Last-Modified" in bottle.response.headers:
                del bottle.response.headers["Last-Modified"]
            raise

    return wrapper


def verify_integrity(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not (key_hex := os.getenv(shared.HMAC_KEY_HEX)):
            bottle.response.status = 501
            return "HMAC secret key isn't set on the server"
        key = bytearray.fromhex(key_hex)

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


def validate_request_body(model: Type[pd.BaseModel]) -> Callable:
    def outer_wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        def inner_wrapper() -> Any:
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


def cache_with_last_modified(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        last_modified = be.models.get_last_modified()
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
        be.models.cache_logger.info(
            f"IfModifiedSince is invalid: {if_modified_since_s}"
        )
        return False

    if if_modified_since.tzinfo is None:
        be.models.cache_logger.info(
            f"IfModifiedSince with -0000 tz: {if_modified_since_s}"
        )
        if_modified_since = if_modified_since.replace(tzinfo=datetime.timezone.utc)

    if last_modified > if_modified_since:
        return False
    elif last_modified == if_modified_since:
        return True

    be.models.cache_logger.info(
        f"IfModifiedSince from the future: {if_modified_since_s} > "
        + f"LastModified: {repr(last_modified)}"
    )
    return False


def format_rfc(my_datetime: datetime.datetime) -> str:
    return email.utils.format_datetime(my_datetime, usegmt=True)


def jsonify(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if bottle.response.status_code < 400 and result is not None:
            result = json.dumps(result, indent=2, cls=BytesEncoder)
            bottle.response.content_type = "application/json"
        return result

    return wrapper


class BytesEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
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
def get_options() -> dict:
    return be.models.get_options()


@app.get("/api/last_check")
@log_errors
def get_last_check() -> str:
    if last_checked := be.models.get_last_checked():
        return last_checked
    else:
        return "unknown"


if TYPE_CHECKING:
    MyStr = str
    MyInt = int
    MyFloat = float
else:
    MyStr = pdt.constr(min_length=1, max_length=be.models.STR_MAX_LEN, strict=False)
    MyInt = pdt.conint(ge=0, strict=False)
    MyFloat = pdt.confloat(ge=0.0, strict=False)


class GetBuildsRequest(pd.BaseModel):
    page: tuple[MyInt]
    season: Annotated[Optional[list[MyInt]], WhereStrat.match]
    league: Annotated[Optional[list[MyStr]], WhereStrat.match]
    phase: Annotated[Optional[list[MyStr]], WhereStrat.match]
    date: Annotated[Optional[tuple[datetime.date, datetime.date]], WhereStrat.range]
    game_i: Annotated[Optional[list[MyInt]], WhereStrat.match]
    game_length: Annotated[
        Optional[tuple[datetime.time, datetime.time]], WhereStrat.range
    ]
    win: Annotated[Optional[list[bool]], WhereStrat.match]
    kda_ratio: Annotated[Optional[tuple[float, float]], WhereStrat.range]
    kills: Annotated[Optional[tuple[int, int]], WhereStrat.range]
    deaths: Annotated[Optional[tuple[int, int]], WhereStrat.range]
    assists: Annotated[Optional[tuple[int, int]], WhereStrat.range]
    role: Annotated[Optional[list[MyStr]], WhereStrat.match]
    player1: Annotated[Optional[list[MyStr]], WhereStrat.match]
    god1: Annotated[Optional[list[MyStr]], WhereStrat.match]
    team1: Annotated[Optional[list[MyStr]], WhereStrat.match]
    player2: Annotated[Optional[list[MyStr]], WhereStrat.match]
    god2: Annotated[Optional[list[MyStr]], WhereStrat.match]
    team2: Annotated[Optional[list[MyStr]], WhereStrat.match]
    relic: Optional[list[MyStr]]
    item: Optional[list[MyStr]]


@app.get("/api/builds")
@log_errors
@cache_with_last_modified
@jsonify
def get_builds() -> Any:
    form_dict = bottle.request.query.decode()
    dict_with_lists = {key: form_dict.getall(key) for key in form_dict.keys()}

    try:
        builds_query = GetBuildsRequest.parse_obj(dict_with_lists)
    except pd.ValidationError as e:
        bottle.response.status = 400
        return str(e)

    return be.models.get_builds(builds_query)


# --------------------------------------------------------------------------------------
# UPDATER ROUTES
# --------------------------------------------------------------------------------------


class PhasesRequest(pd.BaseModel):
    __root__: list[MyStr]


@app.post("/api/phases")
@log_errors
@validate_request_body(PhasesRequest)
@jsonify
def post_phases(phases: list[MyStr]) -> list[list[int]]:
    return [be.models.get_match_ids(phase) for phase in phases]


MyItem = tuple[MyStr, MyStr]
if TYPE_CHECKING:
    MyRelics = list[MyItem]
    MyItems = list[MyItem]
else:
    MyRelics = pdt.conlist(MyItem, min_items=0, max_items=2)
    MyItems = pdt.conlist(MyItem, min_items=0, max_items=6)


class PostBuildRequest(pd.BaseModel):
    season: Optional[MyStr]
    league: MyStr
    phase: MyStr
    year: Optional[MyInt]
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
    __root__: list[PostBuildRequest]


@app.post("/api/builds")
@log_errors
@verify_integrity
@validate_request_body(PostBuildsRequest)
def post_builds(builds: list[PostBuildRequest]) -> Optional[str]:
    if not builds:
        bottle.response.status = 204
    else:
        try:
            bottle.response.status = 201
            be.models.post_builds(builds)
        except MyError as e:
            bottle.response.status = 400
            return str(e)

    now = what_time_is_it()
    be.models.update_last_checked(format_last_checked(now))
    if builds:
        be.models.update_last_modified(now)
    return None


def what_time_is_it() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def format_last_checked(d: datetime.datetime) -> str:
    return d.strftime("%d %b %Y %I:%M:%S %p (%Z)")
