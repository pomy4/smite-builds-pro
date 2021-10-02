import json
import functools
import os
import hmac
import hashlib

from bottle import Bottle, response,  request, HTTPResponse
from bottle_errorsrest import ErrorsRestPlugin
import pydantic
from pydantic .types import *
from typing import List, Optional
from dotenv import load_dotenv

from models import STR_MAX_LEN, MyError, db, add_builds, get_match_ids, get_select_options, get_builds

Mystr = constr(min_length=1, max_length=STR_MAX_LEN, strict=True)
Myint = conint(ge=0, strict=True)
Myfloat = confloat(ge=0., strict=True)
Myitem = conlist(min_items=2, max_items=2, item_type=Mystr)

app = Bottle()
app.install(ErrorsRestPlugin())

@app.hook('before_request')
def before():
    response.content_type = 'application/json'
    db.connect()

@app.hook('after_request')
def after():
    db.close()
    # response.add_header('Access-Control-Allow-Origin', '*')

def validate_request_body(Schema):
    def outer_wrapper(func):
        @functools.wraps(func)
        def inner_wrapper():
            try:
                body_bytes = request.body.read()
                body_str = body_bytes.decode('utf-8')
                body_json = json.loads(body_str)
                body_dict = Schema.parse_obj(body_json).dict()
                body = body_dict.get('__root__', body_dict)
                return func(body)
            except (UnicodeDecodeError, json.JSONDecodeError, pydantic.ValidationError) as e:
                return HTTPResponse(status=400, body=str(e))
        return inner_wrapper
    return outer_wrapper

def verify_integrity(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not (key_hex := os.getenv('HMAC_KEY_HEX')):
            return HTTPResponse(status=501, body='HMAC secret key isn\'t set on the server.')
        key = bytearray.fromhex(key_hex)

        header_name = 'Authorization'
        if not (digest_header := request.get_header(header_name)):
            return HTTPResponse(status=400, body=f'HMAC digest was not included in the {header_name} header.')

        hmac_obj = hmac.new(key, request.body.read(), hashlib.sha256)
        digest_body = hmac_obj.hexdigest()
        if not hmac.compare_digest(digest_header, digest_body):
            return HTTPResponse(status=403, body='Wrong HMAC digest!')

        return func(*args, **kwargs)
    return wrapper

class PhasesSchema(pydantic.BaseModel):
    __root__: List[Mystr]

@app.post('/phases')
@validate_request_body(PhasesSchema)
def phases(phases):
    match_ids = [get_match_ids(phase) for phase in phases]
    return json.dumps(match_ids)

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

@app.post('/builds')
@verify_integrity
@validate_request_body(BuildsSchema)
def builds(builds):
    try:
        add_builds(builds)
        return HTTPResponse(status=201)
    except MyError as e:
        return HTTPResponse(status=400, body=str(e))

@app.get('/api/select_options')
def select_options():
    return get_select_options()

@app.get('/api/builds')
def builds_():
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
    builds = get_builds(page=page, seasons=seasons, leagues=leagues,
        phases=phases, wins=wins, roles=roles, team1s=team1s,
        player1s=player1s, god1s=god1s, team2s=team2s, player2s=player2s,
        god2s=god2s, relics=relics, items=items)
    return json.dumps(builds)

if __name__ == '__main__':
    load_dotenv('../.env')
    app.run(host='localhost', port=8080, reloader=True, debug=True)
