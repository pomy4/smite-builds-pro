import functools
from typing import Callable

import be.backend
import be.models
from be.models import CURRENT_DB_VERSION, DbVersion, Version


def migrate_db() -> None:
    with be.models.db:
        with be.models.db.atomic():
            version_index = get_version().index

            if version_index == CURRENT_DB_VERSION.index:
                return

            add_version_table(version_index)


def get_version() -> DbVersion:
    return DbVersion(Version.get().data) if Version.table_exists() else DbVersion.OLD


Migration = Callable[[], None]
WrappedMigration = Callable[[int], None]


def migrate(db_version: DbVersion) -> Callable[[Migration], WrappedMigration]:
    def outer_wrapper(migration: Migration) -> WrappedMigration:
        @functools.wraps(migration)
        def inner_wrapper(version_index: int) -> None:
            if version_index < db_version.index:
                migration()
                be.models.update_version(db_version)
                print(f"Migrated database to version: {db_version.value}")

        return inner_wrapper

    return outer_wrapper


@migrate(DbVersion.ADD_VERSION_TABLE)
def add_version_table() -> None:
    Version.create_table()


if __name__ == "__main__":
    migrate_db()
