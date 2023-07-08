import base64
import sys

import sqlalchemy as sa

from backend.webapi.models import Item, db_session


def main() -> None:
    item_id = int(sys.argv[1])
    with db_session():
        item = db_session.scalars(sa.select(Item).where(Item.id == item_id)).one()
    assert item.image_data is not None
    image_data = base64.b64decode(item.image_data)
    with open(f"{item_id}.jpg", "wb") as f:
        f.write(image_data)


if __name__ == "__main__":
    main()
