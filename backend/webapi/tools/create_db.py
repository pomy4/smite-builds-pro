from backend.webapi.models import (
    CURRENT_DB_VERSION,
    Build,
    Item,
    LastChecked,
    LastModified,
    Version,
    db,
    db_path,
)
from backend.webapi.simple_queries import update_last_modified, update_version
from backend.webapi.webapi import what_time_is_it


def create_db() -> None:
    if db_path.exists():
        return

    with db:
        with db.atomic():
            db.create_tables([Build, Item, LastChecked, LastModified, Version])
            update_version(CURRENT_DB_VERSION)
            update_last_modified(what_time_is_it())
    print(f"Database created with version: {CURRENT_DB_VERSION.value}")


if __name__ == "__main__":
    create_db()
