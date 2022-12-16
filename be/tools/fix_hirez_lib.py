"""
Functions to simplify manual changes in the database
necessitated by errors on the HiRez website.
"""

import functools
from typing import Any, Callable

import peewee as pw

import be.backend
import be.models
from be.models import Build, Item


def modify_db(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper_modify_db() -> Any:
        with be.models.db:
            with be.models.db.atomic():
                ret = func()
                be.models.update_last_modified(be.backend.what_time_is_it())
                return ret

    return wrapper_modify_db


def rename(table: Any, where: pw.Expression, **renames: Any) -> None:
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

    image_data = be.models.get_image(new_name)
    b64_image_data, was_compressed = be.models.compress_and_base64_image(image_data)

    for item in Item.select().where(
        (Item.image_name == new_name) & (Item.image_data.is_null(True))
    ):
        item.image_data = b64_image_data
        item.save()
        print("fix_image_name:", old_name, "->", new_name)
        if was_compressed:
            be.models.save_item_icon_to_archive(item, image_data)


def fix_player_name(old_name: str, new_name: str) -> None:
    rename(Build, Build.player1 == old_name, player1=new_name)
    rename(Build, Build.player2 == old_name, player2=new_name)


def get_item(image_name: str, index: int) -> be.models.Item:
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


# --------------------------------------------------------------------------------------
# TOO LAZY TO FIX
# --------------------------------------------------------------------------------------

# SEASON 8

# duck3y missing

# 4188|8|SPL|SWC Placements - Group B|2021-12-16|3376|1|1|00:21:06|14.0|7|1|7|
# Jungle|Gilgamesh|LASBRA|BOLTS|Missing data|Missing data|VALKS|
# 1|9|60|229|105|51|15|180

# 4197|8|SPL|SWC Placements - Group B|2021-12-16|3376|2|1|00:23:10|6.0|3|0|3|
# Jungle|Cliodhna|LASBRA|BOLTS|Missing data|Missing data|VALKS|
# 1|2|93|105|122|77|108|78

# 4202|8|SPL|SWC Placements - Group B|2021-12-16|3376|3|1|00:27:35|10.0|3|0|7|
# Jungle|Loki|LASBRA|BOLTS|Missing data|Missing data|VALKS|
# 1|9|15|132|77|54|106|

# SEASON 9

# Set missing

# Pre-Season Friday, 2022 March 25 Atlantis Leviathans VS Valhalla Valkyries
# LVTHN 2 - 0 VALKS (match_id 3472)

# slaaaaaaasH missing

# 5702|9|SCC|NA Phase 1|2022-03-31|3550|1|0|00:34:55|0.0|0|5|0|
# Solo|Cliodhna|Remakami|HOUND|Missing data|Missing data|SAGES|
# 258|256|29|70|257|31|51|15

# 5715|9|SCC|NA Phase 1|2022-03-31|3550|2|1|00:28:26|5.0|1|0|4|
# Solo|Odin|Remakami|HOUND|Missing data|Missing data|SAGES|
# 258|260|202|229|257|31|124|155

# 5724|9|SCC|NA Phase 1|2022-03-31|3550|3|1|00:24:09|5.0|1|0|4|
# Solo|Osiris|Remakami|HOUND|Missing data|Missing data|SAGES|
# 258|260|171|229|30|47|115|124

# 5837|9|SCC|NA Phase 1|2022-04-09|3561|1|1|00:39:04|2.25|2|4|7|
# Solo|Jormungandr|Uzzy|STORM|Missing data|Missing data|SAGES|
# 278|285|139|257|219|176|87|124

# 5850|9|SCC|NA Phase 1|2022-04-09|3561|2|1|00:31:25|7.0|1|1|6|
# Solo|Camazotz|Uzzy|STORM|Missing data|Missing data|SAGES|
# 273|275|202|47|229|51|70|32

# 5885|9|SCC|NA Phase 1|2022-04-14|3562|1|1|00:22:33|8.0|2|1|6|
# Solo|Sun Wukong|RelentlessOne|WRDNS|Missing data|Missing data|SAGES|
# 273|269|29|70|229|32|214|

# 5898|9|SCC|NA Phase 1|2022-04-14|3562|2|1|00:23:51|6.5|4|2|9|
# Solo|Amaterasu|RelentlessOne|WRDNS|Missing data|Missing data|SAGES|
# 282|275|190|47|128|140|51|

# CaptainQuig missing

# 5786|9|SCC|NA Phase 1|2022-04-07|3559|1|0|00:31:59|1.75|2|4|5|Support|
# Atlas|Dashboarřd|WEAVE|Missing data|Missing data|HOUND|
# 264|258|17|19|87|128|20|

# 5795|9|SCC|NA Phase 1|2022-04-07|3559|2|0|00:31:20|0.625|0|8|5|Support|
# Khepri|Dashboarřd|WEAVE|Missing data|Missing data|HOUND|
# 268|264|34|19|20|128||

# Rapio missing

# 9334|9|SCC|EU Phase 2|2022-06-16|3803|2|1|00:34:25|21.0|10|1|11|
# Jungle|Awilix|Dzoni|MAMBO|Missing data|Missing data|RAVEN|
# 276|270|10|78|46|106|77|107

# BIGSLIMTIMMYJIM missing

# 9649|9|SCC|NA Phase 2|2022-06-16|3792|1|0|00:35:05|1.0|1|4|3|
# Support|Khepri|Hurriwind|YOMI|Missing data|Missing data|WEAVE|
# 282|262|17|21|87|128|35|

# delnyy missing

# 9685|9|SCC|NA Phase 2|2022-06-16|3795|1|1|00:26:42|12.0|6|1|6|
# Solo|Bastet|RelentlessOne|WRDNS|Missing data|Missing data|SAGES|
# 276|258|227|70|30|87|15|
