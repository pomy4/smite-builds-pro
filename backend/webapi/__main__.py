import os
import sys

from backend.config import load_webapi_config
from backend.webapi.tools.migrate_db import migrate_db
from backend.webapi.tools.prepare_storage import prepare_storage
from backend.webapi.webapi import app, logger, setup_webapi_logging

prepare_storage()
migrate_db()

load_webapi_config()
setup_webapi_logging()
host, port = "localhost", 4000

if not os.environ.get("BOTTLE_CHILD"):
    logger.info(f"Starting server: http://{host}:{port}/")
else:
    logger.info("Reloader detected")

app.run(host=host, port=port, reloader=len(sys.argv) < 2, debug=True)
