import json
import functools
import os
import hmac
import hashlib
import datetime
import traceback
from typing import List, Optional, Annotated

from bottle import Bottle, request, response
import pydantic
from pydantic .types import *
from dotenv import load_dotenv

from models import (STR_MAX_LEN, MyError, db, get_last_modified, update_last_modified,
    get_last_checked, update_last_checked, get_match_ids, post_builds, get_options, get_builds, WhereStrat)

Mystr = constr(min_length=1, max_length=STR_MAX_LEN, strict=False)
Myint = conint(ge=0, strict=False)
Myfloat = confloat(ge=0., strict=False)
Myitem = conlist(min_items=2, max_items=2, item_type=Mystr)

app = Bottle()
app.config['json.enable'] = False

def what_time_is_it():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

def format_last_checked(d):
    return d.strftime('%d %b %Y %I:%M:%S %p (%Z)')

@app.hook('before_request')
def before():
    db.connect()

@app.hook('after_request')
def after():
    db.close()

def cache_with_last_modified(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not (last_modified := get_last_modified()):
            return func(*args, **kwargs)
        last_modified = last_modified.data
        if if_modified_since := request.get_header('If-Modified-Since'):
            try:
                if_modified_since = datetime.datetime.fromisoformat(if_modified_since)
                if last_modified < if_modified_since:
                    raise ValueError('Request is from the future.')
                elif last_modified == if_modified_since:
                    response.status = 304
                    return
            # Log this, but don't reject the request over it.
            except ValueError:
                traceback.print_exc()
        result = func(*args, **kwargs)
        if response.status_code < 400:
            response.add_header('Cache-Control', 'public')
            response.add_header('Last-modified', last_modified.isoformat())
        return result
    return wrapper

def verify_integrity(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not (key_hex := os.getenv('HMAC_KEY_HEX')):
            response.status = 501
            return 'HMAC secret key isn\'t set on the server.'
        key = bytearray.fromhex(key_hex)

        header_name = 'X-HMAC-DIGEST-HEX'
        if not (digest_header := request.get_header(header_name)):
            response.status = 400
            return f'HMAC digest was not included in the {header_name} header.'

        hmac_obj = hmac.new(key, request.body.read(), hashlib.sha256)
        digest_body = hmac_obj.hexdigest()
        if not hmac.compare_digest(digest_header, digest_body):
            response.status = 403
            return 'Wrong HMAC digest!'

        return func(*args, **kwargs)
    return wrapper

def validate_request_body(Schema):
    def outer_wrapper(func):
        @functools.wraps(func)
        def inner_wrapper():
            try:
                body_bytes = request.body.read()
                body_str = body_bytes.decode('utf-8')
                body_json = json.loads(body_str)
                body_dict = Schema.parse_obj(body_json).dict()
            except (UnicodeDecodeError, json.JSONDecodeError, pydantic.ValidationError) as e:
                response.status = 400
                return str(e)
            body = body_dict.get('__root__', body_dict)
            return func(body)
        return inner_wrapper
    return outer_wrapper

def jsonify(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if response.status_code < 400 and result is not None:
            result = json.dumps(result, indent=2)
            response.content_type = 'application/json'
        return result
    return wrapper

class PhasesSchema(pydantic.BaseModel):
    __root__: List[Mystr]

@app.post('/api/phases')
@validate_request_body(PhasesSchema)
@jsonify
def phases(phases):
    return [get_match_ids(phase) for phase in phases]

class PostBuildSchema(pydantic.BaseModel):
    season: Optional[Mystr]
    league: Mystr
    phase: Mystr
    year: Optional[Myint]
    month: Myint
    day: Myint
    match_id: Myint
    game_i: Myint
    win: StrictBool
    hours: Myint
    minutes: Myint
    seconds: Myint
    kda_ratio: Myfloat
    kills: Myint
    deaths: Myint
    assists: Myint
    role: Mystr
    player1: Mystr
    god1: Mystr
    team1: Mystr
    player2: Mystr
    god2: Mystr
    team2: Mystr
    relics: conlist(Myitem, min_items=0, max_items=2)
    items: conlist(Myitem, min_items=0, max_items=6)

class PostBuildsSchema(pydantic.BaseModel):
    __root__: List[PostBuildSchema]

@app.post('/api/builds')
@verify_integrity
@validate_request_body(PostBuildsSchema)
def builds_post(builds):
    if not builds:
        response.status = 204
    else:
        try:
            response.status = 201
            post_builds(builds)
        except MyError as e:
            response.status = 400
            return str(e)

    now = what_time_is_it()
    update_last_checked(format_last_checked(now))
    if builds:
        update_last_modified(now)

@app.get('/api/options')
@cache_with_last_modified
@jsonify
def options():
    return get_options()

@app.get('/api/last_check')
def last_check():
    return last_checked.data if (last_checked := get_last_checked()) else 'unknown'

class GetBuildsSchema(pydantic.BaseModel):
    page: conlist(Myint, min_items=0, max_items=1)
    season: Annotated[Optional[List[Myint]], WhereStrat.match]
    league: Annotated[Optional[List[Mystr]], WhereStrat.match]
    phase: Annotated[Optional[List[Mystr]], WhereStrat.match]
    date: Annotated[Optional[conlist(datetime.date, min_items=2, max_items=2)], WhereStrat.range]
    game_i: Annotated[Optional[List[Myint]], WhereStrat.match]
    game_length: Annotated[Optional[conlist(datetime.time, min_items=2, max_items=2)], WhereStrat.range]
    win: Annotated[Optional[List[bool]], WhereStrat.match]
    kda_ratio: Annotated[Optional[conlist(Myfloat, min_items=2, max_items=2)], WhereStrat.range]
    kills: Annotated[Optional[conlist(Myint, min_items=2, max_items=2)], WhereStrat.range]
    deaths: Annotated[Optional[conlist(Myint, min_items=2, max_items=2)], WhereStrat.range]
    assists: Annotated[Optional[conlist(Myint, min_items=2, max_items=2)], WhereStrat.range]
    role: Annotated[Optional[List[Mystr]], WhereStrat.match]
    player1: Annotated[Optional[List[Mystr]], WhereStrat.match]
    god1: Annotated[Optional[List[Mystr]], WhereStrat.match]
    team1: Annotated[Optional[List[Mystr]], WhereStrat.match]
    player2: Annotated[Optional[List[Mystr]], WhereStrat.match]
    god2: Annotated[Optional[List[Mystr]], WhereStrat.match]
    team2: Annotated[Optional[List[Mystr]], WhereStrat.match]
    relic: Optional[List[Mystr]]
    item: Optional[List[Mystr]]

@app.get('/api/builds')
@cache_with_last_modified
@jsonify
def builds_get():
    form_dict = request.query.decode()
    dict_with_lists = {key: form_dict.getall(key) for key in form_dict.keys()}

    try:
        model = GetBuildsSchema.parse_obj(dict_with_lists)
    except (pydantic.ValidationError) as e:
        response.status = 400
        return str(e)

    return get_builds(model)

if __name__ == '__main__':
    load_dotenv('../.env')
    app.run(host='localhost', port=8080, reloader=True, debug=True)
