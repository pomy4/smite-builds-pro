from peewee import *
import datetime

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
    league = CharField(30)
    phase = CharField(30)
    date = DateField()
    match_id = IntegerField()
    game_i = SmallIntegerField()
    win = BooleanField()
    game_length = TimeField()
    kills = SmallIntegerField()
    deaths = SmallIntegerField()
    assists = SmallIntegerField()
    role = CharField(30, index=True)
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
    class Meta:
        indexes = (
            (('match_id', 'game_i', 'player1'), True),
        )

def get_last_match_id(phase):
    query = Build.select(fn.MAX(Build.match_id)).where(Build.phase == phase)
    return query.scalar()

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
            build['date'] = datetime.date(year=build['year'], month=build['month'], day=build['day'])
            del build['minutes'], build['seconds'], build['year'], build['month'], build['day']
            for i, (short, long) in enumerate(build['relics'], 1):
                build[f'relic{i}'] = items_request[(short, long)]
            for i, (short, long) in enumerate(build['items'], 1):
                build[f'item{i}'] = items_request[(short, long)]
            del build['relics'], build['items']
        try:
            Build.insert_many(builds_request).execute()
            return True
        except IntegrityError:
            return False

if __name__ == '__main__':
    tables = [Item, Build]
    db.connect()
    db.drop_tables(tables)
    db.create_tables(tables)
    db.close()
