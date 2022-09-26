import sys

import be.models
from be.models import Item


def images_to_base64():
    for item in Item.select():
        try:
            b64_image_data, was_compressed = be.models.compress_and_base64_image(
                item.image_data
            )
            if was_compressed:
                be.models.save_item_icon_to_archive(item, item.image_data)
            item.image_data = b64_image_data
            item.save()
        except Exception:
            print(be.models.no_img(item))
            raise


if __name__ == "__main__":
    with be.models.db:
        with be.models.db.atomic() as txn:
            if sys.argv[1] == "1":
                images_to_base64()
