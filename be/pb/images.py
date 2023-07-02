import base64
import io
import time
import urllib.error
import urllib.request
from typing import Optional

from PIL import Image, UnidentifiedImageError

import shared
from be.models import Item
from shared import STORAGE_DIR


def get_image_or_none(image_name: str) -> Optional[bytes]:
    start = time.time()
    try:
        ret = get_image(image_name)
    except urllib.error.URLError:
        ret = None
    shared.delay(0.25, start)
    return ret


def get_image(image_name: str) -> bytes:
    request = urllib.request.Request(
        f"{shared.IMG_URL}/{image_name}",
        headers={"User-Agent": "Mozilla"},
    )
    with urllib.request.urlopen(request) as f:
        return f.read()


def compress_and_base64_image_or_none(
    image_data: bytes,
) -> tuple[Optional[bytes], bool]:
    try:
        return compress_and_base64_image(image_data)
    # OSError can be thrown while saving as JPEG.
    except (UnidentifiedImageError, OSError):
        return None, False


def compress_and_base64_image(image_data: bytes) -> tuple[bytes, bool]:
    image = Image.open(io.BytesIO(image_data))
    min_side = min(image.size)

    if image.format != "JPEG" or min_side > 128:
        multiplier = min_side / 128
        new_size = round(image.size[0] / multiplier), round(image.size[1] / multiplier)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        if image.mode == "RGBA":
            image = image.convert("RGB")
        b = io.BytesIO()
        image.save(b, "JPEG")
        image_data = b.getvalue()
        was_compressed = True
    else:
        was_compressed = False

    return base64.b64encode(image_data), was_compressed


def save_item_icon_to_archive(item: Item, image_data: bytes) -> None:
    item_icons_archive_dir = STORAGE_DIR / "item_icons_archive"
    image_path = item_icons_archive_dir / f"{item.id:0>5}-{item.image_name}"
    image_path.write_bytes(image_data)
