from backend.webapi.models import db
from backend.webapi.simple_queries import update_last_modified
from backend.webapi.webapi import what_time_is_it

with db:
    update_last_modified(what_time_is_it())
