import dataclasses
import logging.handlers
import sys
import time
import typing as t

import requests

from backend.config import get_project_root_dir

STORAGE_DIR = get_project_root_dir() / "storage"
ITEM_ICONS_ARCHIVE_DIR = STORAGE_DIR / "item_icons_archive"

ROOT_LOG_FORMAT = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(logging.Formatter(ROOT_LOG_FORMAT))

    root_logger = logging.getLogger()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(logging.WARNING)

    app_name = __name__.split(".")[0]
    logging.getLogger(app_name).setLevel(level)
    logging.getLogger("__main__").setLevel(level)

    # this function runs after gunicorn is already set up,
    # which means there is already a logger called gunicorn.error
    # with a stderr handler, different format than ours, and propagate=False,
    # which is fine


def setup_side_logger(
    name: str,
    level: int = logging.INFO,
    format_: str | None = None,
    filter_: logging.Filter | t.Callable[[logging.LogRecord], bool] | None = None,
) -> None:
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(
        logging.Formatter(format_ if format_ else ROOT_LOG_FORMAT)
    )
    if filter_ is not None:
        stream_handler.addFilter(filter_)

    logger = logging.getLogger(name)
    logger.addHandler(stream_handler)
    logger.setLevel(level)
    logger.propagate = False


IMG_URL = "https://webcdn.hirezstudios.com/smite/item-icons"


@dataclasses.dataclass
class League:
    name: str
    schedule_url: str
    match_url: str


SPL = League(
    name="SPL",
    schedule_url="https://www.smiteproleague.com/schedule",
    match_url="https://www.smiteproleague.com/matches",
)
SCC = League(
    name="SCC",
    schedule_url="https://scc.smiteproleague.com/schedule",
    match_url="https://scc.smiteproleague.com/matches",
)


def league_factory(league_name: str) -> League:
    if league_name == SPL.name:
        return SPL
    elif league_name == SCC.name:
        return SCC
    else:
        raise RuntimeError(f"Unknown league_name: {league_name}")


def delay(min_delay: float, start: float) -> None:
    end = time.time()
    time_spent = end - start
    time_remaining = min_delay - time_spent
    if time_remaining > 0:
        time.sleep(time_remaining)


def raise_for_status_with_detail(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        msg = [
            "HTTP response was not OK!",
            f"Url: {response.url}",
            f"Status code: {response.status_code} {response.reason}",
        ]
        if more_detail := response.text:
            msg.append(f"More detail: {more_detail}")
        raise requests.HTTPError("\n".join(msg), response=response) from e
