import base64
import sys

import sqlalchemy as sa
import sqlalchemy.orm as sao

from backend.webapi.models import Image, Item, db_session


def main() -> None:
    item_id = int(sys.argv[1])
    with db_session():
        item = db_session.scalars(
            sa.select(Item)
            .where(Item.id == item_id)
            .join(Image, Item.image_id == Image.id)
            .options(sao.contains_eager(Item.image))
        ).one()
    assert item.image is not None
    image_data = base64.b64decode(item.image.data)
    with open(f"{item_id}.jpg", "wb") as f:
        f.write(image_data)


if __name__ == "__main__":
    main()
