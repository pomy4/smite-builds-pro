from peewee import *
from peewee import Expression
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
    res['roles'] = [b[0] for b in Build.select(Build.role).distinct().tuples()]
    res['god1s'] = [b[0] for b in Build.select(Build.god1).distinct().tuples()]
    return res

def get_builds(page, roles, god1s):
    where = Expression(True, '=', True)
    if roles:
        where = where & Build.role.in_(roles)
    if god1s:
        where = where & Build.god1.in_(god1s)
    return [b for b in Build.select().where(where).paginate(page, PAGE_SIZE).dicts()]

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
