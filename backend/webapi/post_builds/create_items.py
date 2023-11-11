import base64
import dataclasses as dc
import typing as t

import sqlalchemy as sa

from backend.config import get_webapi_config
from backend.webapi.get_builds import EVOLVED_PREFIX, GREATER_PREFIX, UPGRADE_SUFFIX
from backend.webapi.models import Build, BuildItem, Image, Item, db_session
from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger as logger
from backend.webapi.post_builds.auto_fixes_logger import log_curr_game
from backend.webapi.post_builds.images import (
    compress_image_ignore_errors,
    get_image_or_none,
    save_icon_to_archive,
)

BuildDict = dict[str, t.Any]


@dc.dataclass(frozen=True)
class ItemKey:
    is_relic: bool
    name: str
    image_name: str


@dc.dataclass
class BuildItemWip:
    build_i: int
    item_i: int
    index: int


def create_item_keys(
    build_dicts: list[BuildDict],
) -> tuple[list[ItemKey], list[BuildItemWip]]:
    """Uniquerizes items."""

    def handle_one_item() -> None:
        item_key = ItemKey(is_relic, name, image_name)
        item_i = item_keys.get(item_key)
        if item_i is None:
            item_i = len(item_keys)
            item_keys[item_key] = item_i
        build_item_wip = BuildItemWip(build_i, item_i, index)
        build_item_wips.append(build_item_wip)

    item_keys: dict[ItemKey, int] = {}
    build_item_wips: list[BuildItemWip] = []
    for build_i, build_dict in enumerate(build_dicts):
        with log_curr_game(build_dict):
            for dict_key, is_relic in [("relics", True), ("items", False)]:
                for index, (name, image_name) in enumerate(build_dict[dict_key]):
                    handle_one_item()
                del build_dict[dict_key]

    item_keys_lst = list(item_keys.keys())
    return item_keys_lst, build_item_wips


@dc.dataclass
class ItemWip:
    key: ItemKey
    image_name: str
    image_data: bytes | None


def create_item_wips(item_keys: list[ItemKey]) -> list[ItemWip]:
    """
    Downloads item images from the Hi-Rez CDN.
    Done separately here, so that the database inserts/locks are not intertwined with
    the image downloading / sleeping.
    """
    item_wips = [create_item_wip(item_key) for item_key in item_keys]
    return item_wips


def create_item_wip(item_key: ItemKey) -> ItemWip:
    image_name, image_data = get_image_data(item_key.name, item_key.image_name)
    item_wip = ItemWip(item_key, image_name, image_data)
    return item_wip


def get_image_data(name: str, image_name: str) -> tuple[str, bytes | None]:
    fixed_image_name = fix_image_name(name, image_name)
    # Try the fixed image name.
    image_data = get_image_or_none(fixed_image_name)
    if image_data is not None:
        return fixed_image_name, image_data

    # Didn't work - try the backup image name, if we have one.
    backup_item_names = get_webapi_config().backup_item_names
    if backup_image_name := backup_item_names.get(fixed_image_name):
        image_data = get_image_or_none(backup_image_name)
        if image_data is not None:
            logger.info(f"Image (bkp): {fixed_image_name} -> {backup_image_name}")
            return backup_image_name, image_data

    # Also didn't work - try the normal image name
    # (if it's different from the fixed one).
    if image_name == fixed_image_name:
        return image_name, None

    image_date = get_image_or_none(image_name)
    if image_date is not None:
        msg = f"Fixed image name didn't work: {fixed_image_name} -> {image_name}"
        logger.warning(msg)
        return image_name, image_data

    # More ideas, if needed:
    # Check items.json from Hi-Rez API
    # Get most recent image from item with the same key

    return image_name, None


def fix_image_name(name: str, image_name: str) -> str:
    """
    If item has a hyphen or a number in a name, then the image name used by Hi-Rez will
    be wrong (the hyphen/number will be missing, e.g. 'sturdy-stew-step-.jpg' instead
    of 'sturdy-stew---step-2.jpg') (and hence the image will not load). So, here we
    convert the item name into the image name ourselves.
    """
    image_name_split = image_name.rsplit(".", 1)
    if len(image_name_split) == 1:
        logger.warning(f"No extension: {image_name}")
        return image_name
    _, ext = image_name_split

    slug = name.lower().replace(" ", "-").replace("'", "")
    fixed_image_name = f"{slug}.{ext}"

    if fixed_image_name != image_name:
        logger.info(f"Image: {image_name} -> {fixed_image_name}")

    return fixed_image_name


def get_or_create_items(item_wips: list[ItemWip]) -> list[Item]:
    items = [get_or_create_item(item_wip) for item_wip in item_wips]
    return items


def get_or_create_item(item_wip: ItemWip) -> Item:
    if item_wip.image_data is None:
        logger.warning(f"Missing image: {item_wip.image_name}")
        image_id = None
    else:
        image_id = get_or_create_image(item_wip.image_name, item_wip.image_data)

    modified_name, name_was_modified = modify_item_name(
        item_wip.key.is_relic, item_wip.key.name
    )

    item = db_session.scalars(
        sa.select(Item).where(
            Item.is_relic == item_wip.key.is_relic,
            Item.name == modified_name,
            Item.name_was_modified == name_was_modified,
            Item.image_name == item_wip.image_name,
            Item.image_id == image_id,
        )
    ).one_or_none()

    if item:
        return item

    new_item = Item(
        item_wip.key.is_relic,
        modified_name,
        name_was_modified,
        item_wip.image_name,
        image_id,
    )
    db_session.add(new_item)
    db_session.flush()

    return new_item


def get_or_create_image(image_name: str, image_data: bytes) -> int:
    compressed_image_data, was_compressed = compress_image_ignore_errors(
        image_name, image_data
    )

    b64_image_data = base64.b64encode(compressed_image_data)

    image_id, was_new = get_or_create_image_inner(b64_image_data)

    if was_compressed and was_new:
        save_icon_to_archive(image_id, image_name, image_data)

    return image_id


def get_or_create_image_inner(image_data: bytes) -> tuple[int, bool]:
    image = db_session.scalars(
        sa.select(Image).where(Image.data == image_data)
    ).one_or_none()

    if image:
        return image.id, False
    else:
        new_image = Image(image_data)
        db_session.add(new_image)
        db_session.flush()
        return new_image.id, True


def modify_item_name(is_relic: bool, name: str) -> tuple[str, int]:
    if is_relic and name.endswith(UPGRADE_SUFFIX):
        return name[: -len(UPGRADE_SUFFIX)], 1
    elif not is_relic and name.startswith(EVOLVED_PREFIX):
        return name[len(EVOLVED_PREFIX) :], 2
    elif is_relic and name.startswith(GREATER_PREFIX):
        return name[len(GREATER_PREFIX) :], 3
    else:
        return name, 0


def create_build_items(
    builds: list[Build], items: list[Item], build_item_wips: list[BuildItemWip]
) -> None:
    for build_item_wip in build_item_wips:
        create_build_item(builds, items, build_item_wip)
    db_session.flush()


def create_build_item(
    builds: list[Build], items: list[Item], build_item_wip: BuildItemWip
) -> None:
    build_id = builds[build_item_wip.build_i].id
    item_id = items[build_item_wip.item_i].id
    build_item = BuildItem(build_id, item_id, build_item_wip.index)
    db_session.add(build_item)
