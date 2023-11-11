import datetime
import functools
import json
import typing as t
from pathlib import Path

import sqlalchemy as sa
import sqlalchemy.orm as sao

from backend.webapi.models import (
    CURRENT_DB_VERSION,
    DbVersion,
    db_session,
    disable_foreign_keys,
)
from backend.webapi.simple_queries import (
    get_version,
    update_last_modified,
    update_version,
)
from backend.webapi.webapi import what_time_is_it


def migrate_db() -> None:
    with disable_foreign_keys():
        with db_session.begin():
            version_index = get_version().index

            if version_index == CURRENT_DB_VERSION.index:
                return

            add_version_table(version_index)
            switch_to_sqlalchemy(version_index)
            add_god_class(version_index)
            add_image_table(version_index)

            update_last_modified(what_time_is_it())


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


def load_to_dict(table: sa.Table) -> dict[int, dict[str, t.Any]]:
    return {
        row_mapping["id"]: dict(row_mapping)
        for row_mapping in select_all(table).mappings()
    }


def load_to_list(table: sa.Table) -> list[dict[str, t.Any]]:
    return [dict(row_mapping) for row_mapping in select_all(table).mappings()]


def select_all(table: sa.Table) -> sa.Result:
    return db_session.execute(sa.select(table))


def get_tables(*table_names: str) -> list[sa.Table]:
    base: sao.DeclarativeBase = sao.declarative_base()
    base.metadata.reflect(bind=db_session.connection())
    return [base.metadata.tables[table_name] for table_name in table_names]


def drop_tables(*table_names: str) -> None:
    for table_name in table_names:
        # Bound parameters don't work for table names.
        db_session.execute(sa.text(f"DROP TABLE {table_name}"))


def execute_migrations_script(script_name: str) -> None:
    migrations_dir = Path(__file__).parent / "migrations"
    script_path = migrations_dir / script_name
    script = script_path.read_text("utf8")

    statements = script.split("\n\n")
    for statement in statements:
        db_session.execute(sa.text(statement))


def load_json(json_name: str) -> t.Any:
    migrations_dir = Path(__file__).parent / "migrations"
    json_path = migrations_dir / json_name
    json_str = json_path.read_text("utf8")
    result = json.loads(json_str)
    return result


def save_into_tables(**datas: list | dict) -> None:
    tables = get_tables(*datas.keys())
    for table, data in zip(tables, datas.values()):
        if isinstance(data, dict):
            data = list(data.values())
        db_session.execute(sa.insert(table), data)


@migration(DbVersion.ADD_IMAGE_TABLE)
def add_image_table() -> None:
    item_table, *_ = get_tables("item")
    items = load_to_list(item_table)

    images: dict[bytes, int] = {}
    for item in sorted(items, key=lambda x: x["id"]):
        image_data: bytes = item.pop("image_data")
        image_id = images.get(image_data)
        if image_id is None:
            image_id = item["id"]
            images[image_data] = image_id
        else:
            print(f"Duplicate image: {item['id']} {image_id}")
        item["image_id"] = image_id

    images_final = [
        {"id": image_id, "data": image_data} for image_data, image_id in images.items()
    ]

    drop_tables("item")
    execute_migrations_script("04_add_image_table.sql")
    save_into_tables(item=items, image=images_final)


@migration(DbVersion.ADD_GOD_CLASS)
def add_god_class() -> None:
    build_table, *_ = get_tables("build")
    builds = load_to_list(build_table)
    god_classes = load_json("03_god_classes.json")

    for build in builds:
        build["god_class"] = god_classes.get(build["god1"])

    drop_tables("build")
    execute_migrations_script("03_add_god_class.sql")
    save_into_tables(build=builds)


@migration(DbVersion.SWITCH_TO_SQLALCHEMY)
def switch_to_sqlalchemy() -> None:
    # get all data
    last_modified_table, last_checked_table, item_table, build_table = get_tables(
        "last_modified", "last_checked", "item", "build"
    )
    last_modifieds = load_to_dict(last_modified_table)
    last_checkeds = load_to_dict(last_checked_table)
    items = load_to_dict(item_table)
    builds = load_to_list(build_table)

    # make metadata
    last_modified = last_modifieds[1]["data"]
    last_modified = last_modified.replace(tzinfo=datetime.timezone.utc)
    last_modified_str = last_modified.isoformat()
    metadatas = [{"key": "last_modified", "value": last_modified_str}]
    if last_checked := last_checkeds.get(1):
        metadatas.append({"key": "last_checked", "value": last_checked["data"]})
    if last_checked := last_checkeds.get(2):
        metadatas.append({"key": "last_checked_tooltip", "value": last_checked["data"]})

    # get relic names
    relic_ids = set()
    for build in builds:
        if relic_id := build["relic1_id"]:
            relic_ids.add(relic_id)
        if relic_id := build["relic2_id"]:
            relic_ids.add(relic_id)

    # add is_relic
    for item in items.values():
        item["is_relic"] = item["id"] in relic_ids

    # iter builds, make build_items
    build_items = []
    for build in builds:
        build_id = build["id"]
        for item_key_name, cnt in [("relic", 2), ("item", 6)]:
            for i in range(cnt):
                item_key = f"{item_key_name}{i+1}_id"
                if item_id := build[item_key]:
                    build_items.append(
                        {"build_id": build_id, "item_id": item_id, "index": i}
                    )

    # pop relic/item stuff from builds
    for build in builds:
        for k in [
            "relic1_id",
            "relic2_id",
            "item1_id",
            "item2_id",
            "item3_id",
            "item4_id",
            "item5_id",
            "item6_id",
        ]:
            del build[k]

    # drop old data
    drop_tables("last_modified", "last_checked", "version", "build", "item")

    # make new tables
    execute_migrations_script("02_switch_to_sqlalchemy.sql")

    # bulk insert new data
    save_into_tables(
        metadata=metadatas, item=items, build=builds, build_items=build_items
    )


@migration(DbVersion.ADD_VERSION_TABLE)
def add_version_table() -> None:
    raise RuntimeError("Migration not supported anymore")


if __name__ == "__main__":
    migrate_db()
