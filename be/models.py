import base64
import datetime
import enum
import io
import time
import typing
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import peewee as pw
import playhouse.shortcuts
from PIL import Image, UnidentifiedImageError

import shared

if TYPE_CHECKING:
    from be.backend import GetBuildsRequest, PostBuildRequest


class MyError(Exception):
    pass


# --------------------------------------------------------------------------------------
# TABLES
# --------------------------------------------------------------------------------------


db = pw.SqliteDatabase(Path(__file__).parent / "backend.db", autoconnect=False)


class Base(pw.Model):
    class Meta:
        legacy_table_names = False
        database = db


class LastModified(Base):
    data = pw.DateTimeField()


class LastChecked(Base):
    data = pw.CharField(100)


STR_MAX_LEN = 50


class Item(Base):
    name = pw.CharField(STR_MAX_LEN)
    name_was_modified = pw.SmallIntegerField()
    image_name = pw.CharField(STR_MAX_LEN)
    image_data = pw.BlobField(null=True)

    class Meta:
        indexes = ((("name", "name_was_modified", "image_name", "image_data"), True),)


class Build(Base):
    season = pw.SmallIntegerField()
    league = pw.CharField(STR_MAX_LEN)
    phase = pw.CharField(STR_MAX_LEN)
    date = pw.DateField()
    match_id = pw.IntegerField()
    game_i = pw.SmallIntegerField()
    win = pw.BooleanField()
    game_length = pw.TimeField()
    kda_ratio = pw.FloatField()
    kills = pw.SmallIntegerField()
    deaths = pw.SmallIntegerField()
    assists = pw.SmallIntegerField()
    role = pw.CharField(STR_MAX_LEN, index=True)
    god1 = pw.CharField(STR_MAX_LEN, index=True)
    player1 = pw.CharField(STR_MAX_LEN, index=True)
    team1 = pw.CharField(STR_MAX_LEN)
    god2 = pw.CharField(STR_MAX_LEN)
    player2 = pw.CharField(STR_MAX_LEN)
    team2 = pw.CharField(STR_MAX_LEN)
    relic1 = pw.ForeignKeyField(Item, null=True)
    relic2 = pw.ForeignKeyField(Item, null=True)
    item1 = pw.ForeignKeyField(Item, null=True)
    item2 = pw.ForeignKeyField(Item, null=True)
    item3 = pw.ForeignKeyField(Item, null=True)
    item4 = pw.ForeignKeyField(Item, null=True)
    item5 = pw.ForeignKeyField(Item, null=True)
    item6 = pw.ForeignKeyField(Item, null=True)

    class Meta:
        indexes = ((("match_id", "game_i", "player1"), True),)


# --------------------------------------------------------------------------------------
# SIMPLE QUERIES
# --------------------------------------------------------------------------------------


def get_last_modified() -> Optional[datetime.datetime]:
    try:
        return LastModified.get().data
    except LastModified.DoesNotExist:
        return None


def update_last_modified(new_data: datetime.datetime) -> None:
    # Peewee + SQLite does not support timezone aware datetimes.
    LastModified.replace(id=1, data=new_data.replace(tzinfo=None)).execute()


def get_last_checked() -> Optional[str]:
    try:
        return LastChecked.get().data
    except LastChecked.DoesNotExist:
        return None


def update_last_checked(new_data: str) -> None:
    LastChecked.replace(id=1, data=new_data).execute()


def get_match_ids(phase: str) -> list[int]:
    return [
        b.match_id
        for b in Build.select(Build.match_id).where(Build.phase == phase).distinct()
    ]


# --------------------------------------------------------------------------------------
# GET OPTIONS
# --------------------------------------------------------------------------------------


