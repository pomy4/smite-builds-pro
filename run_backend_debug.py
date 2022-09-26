import sys

import shared
from be.backend import app

shared.load_default_dot_env()
app.run(host="localhost", port=8080, reloader=len(sys.argv) < 2, debug=True)
