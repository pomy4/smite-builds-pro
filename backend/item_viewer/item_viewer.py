from __future__ import annotations

import argparse
import base64
import dataclasses as dc
import datetime as dt
import io
import math
import statistics as stat
import typing as t
from pathlib import Path

import flask
import PIL.Image as PI
import sqlalchemy as sa
import sqlalchemy.orm as sao

from backend.webapi.models import Build, BuildItem, Image, Item
from backend.webapi.models import db_path as default_db_path
from backend.webapi.models import db_session

ID_RANGE_HELP = """\
15 returns item with ID 15
15:18 returns items with IDS 15, 16, 17 and 18
:5 returns first five items
-5: returns last five items
"""


def main() -> None:
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "-d",
        "--database",
        type=Path,
        default=default_db_path,
    )
    parser.add_argument(
        "id-range",
        type=parse_id_range,
        nargs="*",
        default=[parse_id_range("-10:")],
        help=ID_RANGE_HELP,
    )
    args = parser.parse_args()
    db_path: Path = args.database
    id_ranges: list[IdRange] = getattr(args, "id-range")
    print(f"{db_path=}")
    print(f"{id_ranges}")

    with db_session():
        max_id = db_session.scalars(sa.select(sa.func.max(Item.id))).one()

    for id_range in id_ranges:
        make_id_range_absolute(max_id, id_range)

    global config
    config = Config(id_ranges)

    flask_app.run(debug=True)


@dc.dataclass
class IdRange:
    start: int
    end: int


def parse_id_range(id_range_s: str) -> IdRange:
    id_range_split = id_range_s.split(":")
    if len(id_range_split) == 1:
        start_s = end_s = id_range_split[0]
    else:
        start_s, end_s = id_range_split

    start = int(start_s) if start_s else 1
    end = int(end_s) if end_s else -1

    return IdRange(start, end)


def make_id_range_absolute(max_id: int, id_range: IdRange) -> None:
    if id_range.start < 0:
        id_range.start += max_id + 1
    if id_range.end < 0:
        id_range.end += max_id + 1


config: Config | None = None


@dc.dataclass
class Config:
    id_ranges: list[IdRange]


def cfg() -> Config:
    if config is None:
        raise RuntimeError("Unset config")
    return config


flask_app = flask.Flask(__name__, template_folder="")


@flask_app.after_request
def after_request(response: flask.Response) -> flask.Response:
    db_session.remove()
    return response


@flask_app.get("/")
def index() -> t.Any:
    items = get_items(cfg().id_ranges)
    return flask.render_template("index.jinja", all_items=[items])


@flask_app.get("/images")
def images() -> t.Any:
    all_items = get_items_with_duplicate_images()
    return flask.render_template("index.jinja", all_items=all_items)


@flask_app.get("/images2")
def images2() -> t.Any:
    all_items = get_items_with_duplicate_names_with_distinct_images()
    return flask.render_template("index.jinja", all_items=all_items)


@flask_app.get("/names")
def names() -> t.Any:
    all_items = get_items_with_duplicate_names()
    return flask.render_template("index.jinja", all_items=all_items)


def get_items(id_ranges: list[IdRange]) -> list[ItemPlus]:
    wheres = [sa.and_(Item.id >= x.start, Item.id <= x.end) for x in id_ranges]
    items = db_session.scalars(
        sa.select(Item)
        .where(sa.or_(*wheres))
        .join(Image, Item.image_id == Image.id)
        .options(sao.contains_eager(Item.image))
        .order_by(Item.id.asc())
    ).all()
    return lst2(items)


def get_items_with_duplicate_images() -> list[list[ItemPlus]]:
    duplicates = db_session.scalars(
        sa.select(Item.image_id)
        .group_by(Item.image_id)
        .having(sa.func.count() > 1)
        .order_by(Item.image_id.desc())
    ).all()
    all_items = []
    for image_id in duplicates:
        items = db_session.scalars(
            sa.select(Item)
            .where(Item.image_id == image_id)
            .join(Image, Item.image_id == Image.id)
            .options(sao.contains_eager(Item.image))
            .order_by(Item.id.asc())
        ).all()
        all_items.append(lst2(items))
    return all_items


def get_items_with_duplicate_names() -> list[list[ItemPlus]]:
    duplicates = db_session.execute(
        sa.select(Item.name, Item.name_was_modified)
        .group_by(Item.name, Item.name_was_modified)
        .having(sa.func.count() > 1)
        .order_by(Item.image_id.desc())
    ).all()
    all_items = []
    for name, name_was_modified in duplicates:
        items = db_session.scalars(
            sa.select(Item)
            .where(Item.name == name)
            .where(Item.name_was_modified == name_was_modified)
            .join(Image, Item.image_id == Image.id)
            .options(sao.contains_eager(Item.image))
            .order_by(Item.id.asc())
        ).all()
        all_items.append(lst2(items))
    return all_items


def get_items_with_duplicate_names_with_distinct_images() -> list[list[ItemPlus]]:
    all_items = get_items_with_duplicate_names()
    new_all_items = []
    for items in all_items:
        images = [get_image(item) for item in items]
        while True:
            to_delete = find_similar_images(images)
            if to_delete is None:
                break
            del images[to_delete]
            del items[to_delete]
        if len(items) > 1:
            new_all_items.append(items)
    return new_all_items


def get_image(item: ItemPlus) -> PI.Image:
    image_obj = item.x.image
    assert image_obj is not None
    b64_image_data = image_obj.data
    image_data = base64.b64decode(b64_image_data)
    image_file = io.BytesIO(image_data)
    image = PI.open(image_file)
    return image


def find_similar_images(images: list[PI.Image]) -> int | None:
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            diff = diff_images(images[i], images[j])
            # print(diff)
            if diff < 35:
                return i
    return None


def diff_images(img1: PI.Image, img2: PI.Image) -> float:
    if img1.size != img2.size:
        # print(img1.size, img2.size)
        return 0

    def impl(img1: PI.Image, img2: PI.Image) -> t.Iterator[float]:
        for img1_pixel, img2_pixel in zip(img1.getdata(), img2.getdata()):
            yield math.dist(img1_pixel, img2_pixel)

    return stat.stdev(impl(img1, img2), 0)


@dc.dataclass
class ItemPlus:
    x: Item
    first_date: dt.date
    last_date: dt.date
    count: int


def lst2(items: t.Sequence[Item]) -> list[ItemPlus]:
    return [add_info_to_item(item) for item in items]


def add_info_to_item(item: Item) -> ItemPlus:
    first_date, last_date, count = db_session.execute(
        sa.select(sa.func.min(Build.date), sa.func.max(Build.date), sa.func.count())
        .join(BuildItem, Build.id == BuildItem.build_id)
        .where(BuildItem.item_id == item.id)
        .order_by(Build.date.asc())
    ).one()
    item_info = ItemPlus(
        x=item, first_date=first_date, last_date=last_date, count=count
    )
    return item_info


if __name__ == "__main__":
    main()
