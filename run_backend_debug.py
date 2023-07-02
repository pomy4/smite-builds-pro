import sys

import be.backend
import be.tools.create_db
import be.tools.migrate_db
from config import load_webapi_config

load_webapi_config()
be.tools.create_db.create_db()
be.tools.migrate_db.migrate_db()
be.backend.setup_logging()
be.backend.app.run(host="localhost", port=8080, reloader=len(sys.argv) < 2, debug=True)
