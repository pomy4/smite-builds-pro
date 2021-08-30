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
