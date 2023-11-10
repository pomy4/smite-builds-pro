from __future__ import annotations

import datetime
import typing as t
import unicodedata

import sqlalchemy as sa

from backend.webapi.exceptions import MyValidationError
from backend.webapi.get_builds import EVOLVED_PREFIX, GREATER_PREFIX, UPGRADE_SUFFIX
from backend.webapi.models import Build, BuildItem, Item, db_session
from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger as logger
from backend.webapi.post_builds.auto_fixes_logger import log_curr_game
from backend.webapi.post_builds.fix_gods import add_god_classes, fix_gods
from backend.webapi.post_builds.fix_roles import fix_roles
from backend.webapi.post_builds.hirez_api import get_god_info
from backend.webapi.post_builds.images import (
    compress_and_base64_image_or_none,
    get_image_or_none,
    save_item_icon_to_archive,
)

if t.TYPE_CHECKING:
    from backend.webapi.webapi import PostBuildRequest


def post_builds(builds: list[PostBuildRequest]) -> None:
    """Logging wrapper."""
    try:
        logger.info("Start")
        post_builds_inner(builds)
    except Exception:
        logger.info("End (FAIL)")
        raise
    else:
        logger.info("End")


def post_builds_inner(build_models: list["PostBuildRequest"]) -> None:
    god_info = get_god_info()

    # For now just work with dicts.
    build_dicts = [build_model.dict() for build_model in build_models]

    # Uniquerize items based upon name and image name.
    item_keys: dict[tuple[str, str, bool], None] = {}
    for build_dict in build_dicts:
        with log_curr_game(build_dict):
            for key, is_relic in [("relics", True), ("items", False)]:
                build_dict[key] = [
                    (name, fix_image_name(name, image_name))
                    for name, image_name in build_dict[key]
                ]
                for name, image_name in build_dict[key]:
                    item_keys[(name, image_name, is_relic)] = None

    # Create or retrieve items.
    items = {}
    for name, image_name, is_relic in item_keys.keys():
        modified_name = name
        name_was_modified = 0
        if is_relic and name.endswith(UPGRADE_SUFFIX):
            modified_name = name[: -len(UPGRADE_SUFFIX)]
            name_was_modified = 1
        elif not is_relic and name.startswith(EVOLVED_PREFIX):
            modified_name = name[len(EVOLVED_PREFIX) :]
            name_was_modified = 2
        elif is_relic and name.startswith(GREATER_PREFIX):
            modified_name = name[len(GREATER_PREFIX) :]
            name_was_modified = 3

        image_data = get_image_or_none(image_name)

        if image_data is None and (
            backup_image_name := (BACKUP_IMAGE_NAMES).get(image_name)
        ):
            logger.info(f"ImageBkp|{image_name} -> {backup_image_name}")
            # image_name is not updated here, so that if HiRez fixes the URL,
            # it will not create a new item in the database
            # (unless HiRez also changes the image).
            image_data = get_image_or_none(backup_image_name)

        if image_data is None:
            logger.warning(f"Missing image: {image_name}")
            b64_image_data, was_compressed = None, False
        else:
            (
                b64_image_data,
                was_compressed,
            ) = compress_and_base64_image_or_none(image_data)

        item, was_new = get_or_create_image(
            is_relic=is_relic,
            name=modified_name,
            name_was_modified=name_was_modified,
            image_name=image_name,
            image_data=b64_image_data,
        )

        if image_data is not None and was_compressed and was_new:
            save_item_icon_to_archive(item, image_data)

        items[(name, image_name, is_relic)] = item

    # Get player names.
    player_names = {
        player_name.upper(): player_name
        for player_name in db_session.scalars(sa.select(Build.player1).distinct()).all()
    }

    # Create builds.
    today = datetime.date.today()
    all_item_ids = []
    for build_dict in build_dicts:
        build_dict["game_length"] = datetime.time(
            hour=build_dict["hours"],
            minute=build_dict["minutes"],
            second=build_dict["seconds"],
        )
        if not build_dict.get("year"):
            build_dict["year"] = today.year
        if not build_dict.get("season"):
            season = today.year - 2013
            if today.month == 1 or today.month == 2 and today.day <= 14:
                season -= 1
            build_dict["season"] = max(season, 0)
        try:
            build_dict["date"] = datetime.date(
                year=build_dict["year"],
                month=build_dict["month"],
                day=build_dict["day"],
            )
        except ValueError as e:
            raise MyValidationError(
                "At least one of the builds has an invalid date"
            ) from e
        with log_curr_game(build_dict):
            build_dict["player1"] = fix_player_name(player_names, build_dict["player1"])
            build_dict["player2"] = fix_player_name(player_names, build_dict["player2"])

        del (
            build_dict["hours"],
            build_dict["minutes"],
            build_dict["seconds"],
            build_dict["year"],
            build_dict["month"],
            build_dict["day"],
        )

        item_ids = []
        for i, (name, image_name) in enumerate(build_dict["relics"]):
            item_ids.append((items[(name, image_name, True)].id, i))
        for i, (name, image_name) in enumerate(build_dict["items"]):
            item_ids.append((items[(name, image_name, False)].id, i))
        del build_dict["relics"], build_dict["items"]
        all_item_ids.append(item_ids)

    fix_roles(build_dicts)
    fix_gods(build_dicts, god_info.newest_god)
    add_god_classes(build_dicts, god_info.god_classes)

    builds = [Build(**build_dict) for build_dict in build_dicts]

    for build in builds:
        db_session.add(build)

    # This can throw, most probably due to a build already existing in the database,
    # which will cause a 500, which is fine, since it is an internal endpoint.
    db_session.flush()

    for item_ids, build in zip(all_item_ids, builds):
        for item_id, index in item_ids:
            build_item = BuildItem(build_id=build.id, item_id=item_id, index=index)
            db_session.add(build_item)


# Names which don't work right now, but will probably start working someday.
# Made for a renamed item whose new url doesn't work.
BACKUP_IMAGE_NAMES = {
    "manticores-spikes.jpg": "manticores-spike.jpg",
}


def get_or_create_image(
    is_relic: bool,
    name: str,
    name_was_modified: int,
    image_name: str,
    image_data: bytes | None,
) -> tuple[Item, bool]:
    item = db_session.scalars(
        sa.select(Item).where(
            Item.is_relic == is_relic,
            Item.name == name,
            Item.name_was_modified == name_was_modified,
            Item.image_name == image_name,
            Item.image_data == image_data,
        )
    ).one_or_none()

    if item:
        return item, False
    else:
        new_item = Item(
            is_relic=is_relic,
            name=name,
            name_was_modified=name_was_modified,
            image_name=image_name,
            image_data=image_data,
        )
        db_session.add(new_item)
        db_session.flush()
        return new_item, True


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
        logger.info(f"Image|{image_name} -> {fixed_image_name}")

    return fixed_image_name


def fix_player_name(player_names: dict[str, str], player_name_with_accents: str) -> str:
    player_name = remove_accents(player_name_with_accents)
    player_name_upper = player_name.upper()

    if player_name_upper not in player_names:
        # Update player_names in case the player name
        # has different case in the same batch of builds.
        player_names[player_name_upper] = player_name
        return player_name
    else:
        existing_player_name = player_names[player_name_upper]
        if player_name != existing_player_name:
            logger.info(f"Player|{player_name} -> {existing_player_name}")
        return existing_player_name


def remove_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )
