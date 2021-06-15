from bottle import Bottle, run, get, response, HTTPError
from bottle_errorsrest import ErrorsRestPlugin
from models import db, Build
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

@app.get('/players')
def players():
    players = []
    for row in Build.select(Build.player).distinct().order_by(Build.player):
        players.append(row.player)
    return json.dumps(players)

@app.get('/player/<player>')
def player(player):
    if not (1 <= len(player) <= 30):
        return HTTPError(400, 'Input too long')
    builds = []
    for row in Build.select().where(Build.player == player):
        builds.append({'player': row.player, 'role': row.role, 'god': row.god})
    return json.dumps(builds)

if __name__ == '__main__':
    app.run(host='localhost', port=8080, reloader=True, debug=True)
