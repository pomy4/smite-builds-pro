import datetime
import unicodedata
from typing import TYPE_CHECKING

import peewee as pw

import be.loggers
import be.models
import be.pb.fix_gods
import be.pb.fix_roles
import be.pb.images
from be.exceptions import MyValidationError
from be.get_builds import EVOLVED_PREFIX, GREATER_PREFIX, UPGRADE_SUFFIX
from be.loggers import auto_fixes_logger
from be.models import Build, Item

if TYPE_CHECKING:
    from be.backend import PostBuildRequest


def post_builds(builds: list["PostBuildRequest"]) -> None:
    """Logging wrapper."""
    try:
        auto_fixes_logger.info("Start")
        post_builds_inner(builds)
    except Exception:
        auto_fixes_logger.info("End (FAIL)")
    else:
        auto_fixes_logger.info("End")


def post_builds_inner(builds_: list["PostBuildRequest"]) -> None:
    # For now just work with dicts.
    builds = [build.dict() for build in builds_]

    # Uniquerize items based upon name and image name.
    items = {}
    for build in builds:
        with be.loggers.log_curr_game(build):
            build["items"] = [
                (name, fix_image_name(image_name))
                for name, image_name in build["items"]
            ]
        for name, image_name in build["relics"]:
            items[(name, image_name)] = True
        for name, image_name in build["items"]:
            items[(name, image_name)] = False

    with be.models.db.atomic():
        # Create or retrieve items.
        for (name, image_name), is_relic in items.items():
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

            image_data = be.pb.images.get_image_or_none(image_name)

            if image_data is None and (
                backup_image_name := (BACKUP_IMAGE_NAMES).get(image_name)
            ):
                auto_fixes_logger.info(f"ImageBkp|{image_name} -> {backup_image_name}")
                # image_name is not updated here, so that if HiRez fixes the URL,
                # it will not create a new item in the database
                # (unless HiRez also changes the image).
                image_data = be.pb.images.get_image_or_none(backup_image_name)

            if image_data is None:
                auto_fixes_logger.warning(f"Missing image: {image_name}")
                b64_image_data, was_compressed = None, False
            else:
                (
                    b64_image_data,
                    was_compressed,
                ) = be.pb.images.compress_and_base64_image_or_none(image_data)

            item, was_new = Item.get_or_create(
                name=modified_name,
                name_was_modified=name_was_modified,
                image_name=image_name,
                image_data=b64_image_data,
            )

            if image_data is not None and was_compressed and was_new:
                be.pb.images.save_item_icon_to_archive(item, image_data)

            items[(name, image_name)] = item.id

        # Get player names.
        player_names = {
            b.player1.upper(): b.player1 for b in Build.select(Build.player1).distinct()
        }

        # Create builds.
        today = datetime.date.today()
        for build in builds:
            build["game_length"] = datetime.time(
                hour=build["hours"], minute=build["minutes"], second=build["seconds"]
            )
            if not build.get("year"):
                build["year"] = today.year
            if not build.get("season"):
                season = today.year - 2013
                if today.month == 1 or today.month == 2 and today.day <= 14:
                    season -= 1
                build["season"] = max(season, 0)
            try:
                build["date"] = datetime.date(
                    year=build["year"], month=build["month"], day=build["day"]
                )
            except ValueError as e:
                raise MyValidationError(
                    "At least one of the builds has an invalid date"
                ) from e
            with be.loggers.log_curr_game(build):
                build["player1"] = fix_player_name(player_names, build["player1"])
                build["player2"] = fix_player_name(player_names, build["player2"])
            del (
                build["hours"],
                build["minutes"],
                build["seconds"],
                build["year"],
                build["month"],
                build["day"],
            )
            for i, (name, image_name) in enumerate(build["relics"], 1):
                build[f"relic{i}"] = items[(name, image_name)]
            for i, (name, image_name) in enumerate(build["items"], 1):
                build[f"item{i}"] = items[(name, image_name)]
            del build["relics"], build["items"]

        be.pb.fix_roles.fix_roles(builds)
        be.pb.fix_gods.fix_gods(builds)

        try:
            # This is done one by one, since for some reason bulk insertion
            # sometimes causes silent corruption of data (!).
            for build in builds:
                Build.create(**build)
        except pw.IntegrityError as e:
            raise MyValidationError(
                "At least one of the builds is already in the database"
            ) from e


# Names which don't work right now, but will probably start working someday.
# Made for a renamed item whose new url doesn't work.
BACKUP_IMAGE_NAMES = {
    "manticores-spikes.jpg": "manticores-spike.jpg",
}

FIXED_IMAGE_NAMES = {
    "bloodsoaked-shroud.jpg": "blood-soaked-shroud.jpg",
    "pointed-shuriken.jpg": "8-pointed-shuriken.jpg",
    "faeblessed-hoops.jpg": "fae-blessed-hoops.jpg",
}


def fix_image_name(image_name: str) -> str:
    if image_name not in FIXED_IMAGE_NAMES:
        return image_name
    else:
        fixed_image_name = FIXED_IMAGE_NAMES[image_name]
        auto_fixes_logger.info(f"Image|{image_name} -> {fixed_image_name}")
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
            auto_fixes_logger.info(f"Player|{player_name} -> {existing_player_name}")
        return existing_player_name


def remove_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )
