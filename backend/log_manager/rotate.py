import datetime
import logging
from pathlib import Path

from backend.log_manager.info import LogInfo, LogManagerInfo

logger = logging.getLogger(__name__)


def rotate(today: datetime.date, info: LogManagerInfo) -> None:
    logger.info("Starting rotating")

    for name, log_info in info.log_infos.items():
        if should_rotate(today, name, log_info):
            rotate_one(today, name, log_info)
            log_info.date_found = today
            if log_info.lines_read is not None:
                log_info.lines_read = 0

    logger.info("Finished rotating")


def should_rotate(today: datetime.date, name: str, log_info: LogInfo) -> bool:
    max_size_in_kb = 300
    diff_in_days = (today - log_info.date_found).days
    max_age_in_days = 7
    size_in_kb = round(log_info.path.stat().st_size / 1000, 2)
    if size_in_kb > max_size_in_kb:
        msg1 = f"Rotating size: {name} {size_in_kb}KB >"
        msg2 = f" {max_size_in_kb}KB {diff_in_days}D"
        logger.info(msg1 + msg2)
        return True
    elif diff_in_days >= max_age_in_days:
        msg1 = f"Rotating age: {name} {size_in_kb}KB"
        msg2 = f" {diff_in_days}D >= {max_age_in_days}D"
        logger.info(msg1 + msg2)
        return True
    else:
        logger.info(f"Skipping: {name} {size_in_kb}KB {diff_in_days}D")
        return False


def rotate_one(today: datetime.date, name: str, log_info: LogInfo) -> None:
    new_name = make_rotated_name(today, name, log_info)
    new_path = log_info.path.with_name(new_name)

    if new_path.exists():
        raise RuntimeError(f"Target already exists: {new_name}")

    logger.info(f"Rotated name: {new_name}")
    log_info.path.rename(new_path)


def make_rotated_name(today: datetime.date, name: str, log_info: LogInfo) -> str:
    date_str = log_info.date_found.strftime("%Y_%m_%d")
    dates_diff = today - log_info.date_found
    rotated_name = f"{name}.{date_str}_{dates_diff.days}.log"
    return rotated_name


def get_date_rotated_from_path(path: Path) -> datetime.date:
    date_str = path.suffixes[-2]
    date_str = date_str[1 : 4 + 1 + 2 + 1 + 2 + 1]
    date_rotated = datetime.datetime.strptime(date_str, "%Y_%m_%d").date()
    return date_rotated
