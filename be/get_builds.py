import enum
import typing
from typing import TYPE_CHECKING, Any

import peewee as pw
import playhouse.shortcuts

import shared
from be.models import Build, Item

if TYPE_CHECKING:
    from be.backend import GetBuildsRequest


class WhereStrat(enum.Enum):
    match = enum.auto()
    range = enum.auto()


def get_builds(builds_query: "GetBuildsRequest") -> Any:
    relic1, relic2, item1, item2, item3, item4, item5, item6 = (
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
    )

    where = pw.Expression(True, "=", True)
    types = typing.get_type_hints(builds_query, include_extras=True)
    page = 1

    for key, vals in vars(builds_query).items():
        if not vals:
            continue
        if key == "page":
            page = vals[0]
        elif key == "relic":
            for relic in vals:
                where = where & pw.Expression(relic, "IN", [relic1.name, relic2.name])
        elif key == "item":
            for item in vals:
                where = where & pw.Expression(
                    item,
                    "IN",
                    [
                        item1.name,
                        item2.name,
                        item3.name,
                        item4.name,
                        item5.name,
                        item6.name,
                    ],
                )
        else:
            where_strat = typing.get_args(types[key])[1]
            if where_strat == WhereStrat.match:
                where = where & getattr(Build, key).in_(vals)
            else:  # where_strat == WhereStrat.range:
                tmp = getattr(Build, key)
                where = where & (vals[0] <= tmp) & (tmp <= vals[1])

    query = (
        Build.select(Build, relic1, relic2, item1, item2, item3, item4, item5, item6)
        .join_from(Build, relic1, pw.JOIN.LEFT_OUTER, Build.relic1)
        .join_from(Build, relic2, pw.JOIN.LEFT_OUTER, Build.relic2)
        .join_from(Build, item1, pw.JOIN.LEFT_OUTER, Build.item1)
        .join_from(Build, item2, pw.JOIN.LEFT_OUTER, Build.item2)
        .join_from(Build, item3, pw.JOIN.LEFT_OUTER, Build.item3)
        .join_from(Build, item4, pw.JOIN.LEFT_OUTER, Build.item4)
        .join_from(Build, item5, pw.JOIN.LEFT_OUTER, Build.item5)
        .join_from(Build, item6, pw.JOIN.LEFT_OUTER, Build.item6)
        .where(where)
        .order_by(
            Build.date.desc(),
            Build.match_id.desc(),
            Build.game_i.desc(),
            Build.win.desc(),
            Build.role.asc(),
        )
    )

    count = query.count() if page == 1 else None
    page_size = 10
    query = query.paginate(page, page_size)

    builds = []
    for build in query.iterator():
        build = playhouse.shortcuts.model_to_dict(build)
        build["date"] = build["date"].isoformat()
        build["game_length"] = build["game_length"].isoformat()
        match_url = shared.league_factory(build["league"]).match_url
        build["match_url"] = f'{match_url}/{build["match_id"]}'
        build["kda_ratio"] = f'{build["kda_ratio"]:.1f}'
        del build["match_id"]
        unmodify_relic_name(build["relic1"])
        unmodify_relic_name(build["relic2"])
        unmodify_item_name(build["item1"])
        unmodify_item_name(build["item2"])
        unmodify_item_name(build["item3"])
        unmodify_item_name(build["item4"])
        unmodify_item_name(build["item5"])
        unmodify_item_name(build["item6"])
        builds.append(build)

    return {"count": count, "builds": builds} if page == 1 else builds


EVOLVED_PREFIX = "Evolved "
UPGRADE_SUFFIX = " Upgrade"
GREATER_PREFIX = "Greater "


def unmodify_relic_name(relic: dict) -> None:
    if not relic or "name_was_modified" not in relic:
        return
    if relic["name_was_modified"] == 1:
        relic["name"] = relic["name"] + UPGRADE_SUFFIX
    elif relic["name_was_modified"] == 3:
        relic["name"] = GREATER_PREFIX + relic["name"]
    del relic["name_was_modified"]


def unmodify_item_name(item: dict) -> None:
    if not item or "name_was_modified" not in item:
        return
    if item["name_was_modified"] == 2:
        item["name"] = EVOLVED_PREFIX + item["name"]
    del item["name_was_modified"]


def no_img(item: Item) -> tuple:
    return item.id, item.name, item.name_was_modified, item.image_name
