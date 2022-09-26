from models import db, update_last_modified

from backend import what_time_is_it

with db:
    update_last_modified(what_time_is_it())
