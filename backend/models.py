from peewee import *
from peewee import Expression
from playhouse.shortcuts import model_to_dict, dict_to_model
import datetime

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
    short = CharField(30)
    long = CharField(30)
    class Meta:
        indexes = (
            (('short', 'long'), True),
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

def get_select_options():
    res = {}
    res['seasons'] = [b[0] for b in Build.select(Build.season).distinct().order_by(Build.season.asc()).tuples()]
    res['leagues'] = [b[0] for b in Build.select(Build.league).distinct().order_by(Build.league.asc()).tuples()]
    res['phases'] = [b[0] for b in Build.select(Build.phase).distinct().order_by(Build.phase.asc()).tuples()]
    res['wins'] = [b[0] for b in Build.select(Build.win).distinct().order_by(Build.win.desc()).tuples()]
    res['roles'] = [b[0] for b in Build.select(Build.role).distinct().order_by(Build.role.asc()).tuples()]
    res['team1s'] = [b[0] for b in Build.select(Build.team1).distinct().order_by(Build.team1.asc()).tuples()]
    res['player1s'] = [b[0] for b in Build.select(Build.player1).distinct().order_by(Build.player1.asc()).tuples()]
    res['god1s'] = [b[0] for b in Build.select(Build.god1).distinct().order_by(Build.god1.asc()).tuples()]
    res['team2s'] = [b[0] for b in Build.select(Build.team2).distinct().order_by(Build.team2.asc()).tuples()]
    res['player2s'] = [b[0] for b in Build.select(Build.player2).distinct().order_by(Build.player2.asc()).tuples()]
    res['god2s'] = [b[0] for b in Build.select(Build.god2).distinct().order_by(Build.god2.asc()).tuples()]
    res['relics'] = [b[0] for b in (
        Build.select(Item.long).join(Item, on=Build.relic1) |
        Build.select(Item.long).join(Item, on=Build.relic2).order_by(Item.long.asc())).tuples()]
    res['items'] = [b[0] for b in (
        Build.select(Item.long).join(Item, on=Build.item1) |
        Build.select(Item.long).join(Item, on=Build.item2) | # type: ignore
        Build.select(Item.long).join(Item, on=Build.item3) | # type: ignore
        Build.select(Item.long).join(Item, on=Build.item4) | # type: ignore
        Build.select(Item.long).join(Item, on=Build.item5) | # type: ignore
        Build.select(Item.long).join(Item, on=Build.item6).order_by(Item.long.asc())).tuples()]
    return res

def get_builds(page, **builds_request):
    where = Expression(True, '=', True)
    if seasons := builds_request['seasons']:
        where = where & Build.season.in_(seasons)
    if leagues := builds_request['leagues']:
        where = where & Build.league.in_(leagues)
    if phases := builds_request['phases']:
        where = where & Build.phase.in_(phases)
    if wins := builds_request['wins']:
        where = where & Build.win.in_(wins)
    if roles := builds_request['roles']:
        where = where & Build.role.in_(roles)
    if team1s := builds_request['team1s']:
        where = where & Build.team1.in_(team1s)
    if player1s := builds_request['player1s']:
        where = where & Build.player1.in_(player1s)
    if god1s := builds_request['god1s']:
        where = where & Build.god1.in_(god1s)
    if team2s := builds_request['team2s']:
        where = where & Build.team2.in_(team2s)
    if player2s := builds_request['player2s']:
        where = where & Build.player2.in_(player2s)
    if god2s := builds_request['god2s']:
        where = where & Build.god2.in_(god2s)
    Relic1, Relic2, Item1, Item2 = Item.alias(), Item.alias(), Item.alias(), Item.alias()
    Item3, Item4, Item5, Item6 = Item.alias(), Item.alias(), Item.alias(), Item.alias()
    query = Build.select(Build, Relic1, Relic2, Item1, Item2, Item3, Item4, Item5, Item6) \
        .join_from(Build, Relic1, JOIN.LEFT_OUTER, Build.relic1) \
        .join_from(Build, Relic2, JOIN.LEFT_OUTER, Build.relic2) \
        .join_from(Build, Item1, JOIN.LEFT_OUTER, Build.item1) \
        .join_from(Build, Item2, JOIN.LEFT_OUTER, Build.item1) \
        .join_from(Build, Item3, JOIN.LEFT_OUTER, Build.item1) \
        .join_from(Build, Item4, JOIN.LEFT_OUTER, Build.item1) \
        .join_from(Build, Item5, JOIN.LEFT_OUTER, Build.item1) \
        .join_from(Build, Item6, JOIN.LEFT_OUTER, Build.item1) \
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
        build['match_url'] = f'https://www.smiteproleague.com/matches/{build["match_id"]}'
        del build['match_id']
        builds.append(build)
    return {'count': count, 'builds': builds} if page == 1 else builds

def add_builds(builds_request):
    # Uniquerize items based upon short and long.
    today = datetime.date.today()
    items_request = dict()
    for build in builds_request:
        for short, long in build['relics']:
            items_request[(short, long)] = None
        for short, long in build['items']:
            items_request[(short, long)] = None
    with db.atomic():
        # Create or retrieve items.
        for (short, long) in items_request.keys():
            item, _ = Item.get_or_create(short=short, long=long)
            items_request[(short, long)] = item.id
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
            for i, (short, long) in enumerate(build['relics'], 1):
                build[f'relic{i}'] = items_request[(short, long)]
            for i, (short, long) in enumerate(build['items'], 1):
                build[f'item{i}'] = items_request[(short, long)]
            del build['relics'], build['items']
        try:
            for batch in chunked(builds_request, 100):
                Build.insert_many(batch).execute()
        except IntegrityError:
            raise MyError('At least one of the builds is already in the database.')

if __name__ == '__main__':
    tables = [Item, Build]
    db.connect()
    db.drop_tables(tables)
    db.create_tables(tables)
    db.close()
