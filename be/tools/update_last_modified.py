import be.backend
import be.models
import be.simple_queries

with be.models.db:
    be.simple_queries.update_last_modified(be.backend.what_time_is_it())
