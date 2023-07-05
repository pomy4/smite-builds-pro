"""
This file is only used on PythonAnywhere, but it is kept in the repo so that it can
be version controlled. The only requirement is that the "application" variable is set
to a WSGI handler, so the code that is in the actual PythonAnywhere configuration is
"from <this file> import application" (and some sys.path manipulation).
"""

import os
import time

from backend.config import load_webapi_config
from backend.webapi.webapi import app, logger, setup_webapi_logging

os.environ["TZ"] = "Europe/Prague"
time.tzset()

load_webapi_config()
setup_webapi_logging()
logger.info("Starting worker")
application = app
