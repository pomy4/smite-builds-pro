import base64
import collections
import contextlib
import datetime
import enum
import io
import logging
import os
import time
import typing
import unicodedata
import urllib.error
import urllib.request
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Optional

import charybdis
import peewee as pw
import playhouse.shortcuts
from PIL import Image, UnidentifiedImageError

import shared

if TYPE_CHECKING:
    from be.backend import GetBuildsRequest, PostBuildRequest


class MyError(Exception):
    pass


# --------------------------------------------------------------------------------------
# LOGGING
# --------------------------------------------------------------------------------------

auto_fixes_logger = logging.getLogger("auto-fixes")
auto_fixes_game_context_default = "x-x"
auto_fixes_game_context: ContextVar[str] = ContextVar(
    "auto_fixes_game_context", default=auto_fixes_game_context_default
)


def setup_auto_fixes_logger() -> None:
    """
    Keeps track of inconsistencies in the input data that were automatically fixed,
    e.g. a player name with different casing or incorrect role such as Sub/Coach,
    but also inconsistencies which require manual fixing, e.g. a missing build.
    """

    def add_game(record: logging.LogRecord) -> bool:
        record.game = auto_fixes_game_context.get()
        return True

    handler = logging.FileHandler(
        "be/logs/auto_fixes.log", mode="a", encoding="utf8", errors="backslashreplace"
    )
    handler.setFormatter(logging.Formatter(shared.AUTO_FIXES_LOG_FORMAT))
    handler.addFilter(add_game)
    auto_fixes_logger.setLevel(logging.INFO)
    auto_fixes_logger.propagate = False
    auto_fixes_logger.addHandler(handler)


@contextlib.contextmanager
def log_curr_game(build: dict) -> Iterator[None]:
    game = f"{build['match_id']}-{build['game_i']}"
    auto_fixes_game_context.set(game)
    try:
        yield None
    except Exception as e:
        e.args = (f"Game: {game}", *e.args)
        raise
    finally:
        auto_fixes_game_context.set(auto_fixes_game_context_default)


# --------------------------------------------------------------------------------------
# DATABASE DEFINITION
# --------------------------------------------------------------------------------------


class DbVersion(enum.Enum):
    OLD = "0.old"
    ADD_VERSION_TABLE = "1.add_version_table"


DB_VERSIONS = list(DbVersion)

CURRENT_DB_VERSION = DB_VERSIONS[-1]

db_path = Path(__file__).parent / "backend.db"
db = pw.SqliteDatabase(db_path, autoconnect=False)


class Base(pw.Model):
    class Meta:
        legacy_table_names = False
        database = db


class LastModified(Base):
    data = pw.DateTimeField()


class LastChecked(Base):
    data = pw.CharField(100)


class Version(Base):
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


