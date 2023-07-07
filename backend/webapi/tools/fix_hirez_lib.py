"""
Functions to simplify manual changes in the database
necessitated by errors on the HiRez website.
"""

import functools
import typing as t

import peewee as pw

from backend.webapi.models import Build, Item, db
from backend.webapi.post_builds.images import (
    compress_and_base64_image,
    get_image,
    save_item_icon_to_archive,
)
from backend.webapi.simple_queries import update_last_modified
from backend.webapi.webapi import what_time_is_it


def modify_db(func: t.Callable) -> t.Callable:
    @functools.wraps(func)
    def wrapper_modify_db() -> t.Any:
        with db:
            with db.atomic():
                ret = func()
                update_last_modified(what_time_is_it())
                return ret

    return wrapper_modify_db


def rename(table: t.Any, where: pw.Expression, **renames: t.Any) -> None:
    query = table.select().where(where)
    for row in query:
        for new_column, new_value in renames.items():
            setattr(row, new_column, new_value)
        row.save()
        print("rename:", renames)


def fix_image_name(old_name: str, new_name: str, also_download: bool) -> None:
    rename(Item, Item.image_name == old_name, image_name=new_name)

    if not also_download:
        return

    image_data = get_image(new_name)
    b64_image_data, was_compressed = compress_and_base64_image(image_data)

    for item in Item.select().where(
        (Item.image_name == new_name) & (Item.image_data.is_null(True))
    ):
        item.image_data = b64_image_data
        item.save()
        print("fix_image_name:", old_name, "->", new_name)
        if was_compressed:
            save_item_icon_to_archive(item, image_data)


def fix_player_name(old_name: str, new_name: str) -> None:
    rename(Build, Build.player1 == old_name, player1=new_name)
    rename(Build, Build.player2 == old_name, player2=new_name)


def get_item(image_name: str, index: int) -> Item:
    items = list(Item.select().where(Item.image_name == image_name))
    return items[index]


def fix_role(
    match_id: int,
    game_i: int,
    player1: str,
    wrong_role: str,
    correct_role: str,
    fix_opp_too: bool = False,
) -> None:
    build = (
        Build.select()
        .where(
            (Build.match_id == match_id)
            & (Build.game_i == game_i)
            & (Build.player1 == player1)
            & (Build.role == wrong_role)
        )
        .first()
    )
    if build is None:
        return

    print(
        f"build: {match_id} {game_i} {player1}",
        f"role: {build.role} -> {correct_role}",
        sep="\n\t",
    )
    build.role = correct_role
    build.save()

    fix_player2_and_god2(match_id, game_i, player1, build.player2, fix_opp_too)


def fix_player2_and_god2(
    match_id: int,
    game_i: int,
    player1: str,
    wrong_player2: str,
    fix_opp_too: bool = False,
) -> None:
    build = (
        Build.select()
        .where(
            (Build.match_id == match_id)
            & (Build.game_i == game_i)
            & (Build.player1 == player1)
            & (Build.player2 == wrong_player2)
        )
        .first()
    )
    if build is None:
        return

    opp_build = (
        Build.select()
        .where(
            (Build.match_id == match_id)
            & (Build.game_i == game_i)
            & (Build.role == build.role)
            & (Build.team1 == build.team2)
        )
        .first()
    )

    print(
        f"build: {match_id} {game_i} {player1}",
        f"player2: {build.player2} -> {opp_build.player1}",
        f"god2: {build.god2} -> {opp_build.god1}",
        sep="\n\t",
    )
    build.player2 = opp_build.player1
    build.god2 = opp_build.god1
    build.save()

    if not fix_opp_too:
        return

    print(
        f"build: {match_id} {game_i} {opp_build.player1}",
        f"player2: {opp_build.player2} -> {build.player1}",
        f"god2: {opp_build.god2} -> {build.god1}",
        sep="\n\t",
    )
    opp_build.player2 = build.player1
    opp_build.god2 = build.god1
    opp_build.save()


def fix_god(
    match_id: int,
    game_i: int,
    player1: str,
    wrong_god1: str,
    correct_god1: str,
) -> None:
    build = (
        Build.select()
        .where(
            (Build.match_id == match_id)
            & (Build.game_i == game_i)
            & (Build.player1 == player1)
            & (Build.god1 == wrong_god1)
        )
        .first()
    )
    if build is None:
        return

    print(
        f"build: {match_id} {game_i} {player1}",
        f"god1: {build.god1} -> {correct_god1}",
        sep="\n\t",
    )
    build.god1 = correct_god1
    build.save()

    opp_build = (
        Build.select()
        .where(
            (Build.match_id == match_id)
            & (Build.game_i == game_i)
            & (Build.player2 == build.player1)
            & (Build.god2 == wrong_god1)
        )
        .first()
    )
    if opp_build is None:
        return

    print(
        f"build: {match_id} {game_i} {opp_build.player1}",
        f"god2: {opp_build.god2} -> {correct_god1}",
        sep="\n\t",
    )
    opp_build.god2 = correct_god1
    opp_build.save()
