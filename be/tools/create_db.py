from models import Build, Item, LastChecked, LastModified, db

if __name__ == "__main__":
    tables = [LastModified, LastChecked, Item, Build]
    db.connect()
    db.drop_tables(tables)
    db.create_tables(tables)
    db.close()
