import datetime as dt
import unicodedata

import sqlalchemy as sa

from backend.webapi.exceptions import MyValidationError
from backend.webapi.models import Build, db_session
from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger as logger
from backend.webapi.post_builds.auto_fixes_logger import log_curr_game
from backend.webapi.post_builds.create_items import BuildDict
from backend.webapi.post_builds.fix_gods import add_god_classes, fix_gods
from backend.webapi.post_builds.fix_roles import fix_roles
from backend.webapi.post_builds.hirez_api import GodInfo


def create_builds(god_info: GodInfo, build_dicts: list[BuildDict]) -> list[Build]:
    player_names = {
        player_name.upper(): player_name
        for player_name in db_session.scalars(sa.select(Build.player1).distinct()).all()
    }

    today = dt.date.today()

    for build_dict in build_dicts:
        build_dict["game_length"] = dt.time(
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
            build_dict["date"] = dt.date(
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

    fix_roles(build_dicts)
    fix_gods(build_dicts, god_info.newest_god)
    add_god_classes(build_dicts, god_info.god_classes)

    builds = [Build(**build_dict) for build_dict in build_dicts]

    for build in builds:
        db_session.add(build)
    db_session.flush()

    return builds


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
            logger.info(f"Player: {player_name} -> {existing_player_name}")
        return existing_player_name


def remove_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )
