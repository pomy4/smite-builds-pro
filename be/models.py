import base64
import datetime
import enum
import io
import time
import typing
import urllib.error
import urllib.request
from pathlib import Path

from peewee import *
from peewee import Expression
from PIL import Image, UnidentifiedImageError
from playhouse.shortcuts import dict_to_model, model_to_dict

spl_matches_url = "https://www.smiteproleague.com/matches"
cdn_images_url = "https://webcdn.hirezstudios.com/smite/item-icons"

evolved_prefix = "Evolved "
upgrade_suffix = " Upgrade"
greater_prefix = "Greater "

min_request_delay = 0.25

STR_MAX_LEN = 50
PAGE_SIZE = 10


class MyError(Exception):
    pass


db = SqliteDatabase("backend.db", autoconnect=False)


class Base(Model):
    class Meta:
        legacy_table_names = False
        database = db


# Metadata tables.


class LastModified(Base):
    data = DateTimeField()


class LastChecked(Base):
    data = CharField(100)


# Data tables.


class Item(Base):
    name = CharField(STR_MAX_LEN)
    name_was_modified = SmallIntegerField()
    image_name = CharField(STR_MAX_LEN)
    image_data = BlobField(null=True)

    class Meta:
        indexes = ((("name", "name_was_modified", "image_name", "image_data"), True),)


class Build(Base):
    season = SmallIntegerField()
    league = CharField(STR_MAX_LEN)
    phase = CharField(STR_MAX_LEN)
    date = DateField()
    match_id = IntegerField()
    game_i = SmallIntegerField()
    win = BooleanField()
    game_length = TimeField()
    kda_ratio = FloatField()
    kills = SmallIntegerField()
    deaths = SmallIntegerField()
    assists = SmallIntegerField()
    role = CharField(STR_MAX_LEN, index=True)
    god1 = CharField(STR_MAX_LEN, index=True)
    player1 = CharField(STR_MAX_LEN, index=True)
    team1 = CharField(STR_MAX_LEN)
    god2 = CharField(STR_MAX_LEN)
    player2 = CharField(STR_MAX_LEN)
    team2 = CharField(STR_MAX_LEN)
    relic1 = ForeignKeyField(Item, null=True)
    relic2 = ForeignKeyField(Item, null=True)
    item1 = ForeignKeyField(Item, null=True)
    item2 = ForeignKeyField(Item, null=True)
    item3 = ForeignKeyField(Item, null=True)
    item4 = ForeignKeyField(Item, null=True)
    item5 = ForeignKeyField(Item, null=True)
    item6 = ForeignKeyField(Item, null=True)

    class Meta:
        indexes = ((("match_id", "game_i", "player1"), True),)


def get_last_modified():
    return LastModified.get_or_none()


def update_last_modified(new_data: datetime.datetime):
    # Peewee + SQLite does not support timezone aware datetimes.
    LastModified.replace(id=1, data=new_data.replace(tzinfo=None)).execute()


def get_last_checked():
    return LastChecked.get_or_none()


def update_last_checked(new_data: str):
    LastChecked.replace(id=1, data=new_data).execute()


def get_match_ids(phase):
    return [
        b[0]
        for b in Build.select(Build.match_id)
        .where(Build.phase == phase)
        .distinct()
        .tuples()
    ]


def get_options():
    res = {}
    res["season"] = [
        b[0]
        for b in Build.select(Build.season)
        .distinct()
        .order_by(Build.season.asc())
        .tuples()
    ]
    res["league"] = [
        b[0]
        for b in Build.select(Build.league)
        .distinct()
        .order_by(Build.league.asc())
        .tuples()
    ]
    res["phase"] = [
        b[0]
        for b in Build.select(Build.phase)
        .distinct()
        .order_by(Build.phase.asc())
        .tuples()
    ]
    res["date"] = [
        x.isoformat()
        for x in Build.select(fn.MIN(Build.date), fn.MAX(Build.date)).tuples()[0]
    ]
    res["game_i"] = [
        b[0]
        for b in Build.select(Build.game_i)
        .distinct()
        .order_by(Build.game_i.asc())
        .tuples()
    ]
    res["win"] = [
        b[0]
        for b in Build.select(Build.win).distinct().order_by(Build.win.desc()).tuples()
    ]
    res["game_length"] = [
        x.isoformat()
        for x in Build.select(
            fn.MIN(Build.game_length), fn.MAX(Build.game_length)
        ).tuples()[0]
    ]
    res["kda_ratio"] = Build.select(
        fn.MIN(Build.kda_ratio), fn.MAX(Build.kda_ratio)
    ).tuples()[0]
    res["kills"] = Build.select(fn.MIN(Build.kills), fn.MAX(Build.kills)).tuples()[0]
    res["deaths"] = Build.select(fn.MIN(Build.deaths), fn.MAX(Build.deaths)).tuples()[0]
    res["assists"] = Build.select(
        fn.MIN(Build.assists), fn.MAX(Build.assists)
    ).tuples()[0]
    res["role"] = [
        b[0]
        for b in Build.select(Build.role).distinct().order_by(Build.role.asc()).tuples()
    ]
    res["team1"] = [
        b[0]
        for b in Build.select(Build.team1)
        .distinct()
        .order_by(Build.team1.asc())
        .tuples()
    ]
    res["player1"] = [
        b[0]
        for b in Build.select(Build.player1)
        .distinct()
        .order_by(Build.player1.asc())
        .tuples()
    ]
    res["god1"] = [
        b[0]
        for b in Build.select(Build.god1).distinct().order_by(Build.god1.asc()).tuples()
    ]
    res["team2"] = [
        b[0]
        for b in Build.select(Build.team2)
        .distinct()
        .order_by(Build.team2.asc())
        .tuples()
    ]
    res["player2"] = [
        b[0]
        for b in Build.select(Build.player2)
        .distinct()
        .order_by(Build.player2.asc())
        .tuples()
    ]
    res["god2"] = [
        b[0]
        for b in Build.select(Build.god2).distinct().order_by(Build.god2.asc()).tuples()
    ]
    res["relic"] = [
        b[0]
        for b in (
            Build.select(Item.name).join(Item, on=Build.relic1)
            | Build.select(Item.name)
            .join(Item, on=Build.relic2)
            .order_by(Item.name.asc())
        ).tuples()
    ]
    res["item"] = [
        b[0]
        for b in (
            Build.select(Item.name).join(Item, on=Build.item1)
            | Build.select(Item.name).join(Item, on=Build.item2)
            | Build.select(Item.name).join(Item, on=Build.item3)  # type: ignore
            | Build.select(Item.name).join(Item, on=Build.item4)  # type: ignore
            | Build.select(Item.name).join(Item, on=Build.item5)  # type: ignore
            | Build.select(Item.name)  # type: ignore
            .join(Item, on=Build.item6)
            .order_by(Item.name.asc())
        ).tuples()
    ]
    return res


def no_img(item):
    return item.id, item.name, item.name_was_modified, item.image_name


def unmodify_relic_name(relic):
    if not relic or "name_was_modified" not in relic:
        return
    if relic["name_was_modified"] == 1:
        relic["name"] = relic["name"] + upgrade_suffix
    elif relic["name_was_modified"] == 3:
        relic["name"] = greater_prefix + relic["name"]
    del relic["name_was_modified"]


def unmodify_item_name(item):
    if not item or "name_was_modified" not in item:
        return
    if item["name_was_modified"] == 2:
        item["name"] = evolved_prefix + item["name"]
    del item["name_was_modified"]


class WhereStrat(enum.Enum):
    match = enum.auto()
    range = enum.auto()


