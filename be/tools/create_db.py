import be.models
from be.models import (
    CURRENT_DB_VERSION,
    Build,
    Item,
    LastChecked,
    LastModified,
    Version,
)


def create_db() -> None:
    if be.models.db_path.exists():
        return

    with be.models.db:
        with be.models.db.atomic():
            be.models.db.create_tables(
                [Build, Item, LastChecked, LastModified, Version]
            )
            be.models.update_version(CURRENT_DB_VERSION)
    print(f"Database created with version: {CURRENT_DB_VERSION.value}")


if __name__ == "__main__":
    create_db()
