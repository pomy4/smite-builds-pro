import functools
import typing as t

from backend.webapi.models import CURRENT_DB_VERSION, DbVersion, Version, db
from backend.webapi.simple_queries import update_version


def migrate_db() -> None:
    with db:
        with db.atomic():
            version_index = get_version().index

            if version_index == CURRENT_DB_VERSION.index:
                return

            add_version_table(version_index)


def get_version() -> DbVersion:
    return DbVersion(Version.get().data) if Version.table_exists() else DbVersion.OLD


Migration = t.Callable[[], None]
WrappedMigration = t.Callable[[int], None]


def migration(db_version: DbVersion) -> t.Callable[[Migration], WrappedMigration]:
    def outer_wrapper(migration: Migration) -> WrappedMigration:
        @functools.wraps(migration)
        def inner_wrapper(version_index: int) -> None:
            if version_index < db_version.index:
                migration()
                update_version(db_version)
                print(f"Migrated database to version: {db_version.value}")

        return inner_wrapper

    return outer_wrapper


@migration(DbVersion.ADD_VERSION_TABLE)
def add_version_table() -> None:
    Version.create_table()


if __name__ == "__main__":
    migrate_db()
