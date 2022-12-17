"""
This file is only used on PythonAnywhere, but it is kept in the repo so that it can
be version controlled. The only requirement is that the "application" variable is set
to a WSGI handler, so the code that is in the actual PythonAnywhere configuration is
"from <this file> import application" (and some sys.path manipulation).
"""

import os
import time

import be.backend
import shared

os.environ["TZ"] = "Europe/Prague"
time.tzset()

shared.load_default_dot_env()
be.backend.setup_logging()
application = be.backend.app
