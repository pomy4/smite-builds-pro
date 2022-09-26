import be.models
from be.models import Build, Item, LastChecked, LastModified

if __name__ == "__main__":
    tables = [Build, Item, LastChecked, LastModified]
    with be.models.db:
        be.models.db.drop_tables(tables)
        be.models.db.create_tables(tables)
