import be.backend
import be.models
from be.models import CURRENT_DB_VERSION, DB_VERSIONS, DbVersion, Version


def migrate_db() -> None:
    with be.models.db:
        with be.models.db.atomic():
            version = get_version()
            if version == CURRENT_DB_VERSION:
                return
            version_i = DB_VERSIONS.index(version)

            if DB_VERSIONS[version_i + 1] == DbVersion.ADD_VERSION_TABLE:
                add_version_table()


def get_version() -> DbVersion:
    return DbVersion(Version.get().data) if Version.table_exists() else DbVersion.OLD


def add_version_table() -> None:
    Version.create_table()
    be.models.update_version(DbVersion.ADD_VERSION_TABLE)
    print(f"Migrated database to version: {DbVersion.ADD_VERSION_TABLE.value}")


if __name__ == "__main__":
    migrate_db()
