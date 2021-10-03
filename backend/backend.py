import json
import functools
import os
import hmac
import hashlib
import datetime
import traceback

from bottle import Bottle, request, response
from bottle_errorsrest import ErrorsRestPlugin
import pydantic
from pydantic .types import *
from typing import List, Optional
from dotenv import load_dotenv

from models import STR_MAX_LEN, MyError, db, get_match_ids, post_builds, get_options, get_builds

Mystr = constr(min_length=1, max_length=STR_MAX_LEN, strict=True)
Myint = conint(ge=0, strict=True)
Myfloat = confloat(ge=0., strict=True)
Myitem = conlist(min_items=2, max_items=2, item_type=Mystr)

app = Bottle()
app.install(ErrorsRestPlugin())

last_modified = datetime.datetime.now(datetime.timezone.utc)

@app.hook('before_request')
def before():
    db.connect()

@app.hook('after_request')
def after():
    db.close()

def cache_with_last_modified(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
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

        header_name = 'Authorization'
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
        if response.status_code < 400 and result:
            result = json.dumps(result)
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

class BuildSchema(pydantic.BaseModel):
    season: Optional[Mystr]
    league: Mystr
    phase: Mystr
    year: Optional[Myint]
    month: Myint
    day: Myint
    match_id: Myint
    game_i: conint(ge=1, le=7, strict=True)
    win: StrictBool
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
    relics: conlist(min_items=0, max_items=2, item_type=Myitem)
    items: conlist(min_items=0, max_items=6, item_type=Myitem)

class BuildsSchema(pydantic.BaseModel):
    __root__: List[BuildSchema]

@app.post('/api/builds')
@verify_integrity
@validate_request_body(BuildsSchema)
def builds_post(builds):
    global last_modified
    if not builds:
        response.status = 204
        return
    try:
        post_builds(builds)
        last_modified = datetime.datetime.now(datetime.timezone.utc)
        response.status = 201
        return
    except MyError as e:
        response.status = 400
        return str(e)

@app.get('/api/options')
@cache_with_last_modified
@jsonify
def options():
    return get_options()

@app.get('/api/builds')
@cache_with_last_modified
@jsonify
def builds_get():
    page = request.query.get('page', '1')
    page = int(page) if page.isnumeric() else 1
    seasons = [int(x) for x in request.query.getall('season')]
    leagues = request.query.getall('league')
    phases = request.query.getall('phase')
    wins = [bool(int(x)) for x in request.query.getall('win')]
    roles = request.query.getall('role')
    team1s = request.query.getall('team1')
    player1s = request.query.getall('player1')
    god1s = request.query.getall('god1')
    team2s = request.query.getall('team2')
    player2s = request.query.getall('player2')
    god2s = request.query.getall('god2')
    relics = request.query.getall('relic')
    items = request.query.getall('item')
    return get_builds(page=page, seasons=seasons, leagues=leagues,
        phases=phases, wins=wins, roles=roles, team1s=team1s,
        player1s=player1s, god1s=god1s, team2s=team2s, player2s=player2s,
        god2s=god2s, relics=relics, items=items)

if __name__ == '__main__':
    load_dotenv('../.env')
    app.run(host='localhost', port=8080, reloader=True, debug=True)
