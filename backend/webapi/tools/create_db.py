from backend.shared import STORAGE_DIRS
from backend.webapi.models import (
    CURRENT_DB_VERSION,
    Base,
    db_engine,
    db_path,
    db_session,
    reorder_indices,
)
from backend.webapi.simple_queries import update_last_modified, update_version
from backend.webapi.webapi import what_time_is_it


def create_db() -> None:
    if db_path.exists():
        return

    create_storage_dirs()

    with db_session.begin():
        Base.metadata.create_all(db_engine)
        reorder_indices()
        update_version(CURRENT_DB_VERSION)
        update_last_modified(what_time_is_it())

    print(f"Database created with version: {CURRENT_DB_VERSION.value}")


def create_storage_dirs() -> None:
    for dir_ in STORAGE_DIRS:
        if dir_.exists():
            continue
        dir_.mkdir()
        print(f"Created directory: {dir_}")


if __name__ == "__main__":
    create_db()