def update_version(new_data: DbVersion) -> None:
    # replace is an 'upsert'.
    Version.replace(id=1, data=new_data.value).execute()


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
        with log_curr_game(build):
            build["items"] = [
                (name, fix_image_name(image_name))
                for name, image_name in build["items"]
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

            image_data = get_image_or_none(image_name)

            if image_data is None and (
                backup_image_name := (BACKUP_IMAGE_NAMES).get(image_name)
            ):
                auto_fixes_logger.info(f"ImageBkp|{image_name} -> {backup_image_name}")
                # image_name is not updated here, so that if HiRez fixes the URL,
                # it will not create a new item in the database
                # (unless HiRez also changes the image).
                image_data = get_image_or_none(backup_image_name)

            if image_data is None:
                auto_fixes_logger.warning(f"Missing image: {image_name}")
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
                if today.month <= 2:
                    season -= 1
                build["season"] = max(season, 0)
            try:
                build["date"] = datetime.date(
                    year=build["year"], month=build["month"], day=build["day"]
                )
            except ValueError as e:
                raise MyError("At least one of the builds has an invalid date") from e
            with log_curr_game(build):
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

        fix_roles(builds)
        fix_gods(builds)

        try:
            # This is done one by one, since for some reason bulk insertion
            # sometimes causes silent corruption of data (!).
            for build in builds:
                Build.create(**build)
        except pw.IntegrityError as e:
            raise MyError(
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


def get_image_or_none(image_name: str) -> Optional[bytes]:
    start = time.time()
    try:
        ret = get_image(image_name)
    except urllib.error.URLError:
        ret = None
    shared.delay(0.25, start)
    return ret


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


BuildDict = dict

# --------------------------------------------------------------------------------------
# FIX ROLES
# --------------------------------------------------------------------------------------


def fix_roles(builds: list[BuildDict]) -> None:
    game_to_builds = collections.defaultdict(list)
    for build in builds:
        game_to_builds[(build["match_id"], build["game_i"])].append(build)

    for game_builds in game_to_builds.values():
        with log_curr_game(game_builds[0]):
            fix_roles_in_single_game(game_builds)


def fix_roles_in_single_game(builds: list[BuildDict]) -> None:
    team_to_builds = collections.defaultdict(list)
    for build in builds:
        team_to_builds[build["team1"]].append(build)

    teams = list(team_to_builds.keys())
    if len(teams) != 2:
        raise MyError(f"Teams must be two: {len(teams), teams}")

    team1, team2 = teams
    team1_builds, team2_builds = team_to_builds[team1], team_to_builds[team2]

    team1_fixed_builds, role_to_team1_build = fix_roles_in_single_team(team1_builds)
    team2_fixed_builds, role_to_team2_build = fix_roles_in_single_team(team2_builds)

    # The wrongly specified role almost certainly caused the fields god2 and player2
    # filled in updater to also be wrong, so we have to also fix them.
    fix_opp_fields(team1_fixed_builds, role_to_team2_build)
    fix_opp_fields(team2_fixed_builds, role_to_team1_build)


ALLOWED_ROLES = {"ADC", "Jungle", "Mid", "Solo", "Support"}


def fix_roles_in_single_team(
    builds: list[BuildDict],
) -> tuple[list[BuildDict], dict[str, BuildDict]]:
    """
    There are two types of issues that can happen in the input data:
    1) Build is missing - not much we can do with that.
    2) Build has the wrong role specified. This happen when there is a sub player,
    and there are two possible sub-issues:
    2a) Quite often their role will be specified as Sub or Coach, instead of their
    actual role.
    2b) This happened only once, but there was a sub that previously played for a
    different team, and their displayed role reflected their role in their previous
    team and not what they actually played. Thus there can be e.g. 2x Mids and 0x Solo.
    """
    if len(builds) > 5:
        raise MyError(f"Too many builds: {len(builds)}")

    correct_roles = []
    fixable_roles = []
    unfixable_roles = []

    MISSING_ROLE = "Missing data"
    for _ in range(5 - len(builds)):
        # Situation 1.
        unfixable_roles.append(MISSING_ROLE)

    role_to_builds = collections.defaultdict(list)
    for build in builds:
        role_to_builds[build["role"]].append(build)

    for role, role_builds in role_to_builds.items():
        if len(role_builds) > 2:
            unfixable_roles.append(role)
        elif len(role_builds) == 2:
            if role not in ALLOWED_ROLES:
                unfixable_roles.append(role)
            else:
                # Situation 2b.
                fixable_roles.append(role)
        else:
            if role not in ALLOWED_ROLES:
                # Situation 2a.
                fixable_roles.append(role)
            else:
                correct_roles.append(role)

    correct_role_to_build: dict[str, BuildDict] = {
        role: role_to_builds[role][0] for role in correct_roles
    }

    # We can only auto-fix when there is at most one (fixable) error.
    # If there is e.g. Coach instead of Solo and Sub instead of Mid, then we don't know
    # whether we should do Coach -> Solo and Sub -> Mid or Coach -> Mid and Sub -> Solo.
    if not (len(fixable_roles) == 1 and len(unfixable_roles) == 0):
        for role in fixable_roles + unfixable_roles:
            role_builds = role_to_builds[role] if role != MISSING_ROLE else []
            auto_fixes_logger.warning(f"Wrong role: {role} ({len(role_builds)})")
        return [], correct_role_to_build

    role_to_fix = fixable_roles[0]
    builds_to_fix = role_to_builds[role_to_fix]
    missing_roles = {role for role in ALLOWED_ROLES if role not in correct_roles}

    if role_to_fix not in ALLOWED_ROLES:
        # Situation 2a - easy.
        assert len(builds_to_fix) == 1
        assert len(missing_roles) == 1
        build_to_fix = builds_to_fix[0]
        missing_role = next(iter(missing_roles))
    else:
        # Situation 2b - more difficult, we have to decide which player is sub, and we
        # do that based on the number of games either player played with that team.
        assert len(builds_to_fix) == 2
        assert len(missing_roles) == 2
        assert role_to_fix in missing_roles
        missing_roles.remove(role_to_fix)
        missing_role = next(iter(missing_roles))
        build1, build2 = builds_to_fix
        count1 = get_player_count_with_team(build1)
        count2 = get_player_count_with_team(build2)
        if count1 < count2:
            build_to_fix = build1
        elif count1 > count2:
            build_to_fix = build2
        else:
            # If both played the same number, we stop here without auto-fixing.
            auto_fixes_logger.warning(f"Wrong role: {role_to_fix} (2) [{count1}]")
            return [], correct_role_to_build

    auto_fixes_logger.info(f"Role|{role_to_fix} -> {missing_role}")
    build_to_fix["role"] = missing_role
    correct_role_to_build[missing_role] = build_to_fix
    return [build_to_fix], correct_role_to_build


def get_player_count_with_team(build: BuildDict) -> int:
    return (
        Build.select()
        .where((Build.team1 == build["team1"]) & (Build.player1 == build["player1"]))
        .count()
    )


def fix_opp_fields(
    fixed_builds: list[BuildDict], role_to_opp_build: dict[str, BuildDict]
) -> None:
    for build in fixed_builds:
        role = build["role"]
        if role not in role_to_opp_build:
            # We don't need to log here, since the dictionary contains only correct
            # roles, and if a role is not there, then its error was already logged in
            # the function tasked with fixing roles.
            continue
        opp_build = role_to_opp_build[role]

        auto_fixes_logger.info(f"God2|{build['god2']} -> {opp_build['god1']}")
        build["god2"] = opp_build["god1"]
        auto_fixes_logger.info(f"Player2|{build['player2']} -> {opp_build['player1']}")
        build["player2"] = opp_build["player1"]


# --------------------------------------------------------------------------------------
# FIX GODS
# --------------------------------------------------------------------------------------


def fix_gods(builds: list[BuildDict]) -> None:
    suspicious_gods1 = []
    suspicious_gods2 = []
    for build_i, build in enumerate(builds):
        if contains_digits(build["god1"]):
            suspicious_gods1.append((build_i, build["god1"]))
        if contains_digits(build["god2"]):
            suspicious_gods2.append((build_i, build["god2"]))

    if not suspicious_gods1 and not suspicious_gods2:
        return

    try:
        newest_god = get_newest_god()
    except Exception:
        auto_fixes_logger.warning(
            "Failed to get newest god from Hi-Rez API", exc_info=True
        )
        for build_i, god in suspicious_gods1:
            auto_fixes_logger.warning(f"Suspicious god1: {god} ({build_i})")
        for build_i, god in suspicious_gods2:
            auto_fixes_logger.warning(f"Suspicious god2: {god} ({build_i})")
        return

    for build_i, old_god in suspicious_gods1:
        auto_fixes_logger.info(f"God1|{old_god} -> {newest_god}")
        builds[build_i]["god1"] = newest_god
    for build_i, old_god in suspicious_gods2:
        auto_fixes_logger.info(f"God2|{old_god} -> {newest_god}")
        builds[build_i]["god2"] = newest_god


def contains_digits(s: str) -> bool:
    return any("0" <= c <= "9" for c in s)


def get_newest_god() -> str:
    api = charybdis.Api(
        base_url=charybdis.Api.SMITE_PC_URL,
        dev_id=os.getenv(shared.SMITE_DEV_ID),
        auth_key=os.getenv(shared.SMITE_AUTH_KEY),
    )
    gods = api.call_method("getgods", "1")
    newest_god_candidates = [god["Name"] for god in gods if god["latestGod"] == "y"]
    if len(newest_god_candidates) != 1:
        raise RuntimeError(
            f"Failed to ascertain which god is newest: {newest_god_candidates}"
        )
    return newest_god_candidates[0]


def are_hirez_api_credentials_set() -> bool:
    return (
        os.getenv(shared.SMITE_DEV_ID) is not None
        and os.getenv(shared.SMITE_AUTH_KEY) is not None
    )
