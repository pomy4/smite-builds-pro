import sys

from backend.config import load_webapi_config
from backend.webapi.tools.create_db import create_db
from backend.webapi.tools.migrate_db import migrate_db
from backend.webapi.webapi import app, setup_logging

load_webapi_config()
setup_logging()

create_db()
migrate_db()

app.run(host="localhost", port=8080, reloader=len(sys.argv) < 2, debug=True)
