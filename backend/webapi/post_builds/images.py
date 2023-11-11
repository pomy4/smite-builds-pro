import io
import time
import urllib.error
import urllib.request

import PIL.Image

from backend.shared import IMG_URL, STORAGE_DIR, delay
from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger as logger


def get_image_or_none(image_name: str) -> bytes | None:
    start = time.time()
    try:
        ret = get_image(image_name)
        print(f"Download success: {image_name}")
    except urllib.error.URLError:
        ret = None
        logger.warning(f"Download fail: {image_name}", exc_info=True)
    delay(0.20, start)
    return ret


def get_image(image_name: str) -> bytes:
    request = urllib.request.Request(
        f"{IMG_URL}/{image_name}", headers={"User-Agent": "Mozilla"}
    )
    with urllib.request.urlopen(request) as f:
        return f.read()


def compress_image_ignore_errors(
    image_name: str, image_data: bytes
) -> tuple[bytes, bool]:
    try:
        return compress_image(image_data)
    # OSError can be thrown while saving as JPEG.
    except (PIL.UnidentifiedImageError, OSError):
        logger.warning(f"Failed to compress: {image_name}", exc_info=True)
        return image_data, False


def compress_image(image_data: bytes) -> tuple[bytes, bool]:
    image = PIL.Image.open(io.BytesIO(image_data))
    min_side = min(image.size)

    if image.format != "JPEG" or min_side > 128:
        multiplier = min_side / 128
        new_size = round(image.size[0] / multiplier), round(image.size[1] / multiplier)
        image = image.resize(new_size, PIL.Image.Resampling.LANCZOS)
        if image.mode == "RGBA":
            image = image.convert("RGB")
        b = io.BytesIO()
        image.save(b, "JPEG")
        image_data = b.getvalue()
        was_compressed = True
    else:
        was_compressed = False

    return image_data, was_compressed


def save_icon_to_archive(image_id: int, image_name: str, image_data: bytes) -> None:
    item_icons_archive_dir = STORAGE_DIR / "item_icons_archive"
    image_path = item_icons_archive_dir / f"{image_id:0>5}-{image_name}"
    image_path.write_bytes(image_data)
