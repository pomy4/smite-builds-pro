import enum

import peewee as pw

from shared import STORAGE_DIR


class DbVersion(enum.Enum):
    OLD = "0.old"
    ADD_VERSION_TABLE = "1.add_version_table"

    def __init__(self, value: str) -> None:
        self.index = int(value.split(".")[0])


CURRENT_DB_VERSION = list(DbVersion)[-1]

db_path = STORAGE_DIR / "backend.db"
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
