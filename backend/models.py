from peewee import *
import datetime

db = SqliteDatabase('backend.db')

class Base(Model):
    class Meta:
        legacy_table_names = False
        database = db

class Item(Base):
    short = CharField(30, unique=True)
    long = CharField(30)

class Build(Base):
    season = SmallIntegerField()
    league = CharField(30)
    phase = CharField(30)
    date = DateField()
    game_i = SmallIntegerField()
    match_id = IntegerField()
    win = BooleanField()
    game_length = TimeField()
    kills = SmallIntegerField()
    deaths = SmallIntegerField()
    assists = SmallIntegerField()
    role = CharField(30)
    god1 = CharField(30, index=True)
    player1 = CharField(30, index=True)
    team1 = CharField(30)
    god2 = CharField(30)
    player2 = CharField(30)
    team2 = CharField(30)
    relic1 = ForeignKeyField(Item, null=True)
    relic2 = ForeignKeyField(Item, null=True)
    item1 = ForeignKeyField(Item, null=True)
    item2 = ForeignKeyField(Item, null=True)
    item3 = ForeignKeyField(Item, null=True)
    item4 = ForeignKeyField(Item, null=True)
    item5 = ForeignKeyField(Item, null=True)
    item6 = ForeignKeyField(Item, null=True)

def get_last_match_id(phase):
    query = Build.select(fn.MAX(Build.match_id)).where(Build.phase == phase)
    return query.scalar()

def add_builds(builds_request):
    # Uniquerize items based upon short.
    today = datetime.date.today()
    items_request = dict()
    for build in builds_request:
        for short, long in build['relics']:
            items_request[short] = long
        for short, long in build['items']:
            items_request[short] = long
    items_db = dict()
    with db.atomic():
        # Create or retrieve items.
        for short, long in items_request.items():
            item, _ = Item.get_or_create(short=short, long=long)
            items_db[short] = item.id
        # Create builds.
        for build in builds_request:
            build['game_length'] = datetime.time(minute=build['minutes'], second=build['seconds'])
            if 'year' not in build:
                build['year'] = today.year
            if 'season' not in build:
                season = today.year - 2013
                if today.month <= 2:
                    season -= 1
                build['season'] = max(season, 0)
            build['date'] = datetime.date(year=build['year'], month=build['month'], day=build['day'])
            del build['minutes'], build['seconds'], build['year'], build['month'], build['day']
            for i, (short, _) in enumerate(build['relics'], 1):
                build[f'relic{i}'] = items_db[short]
            for i, (short, _) in enumerate(build['items'], 1):
                build[f'item{i}'] = items_db[short]
            del build['relics'], build['items']
        Build.insert_many(builds_request).execute()

if __name__ == '__main__':
    tables = [Item, Build]
    db.connect()
    db.drop_tables(tables)
    db.create_tables(tables)
    db.close()