def get_builds(builds_request):
    Relic1, Relic2, Item1, Item2, Item3, Item4, Item5, Item6 = (
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
        Item.alias(),
    )

    where = Expression(True, "=", True)
    types = typing.get_type_hints(builds_request, include_extras=True)
    for key, vals in vars(builds_request).items():
        if not vals:
            continue
        if key == "page":
            page = vals[0]
        elif key == "relic":
            for relic in vals:
                where = where & Expression(relic, "IN", [Relic1.name, Relic2.name])
        elif key == "item":
            for item in vals:
                where = where & Expression(
                    item,
                    "IN",
                    [
                        Item1.name,
                        Item2.name,
                        Item3.name,
                        Item4.name,
                        Item5.name,
                        Item6.name,
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
        Build.select(Build, Relic1, Relic2, Item1, Item2, Item3, Item4, Item5, Item6)
        .join_from(Build, Relic1, JOIN.LEFT_OUTER, Build.relic1)
        .join_from(Build, Relic2, JOIN.LEFT_OUTER, Build.relic2)
        .join_from(Build, Item1, JOIN.LEFT_OUTER, Build.item1)
        .join_from(Build, Item2, JOIN.LEFT_OUTER, Build.item2)
        .join_from(Build, Item3, JOIN.LEFT_OUTER, Build.item3)
        .join_from(Build, Item4, JOIN.LEFT_OUTER, Build.item4)
        .join_from(Build, Item5, JOIN.LEFT_OUTER, Build.item5)
        .join_from(Build, Item6, JOIN.LEFT_OUTER, Build.item6)
        .where(where)
        .order_by(
            Build.date.desc(),
            Build.match_id.desc(),
            Build.game_i.desc(),
            Build.win.desc(),
            Build.role.asc(),
        )
    )
    if page == 1:
        count = query.count()
    query = query.paginate(page, PAGE_SIZE)
    builds = []
    for build in query.iterator():
        build = model_to_dict(build)
        build["date"] = build["date"].isoformat()
        build["game_length"] = build["game_length"].isoformat()
        build["match_url"] = f'{spl_matches_url}/{build["match_id"]}'
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


def request_delay(start):
    end = time.time()
    time_spent = end - start
    time_remaining = min_request_delay - time_spent
    if time_remaining > 0:
        time.sleep(time_remaining)


def fix_image_name(image_name):
    if image_name == "bloodsoaked-shroud.jpg":
        return "blood-soaked-shroud.jpg"
    elif image_name == "pointed-shuriken.jpg":
        return "8-pointed-shuriken.jpg"
    elif image_name == "faeblessed-hoops.jpg":
        return "fae-blessed-hoops.jpg"
    else:
        return image_name


def fix_player_name(player_name):
    if player_name == "AwesomeJake408":
        return "Awesomejake408"
    else:
        return player_name


def post_builds(builds_request):
    # Uniquerize items based upon name and image name.
    today = datetime.date.today()
    items_request = dict()
    for build in builds_request:
        build["items"] = [
            (name, fix_image_name(image_name)) for name, image_name in build["items"]
        ]
        for name, image_name in build["relics"]:
            items_request[(name, image_name)] = True
        for name, image_name in build["items"]:
            items_request[(name, image_name)] = False

    with db.atomic():
        # Create or retrieve items.
        for (name, image_name), is_relic in items_request.items():
            modified_name = name
            name_was_modified = 0
            if is_relic and name.endswith(upgrade_suffix):
                modified_name = name[: -len(upgrade_suffix)]
                name_was_modified = 1
            elif not is_relic and name.startswith(evolved_prefix):
                modified_name = name[len(evolved_prefix) :]
                name_was_modified = 2
            elif is_relic and name.startswith(greater_prefix):
                modified_name = name[len(greater_prefix) :]
                name_was_modified = 3

            start = time.time()
            try:
                request = urllib.request.Request(
                    f"{cdn_images_url}/{image_name}", headers={"User-Agent": "Mozilla"}
                )
                with urllib.request.urlopen(request) as f:
                    image_data = f.read()
            except urllib.error.URLError:
                image_data = None
            request_delay(start)

            try:
                b64_image_data, was_compressed = compress_and_base64_image(image_data)
            # OSError can be thrown while saving as JPEG.
            except (UnidentifiedImageError, OSError):
                b64_image_data, was_compressed = None, False

            item, was_new = Item.get_or_create(
                name=modified_name,
                name_was_modified=name_was_modified,
                image_name=image_name,
                image_data=b64_image_data,
            )

            if was_compressed and was_new:
                save_item_icon_to_archive(item, image_data)

            items_request[(name, image_name)] = item.id

        # Create builds.
        for build in builds_request:
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
                raise MyError("At least one of the builds has an invalid date.")
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
                build[f"relic{i}"] = items_request[(name, image_name)]
            for i, (name, image_name) in enumerate(build["items"], 1):
                build[f"item{i}"] = items_request[(name, image_name)]
            del build["relics"], build["items"]
        try:
            # This is done one by one, since for some reason bulk insertion
            # sometimes causes silent corruption of data (!).
            for build in builds_request:
                Build.create(**build)
        except IntegrityError:
            raise MyError("At least one of the builds is already in the database.")


def compress_and_base64_image(image_data: bytes) -> typing.Tuple[bytes, bool]:
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
    item_icons_archive_dir = Path("item_icons_archive")
    item_icons_archive_dir.mkdir(exist_ok=True)
    image_path = item_icons_archive_dir / f"{item.id}-{item.image_name}"
    image_path.write_bytes(image_data)