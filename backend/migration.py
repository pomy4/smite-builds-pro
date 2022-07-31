import sys

from models import (
    Item,
    compress_and_base64_image,
    db,
    no_img,
    save_item_icon_to_archive,
)


def images_to_base64():
    for item in Item.select():
        try:
            b64_image_data, was_compressed = compress_and_base64_image(item.image_data)
            if was_compressed:
                save_item_icon_to_archive(item, item.image_data)
            item.image_data = b64_image_data
            item.save()
        except:  # noqa
            print(no_img(item))
            raise


if __name__ == "__main__":
    with db:
        with db.atomic() as txn:
            if sys.argv[1] == "1":
                images_to_base64()