def get_options() -> dict:
    res = {}
    res["season"] = [
        b.season
        for b in Build.select(Build.season).distinct().order_by(Build.season.asc())
    ]
    res["league"] = [
        b.league
        for b in Build.select(Build.league).distinct().order_by(Build.league.asc())
    ]
    res["phase"] = [
        b.phase
        for b in Build.select(Build.phase).distinct().order_by(Build.phase.asc())
    ]
    res["date"] = [
        date.isoformat()
        if date
        else datetime.date(year=2012, month=5, day=31).isoformat()
        for date in Build.select(pw.fn.MIN(Build.date), pw.fn.MAX(Build.date)).scalar(
            as_tuple=True
        )
    ]
    res["game_i"] = [
        b.game_i
        for b in Build.select(Build.game_i).distinct().order_by(Build.game_i.asc())
    ]
    res["win"] = [
        b.win for b in Build.select(Build.win).distinct().order_by(Build.win.desc())
    ]
    res["game_length"] = [
        time.isoformat() if time else datetime.time().isoformat()
        for time in Build.select(
            pw.fn.MIN(Build.game_length), pw.fn.MAX(Build.game_length)
        ).scalar(as_tuple=True)
    ]
    res["kda_ratio"] = [
        kda_ratio if kda_ratio else 0
        for kda_ratio in Build.select(
            pw.fn.MIN(Build.kda_ratio), pw.fn.MAX(Build.kda_ratio)
        ).scalar(as_tuple=True)
    ]
    res["kills"] = [
        kills if kills else 0
        for kills in Build.select(
            pw.fn.MIN(Build.kills), pw.fn.MAX(Build.kills)
        ).scalar(as_tuple=True)
    ]
    res["deaths"] = [
        deaths if deaths else 0
        for deaths in Build.select(
            pw.fn.MIN(Build.deaths), pw.fn.MAX(Build.deaths)
        ).scalar(as_tuple=True)
    ]
    res["assists"] = [
        assists if assists else 0
        for assists in Build.select(
            pw.fn.MIN(Build.assists), pw.fn.MAX(Build.assists)
        ).scalar(as_tuple=True)
    ]
    res["role"] = [
        b.role for b in Build.select(Build.role).distinct().order_by(Build.role.asc())
    ]
    res["team1"] = [
        b.team1
        for b in Build.select(Build.team1).distinct().order_by(Build.team1.asc())
    ]
    res["player1"] = [
        b.player1
        for b in Build.select(Build.player1)
        .distinct()
        .order_by(pw.fn.Upper(Build.player1).asc())
    ]
    res["god1"] = [
        b.god1 for b in Build.select(Build.god1).distinct().order_by(Build.god1.asc())
    ]
    res["team2"] = [
        b.team2
        for b in Build.select(Build.team2).distinct().order_by(Build.team2.asc())
    ]
    res["player2"] = [
        b.player2
        for b in Build.select(Build.player2)
        .distinct()
        .order_by(pw.fn.Upper(Build.player2).asc())
    ]
    res["god2"] = [
        b.god2 for b in Build.select(Build.god2).distinct().order_by(Build.god2.asc())
    ]
    res["relic"] = [
        b.relic1.name
        for b in (
            Build.select(Item.name).join(Item, on=Build.relic1)
            | Build.select(Item.name).join(Item, on=Build.relic2)
        ).order_by(Item.name.asc())
    ]
    res["item"] = [
        b.item1.name
        for b in (
            Build.select(Item.name).join(Item, on=Build.item1)
            | Build.select(Item.name).join(Item, on=Build.item2)
            | Build.select(Item.name).join(Item, on=Build.item3)
            | Build.select(Item.name).join(Item, on=Build.item4)
            | Build.select(Item.name).join(Item, on=Build.item5)
            | Build.select(Item.name).join(Item, on=Build.item6)
        ).order_by(Item.name.asc())
    ]
    return res


# --------------------------------------------------------------------------------------
# GET BUILDS
# --------------------------------------------------------------------------------------


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


# --------------------------------------------------------------------------------------
# POST BUILDS
# --------------------------------------------------------------------------------------


