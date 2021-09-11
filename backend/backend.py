import json
import functools

from bottle import Bottle, response,  request, HTTPResponse
from bottle_errorsrest import ErrorsRestPlugin
import pydantic
from typing import List, Optional

from models import db, Build, add_builds, get_last_match_id

app = Bottle()
app.install(ErrorsRestPlugin())

@app.hook('before_request')
def before():
    response.content_type = 'application/json'
    db.connect()

@app.hook('after_request')
def after():
    db.close()
    response.add_header('Access-Control-Allow-Origin', '*')

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

class PhasesSchema(pydantic.BaseModel):
    __root__: List[str]

@app.post('/phases')
@validate_request_body(PhasesSchema)
def phases(phases):
    match_ids = [(match_id if (match_id := get_last_match_id(phase)) else 0) for phase in phases]
    return json.dumps(match_ids)

class BuildSchema(pydantic.BaseModel):
    season: Optional[str]
    league: str
    phase: str
    year: Optional[str]
    month: int
    day: int
    match_id: int
    game_i: int
    win: bool
    minutes: int
    seconds: int
    kills: int
    deaths: int
    assists: int
    role: str
    player1: str
    god1: str
    team1: str
    player2: str
    god2: str
    team2: str
    relics: List[List[str]]
    items: List[List[str]]

class BuildsSchema(pydantic.BaseModel):
    __root__: List[BuildSchema]

@app.post('/builds')
@validate_request_body(BuildsSchema)
def builds(builds):
    if add_builds(builds):
        return HTTPResponse(status=201)
    else:
        return HTTPResponse(status=409, body='At least one of the builds already exists.')

@app.get('/players')
def players():
    players = []
    for row in Build.select(Build.player1).distinct().order_by(Build.player1):
        players.append(row.player1)
    return json.dumps(players)

@app.get('/player/<player>')
def player(player):
    if not (1 <= len(player) <= 30):
        return HTTPResponse(status=400, body='Input too long or too short.')
    builds = []
    for row in Build.select().where(Build.player1 == player):
        builds.append({'player': row.player1, 'role': row.role, 'god': row.god1})
    return json.dumps(builds)

if __name__ == '__main__':
    app.run(host='localhost', port=8080, reloader=True, debug=True)
