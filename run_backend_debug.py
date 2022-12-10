import sys

import be.backend
import be.tools.create_db
import be.tools.migrate_db
import shared

shared.load_default_dot_env()
be.tools.create_db.create_db()
be.tools.migrate_db.migrate_db()
be.backend.app.run(host="localhost", port=8080, reloader=len(sys.argv) < 2, debug=True)
