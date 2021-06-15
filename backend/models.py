from peewee import *

db = SqliteDatabase('test.db')

class Base(Model):
    class Meta:
        legacy_table_names = False
        database = db

class Build(Base):
    player = CharField(30)
    role = CharField(30)
    god = CharField(30)

if __name__ == '__main__':
    tables = [Build]
    db.connect()
    db.drop_tables(tables)
    db.create_tables(tables)
    db.close()
