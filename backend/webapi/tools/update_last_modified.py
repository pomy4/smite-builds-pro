from backend.webapi.models import db_session
from backend.webapi.simple_queries import update_last_modified
from backend.webapi.webapi import what_time_is_it

with db_session.begin():
    update_last_modified(what_time_is_it())
