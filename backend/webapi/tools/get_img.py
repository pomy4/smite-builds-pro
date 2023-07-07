import base64
import sys

from backend.webapi.models import Item, db


def main() -> None:
    pk = int(sys.argv[1])
    with db:
        item = Item.get_by_id(pk)
    image_data = base64.b64decode(item.image_data)
    with open(f"{pk}.jpg", "wb") as f:
        f.write(image_data)


if __name__ == "__main__":
    main()
