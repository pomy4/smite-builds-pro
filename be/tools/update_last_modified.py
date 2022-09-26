import be.backend
import be.models

with be.models.db:
    be.models.update_last_modified(be.backend.what_time_is_it())
