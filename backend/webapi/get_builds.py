import enum
import typing as t

import sqlalchemy as sa
import sqlalchemy.orm as sao

from backend.shared import league_factory
from backend.webapi.models import Build, BuildItem, Item, db_session

if t.TYPE_CHECKING:
    from backend.webapi.webapi import GetBuildsRequest


class WhereStrat(enum.Enum):
    match = enum.auto()
    range = enum.auto()


def get_builds(builds_query: "GetBuildsRequest") -> t.Any:
    where = [sa.true() == sa.true()]
    types = t.get_type_hints(builds_query, include_extras=True)
    page = 1

    for key, vals in vars(builds_query).items():
        if not vals:
            continue
        if key == "page":
            page = vals[0]
        elif key in ["relic", "item"]:
            is_relic = key == "relic"
            for val in vals:
                subq = (
                    sa.select(BuildItem.build_id)
                    .join(Item, BuildItem.item_id == Item.id)
                    .where(sa.and_(Item.is_relic.is_(is_relic), Item.name == val))
                    .scalar_subquery()
                )
                where.append(Build.id.in_(subq))
        else:
            where_strat = t.get_args(types[key])[1]
            if where_strat == WhereStrat.match:
                where.append(getattr(Build, key).in_(vals))
            else:  # where_strat == WhereStrat.range:
                tmp = getattr(Build, key)
                where.append(vals[0] <= tmp)
                where.append(tmp <= vals[1])

    if page != 1:
        count = None
    else:
        count = db_session.scalars(
            sa.select(sa.func.count(Build.id)).where(sa.and_(*where))
        ).one()

    page_size = 10

    build_order_by: list[t.Any] = [
        Build.date.desc(),
        Build.match_id.desc(),
        Build.game_i.desc(),
        Build.win.desc(),
        Build.role.asc(),
    ]

    final_subq = (
        sa.select(Build.id)
        .where(sa.and_(*where))
        .order_by(*build_order_by)
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).scalar_subquery()

    builds_iter = db_session.scalars(
        sa.select(Build)
        .where(Build.id.in_(final_subq))
        .outerjoin(BuildItem, Build.id == BuildItem.build_id)
        .join(Item, BuildItem.item_id == Item.id)
        .order_by(*build_order_by)
        .options(sao.contains_eager(Build.build_items, BuildItem.item))
    ).unique()

    build_dicts = []
    for build in builds_iter:
        build_dict = build.asdict()
        build_dict["date"] = build.date.isoformat()
        build_dict["game_length"] = build.game_length.isoformat()
        match_url = league_factory(build.league).match_url
        build_dict["match_url"] = f"{match_url}/{build.match_id}"
        build_dict["kda_ratio"] = f"{build.kda_ratio:.1f}"

        build_dict["relics"] = [None] * 2
        build_dict["items"] = [None] * 6
        for build_item in build.build_items:
            item = build_item.item
            item_dict: dict[str, t.Any] = {}
            item_dict["name"] = unmodify_item_name(item.name, item.name_was_modified)
            item_dict["image_name"] = item.image_name
            item_dict["image_data"] = item.image_data
            key = "relics" if item.is_relic else "items"
            build_dict[key][build_item.index] = item_dict

        build_dicts.append(build_dict)

    return {"count": count, "builds": build_dicts} if page == 1 else build_dicts


EVOLVED_PREFIX = "Evolved "
UPGRADE_SUFFIX = " Upgrade"
GREATER_PREFIX = "Greater "


def unmodify_item_name(name: str, name_was_modified: int) -> str:
    if name_was_modified == 1:
        return name + UPGRADE_SUFFIX
    elif name_was_modified == 2:
        return EVOLVED_PREFIX + name
    elif name_was_modified == 3:
        return GREATER_PREFIX + name
    else:
        return name


def no_img(item: Item) -> tuple:
    return item.id, item.name, item.name_was_modified, item.image_name
