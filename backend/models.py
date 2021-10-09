from peewee import *
from peewee import Expression
from playhouse.shortcuts import model_to_dict, dict_to_model
import datetime
import urllib.request
import urllib.error
import time
import enum
import typing

spl_matches_url = 'https://www.smiteproleague.com/matches'
cdn_images_url = 'https://webcdn.hirezstudios.com/smite/item-icons'

evolved_prefix = 'Evolved '
upgrade_suffix = ' Upgrade'

min_request_delay = 0.25

STR_MAX_LEN = 30
PAGE_SIZE = 10

class MyError(Exception):
    pass

db = SqliteDatabase('backend.db')

class Base(Model):
    class Meta:
        legacy_table_names = False
        database = db

class Item(Base):
    name = CharField(30)
    name_was_modified = SmallIntegerField()
    image_name = CharField(30)
    image_data = BlobField(null=True)
    class Meta:
        indexes = (
            (('name', 'name_was_modified', 'image_name', 'image_data'), True),
        )

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
        indexes = (
            (('match_id', 'game_i', 'player1'), True),
        )

def get_match_ids(phase):
    return [b[0] for b in Build.select(Build.match_id).where(Build.phase == phase).distinct().tuples()]

def get_options():
    res = {}
    res['season'] = [b[0] for b in Build.select(Build.season).distinct().order_by(Build.season.asc()).tuples()]
    res['league'] = [b[0] for b in Build.select(Build.league).distinct().order_by(Build.league.asc()).tuples()]
    res['phase'] = [b[0] for b in Build.select(Build.phase).distinct().order_by(Build.phase.asc()).tuples()]
    res['win'] = [b[0] for b in Build.select(Build.win).distinct().order_by(Build.win.desc()).tuples()]
    res['role'] = [b[0] for b in Build.select(Build.role).distinct().order_by(Build.role.asc()).tuples()]
    res['team1'] = [b[0] for b in Build.select(Build.team1).distinct().order_by(Build.team1.asc()).tuples()]
    res['player1'] = [b[0] for b in Build.select(Build.player1).distinct().order_by(Build.player1.asc()).tuples()]
    res['god1'] = [b[0] for b in Build.select(Build.god1).distinct().order_by(Build.god1.asc()).tuples()]
    res['team2'] = [b[0] for b in Build.select(Build.team2).distinct().order_by(Build.team2.asc()).tuples()]
    res['player2'] = [b[0] for b in Build.select(Build.player2).distinct().order_by(Build.player2.asc()).tuples()]
    res['god2'] = [b[0] for b in Build.select(Build.god2).distinct().order_by(Build.god2.asc()).tuples()]
    res['relic'] = [b[0] for b in (
        Build.select(Item.name).join(Item, on=Build.relic1) |
        Build.select(Item.name).join(Item, on=Build.relic2).order_by(Item.name.asc())).tuples()]
    res['item'] = [b[0] for b in (
        Build.select(Item.name).join(Item, on=Build.item1) |
        Build.select(Item.name).join(Item, on=Build.item2) | # type: ignore
        Build.select(Item.name).join(Item, on=Build.item3) | # type: ignore
        Build.select(Item.name).join(Item, on=Build.item4) | # type: ignore
        Build.select(Item.name).join(Item, on=Build.item5) | # type: ignore
        Build.select(Item.name).join(Item, on=Build.item6).order_by(Item.name.asc())).tuples()]
    return res

def no_img(item):
    return item.id, item.name, item.name_was_modified, item.image_name

def unmodify_relic_name(relic):
    if relic and relic['name_was_modified'] == 1:
        relic['name'] = relic['name'] + upgrade_suffix
        del relic['name_was_modified']

def unmodify_item_name(item):
    if item and item['name_was_modified'] == 2:
        item['name'] = evolved_prefix + item['name']
        del item['name_was_modified']

class WhereStrat(enum.Enum):
    match = enum.auto()
    range = enum.auto()

