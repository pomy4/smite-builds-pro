from pathlib import Path

from backend.shared import ITEM_ICONS_ARCHIVE_DIR, STORAGE_DIR
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


def prepare_storage() -> None:
    create_dir(STORAGE_DIR)
    create_dir(ITEM_ICONS_ARCHIVE_DIR)
    create_db()


def create_dir(path: Path) -> None:
    if path.is_dir():
        return
    path.mkdir()
    print(f"Created directory: {path}")


def create_db() -> None:
    if db_path.exists():
        return

    with db_session.begin():
        Base.metadata.create_all(db_engine)
        reorder_indices()
        update_version(CURRENT_DB_VERSION)
        update_last_modified(what_time_is_it())

    print(f"Database created with version: {CURRENT_DB_VERSION.value}")


if __name__ == "__main__":
    prepare_storage()
