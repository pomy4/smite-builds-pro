from bottle import Bottle, run, get, response, HTTPError, post, request, HTTPResponse
from bottle_errorsrest import ErrorsRestPlugin
from models import add_builds, db, Build, get_last_match_id
import json

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

@app.post('/phases')
def phases():
    try:
        phases_bytes = request.body.read()
        phases_str = phases_bytes.decode('utf-8')
        phases = json.loads(phases_str)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPResponse(400, 'Request body should be an utf-8 encoded json.')
    if not isinstance(phases, list) or any(not isinstance(phase, str) for phase in phases):
        return HTTPResponse(400, 'Request body should be a list of strings.')
    match_ids = [(match_id if (match_id := get_last_match_id(phase)) else 0) for phase in phases]
    return json.dumps(match_ids)

@app.post('/builds')
def builds():
    try:
        builds_bytes = request.body.read()
        builds_str = builds_bytes.decode('utf-8')
        builds = json.loads(builds_str)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPResponse(400, 'Request body should be an utf-8 encoded json.')
    if add_builds(builds): # TODO input checking.
        return HTTPResponse(status=201)
    else:
        return HTTPResponse(status=400, body='At least one of the builds already exists.')

@app.get('/players')
def players():
    players = []
    for row in Build.select(Build.player1).distinct().order_by(Build.player1):
        players.append(row.player1)
    return json.dumps(players)

@app.get('/player/<player>')
def player(player):
    if not (1 <= len(player) <= 30):
        return HTTPError(400, 'Input too long')
    builds = []
    for row in Build.select().where(Build.player1 == player):
        builds.append({'player': row.player1, 'role': row.role, 'god': row.god1})
    return json.dumps(builds)

if __name__ == '__main__':
    app.run(host='localhost', port=8080, reloader=True, debug=True)