def get_builds(builds_request):
    Relic1, Relic2, Item1, Item2 = Item.alias(), Item.alias(), Item.alias(), Item.alias()
    Item3, Item4, Item5, Item6 = Item.alias(), Item.alias(), Item.alias(), Item.alias()

    where = Expression(True, '=', True)
    types = typing.get_type_hints(builds_request, include_extras=True)
    for key, vals in vars(builds_request).items():
        if not vals:
            continue
        if key == 'page':
            page = vals[0]
        elif key == 'relic':
            for relic in vals:
                where = where & Expression(relic, 'IN', [Relic1.name, Relic2.name])
        elif key == 'item':
            for item in vals:
                where = where & Expression(item, 'IN', [Item1.name, Item2.name,
                    Item3.name, Item4.name, Item5.name, Item6.name])
        else:
            where_strat = typing.get_args(types[key])[1]
            if where_strat == WhereStrat.match:
                where = where & getattr(Build, key).in_(vals)
            else: # where_strat == WhereStrat.range:
                raise NotImplementedError

    query = Build.select(Build, *no_img(Relic1), *no_img(Relic2),
            *no_img(Item1), *no_img(Item2), *no_img(Item3),
            *no_img(Item4), *no_img(Item5), *no_img(Item6)) \
        .join_from(Build, Relic1, JOIN.LEFT_OUTER, Build.relic1) \
        .join_from(Build, Relic2, JOIN.LEFT_OUTER, Build.relic2) \
        .join_from(Build, Item1, JOIN.LEFT_OUTER, Build.item1) \
        .join_from(Build, Item2, JOIN.LEFT_OUTER, Build.item2) \
        .join_from(Build, Item3, JOIN.LEFT_OUTER, Build.item3) \
        .join_from(Build, Item4, JOIN.LEFT_OUTER, Build.item4) \
        .join_from(Build, Item5, JOIN.LEFT_OUTER, Build.item5) \
        .join_from(Build, Item6, JOIN.LEFT_OUTER, Build.item6) \
        .where(where) \
        .order_by(Build.date.desc(), Build.match_id.desc(), Build.game_i.desc(),
            Build.win.desc(), Build.role.asc())
    if page == 1:
        count = query.count()
    query = query.paginate(page, PAGE_SIZE)
    builds = []
    for build in query.iterator():
        build = model_to_dict(build)
        build['date'] = build['date'].isoformat()
        build['game_length'] = build['game_length'].strftime('%M:%S')
        build['match_url'] = f'{spl_matches_url}/{build["match_id"]}'
        build['kda_ratio'] = f'{build["kda_ratio"]:.1f}'
        del build['match_id']
        unmodify_relic_name(build['relic1'])
        unmodify_relic_name(build['relic2'])
        unmodify_item_name(build['item1'])
        unmodify_item_name(build['item2'])
        unmodify_item_name(build['item3'])
        unmodify_item_name(build['item4'])
        unmodify_item_name(build['item5'])
        unmodify_item_name(build['item6'])
        builds.append(build)
    return {'count': count, 'builds': builds} if page == 1 else builds

def request_delay(start):
    end = time.time()
    time_spent = end - start
    time_remaining = min_request_delay - time_spent
    if time_remaining > 0:
        time.sleep(time_remaining)

def post_builds(builds_request):
    # Uniquerize items based upon name and image name.
    today = datetime.date.today()
    items_request = dict()
    for build in builds_request:
        for name, image_name in build['relics']:
            items_request[(name, image_name)] = True
        for name, image_name in build['items']:
            items_request[(name, image_name)] = False
    with db.atomic():
        # Create or retrieve items.
        for (name, image_name), is_relic in items_request.items():
            modified_name = name
            name_was_modified = 0
            if is_relic and name.endswith(upgrade_suffix):
                modified_name = name[:-len(upgrade_suffix)]
                name_was_modified = 1
            elif not is_relic and name.startswith(evolved_prefix):
                modified_name = name[len(evolved_prefix):]
                name_was_modified = 2
            start = time.time()
            try:
                request = urllib.request.Request(f'{cdn_images_url}/{image_name}', headers={'User-Agent': 'Mozilla'})
                with urllib.request.urlopen(request) as f:
                    image_data = f.read()
            except urllib.error.URLError:
                image_data = None
            request_delay(start)
            item, _ = Item.get_or_create(name=modified_name, name_was_modified=name_was_modified,
                image_name=image_name, image_data=image_data)
            items_request[(name, image_name)] = item.id
        # Create builds.
        for build in builds_request:
            build['game_length'] = datetime.time(minute=build['minutes'], second=build['seconds'])
            if not build.get('year'):
                build['year'] = today.year
            if not build.get('season'):
                season = today.year - 2013
                if today.month <= 2:
                    season -= 1
                build['season'] = max(season, 0)
            try:
                build['date'] = datetime.date(year=build['year'], month=build['month'], day=build['day'])
            except ValueError:
                raise MyError('At least one of the builds has an invalid date.')
            del build['minutes'], build['seconds'], build['year'], build['month'], build['day']
            for i, (name, image_name) in enumerate(build['relics'], 1):
                build[f'relic{i}'] = items_request[(name, image_name)]
            for i, (name, image_name) in enumerate(build['items'], 1):
                build[f'item{i}'] = items_request[(name, image_name)]
            del build['relics'], build['items']
        try:
            # This is done one by one, since for some reason bulk insertion
            # sometimes causes silent corruption of data (!).
            for build in builds_request:
                Build.create(**build)
        except IntegrityError:
            raise MyError('At least one of the builds is already in the database.')

if __name__ == '__main__':
    tables = [Item, Build]
    db.connect()
    db.drop_tables(tables)
    db.create_tables(tables)
    db.close()