def post_builds(builds_: list["PostBuildRequest"]) -> None:
    # For now just work with dicts.
    builds = [build.dict() for build in builds_]

    # Uniquerize items based upon name and image name.
    items = {}
    for build in builds:
        build["items"] = [
            (name, fix_image_name(image_name)) for name, image_name in build["items"]
        ]
        for name, image_name in build["relics"]:
            items[(name, image_name)] = True
        for name, image_name in build["items"]:
            items[(name, image_name)] = False

    with db.atomic():
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

            start = time.time()
            image_data = get_image_or_none(image_name)
            shared.delay(0.25, start)

            if image_data is None:
                b64_image_data, was_compressed = None, False
            else:
                b64_image_data, was_compressed = compress_and_base64_image_or_none(
                    image_data
                )

            item, was_new = Item.get_or_create(
                name=modified_name,
                name_was_modified=name_was_modified,
                image_name=image_name,
                image_data=b64_image_data,
            )

            if image_data is not None and was_compressed and was_new:
                save_item_icon_to_archive(item, image_data)

            items[(name, image_name)] = item.id

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
                if today.month <= 2:
                    season -= 1
                build["season"] = max(season, 0)
            try:
                build["date"] = datetime.date(
                    year=build["year"], month=build["month"], day=build["day"]
                )
            except ValueError:
                raise MyError("At least one of the builds has an invalid date")
            build["player1"] = fix_player_name(build["player1"])
            build["player2"] = fix_player_name(build["player2"])
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

        try:
            # This is done one by one, since for some reason bulk insertion
            # sometimes causes silent corruption of data (!).
            for build in builds:
                Build.create(**build)
        except pw.IntegrityError:
            raise MyError("At least one of the builds is already in the database")


FIXED_IMAGE_NAMES = {
    "bloodsoaked-shroud.jpg": "blood-soaked-shroud.jpg",
    "pointed-shuriken.jpg": "8-pointed-shuriken.jpg",
    "faeblessed-hoops.jpg": "fae-blessed-hoops.jpg",
}


def fix_image_name(image_name: str) -> str:
    return FIXED_IMAGE_NAMES.get(image_name, image_name)


FIXED_PLAYER_NAMES = {
    "AwesomeJake408": "Awesomejake408",
    "LeMoGoW": "LeMoGow",
    "ErupTCrimson": "EruptCrimson",
    "ELLEON": "Elleon",
    "MastKiII": "MastkiII",
    "MagicFeet": "Magicfeet",
    "ChinFu": "Chinfu",
    "Calvìn": "Calvin",
    "Briz": "Brìz",
}


def fix_player_name(player_name: str) -> str:
    return FIXED_PLAYER_NAMES.get(player_name, player_name)


def get_image_or_none(image_name: str) -> Optional[bytes]:
    try:
        return get_image(image_name)
    except urllib.error.URLError:
        return None


def get_image(image_name: str) -> bytes:
    request = urllib.request.Request(
        f"{shared.IMG_URL}/{image_name}",
        headers={"User-Agent": "Mozilla"},
    )
    with urllib.request.urlopen(request) as f:
        return f.read()


def compress_and_base64_image_or_none(
    image_data: bytes,
) -> tuple[Optional[bytes], bool]:
    try:
        return compress_and_base64_image(image_data)
    # OSError can be thrown while saving as JPEG.
    except (UnidentifiedImageError, OSError):
        return None, False


def compress_and_base64_image(image_data: bytes) -> tuple[bytes, bool]:
    image = Image.open(io.BytesIO(image_data))
    min_side = min(image.size)

    if image.format != "JPEG" or min_side > 128:
        multiplier = min_side / 128
        new_size = round(image.size[0] / multiplier), round(image.size[1] / multiplier)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        if image.mode == "RGBA":
            image = image.convert("RGB")
        b = io.BytesIO()
        image.save(b, "JPEG")
        image_data = b.getvalue()
        was_compressed = True
    else:
        was_compressed = False

    return base64.b64encode(image_data), was_compressed


def save_item_icon_to_archive(item: Item, image_data: bytes) -> None:
    item_icons_archive_dir = Path(__file__).parent / "item_icons_archive"
    item_icons_archive_dir.mkdir(exist_ok=True)
    image_path = item_icons_archive_dir / f"{item.id}-{item.image_name}"
    image_path.write_bytes(image_data)
