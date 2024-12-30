from backend.config import load_webapi_config
from backend.webapi.webapi import app, logger, setup_webapi_logging

load_webapi_config()
setup_webapi_logging()
logger.info("Starting worker")
application = app
