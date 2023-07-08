from __future__ import annotations

import datetime
import logging
import zipfile
from pathlib import Path

from backend.log_manager.info import LogManagerInfo, get_rotated_logs
from backend.log_manager.rotate import get_date_rotated_from_path
from backend.shared import LOGS_ARCHIVE_DIR, STORAGE_DIR

logger = logging.getLogger(__name__)


def archive(today: datetime.date, info: LogManagerInfo) -> None:
    logger.info("Starting archiving")

    archival_period_in_days = 30
    days_since_last_archival = (today - info.date_last_archival).days
    if days_since_last_archival < archival_period_in_days:
        cmp_str = f"{days_since_last_archival}D < {archival_period_in_days}D"
        logger.info(f"Archival period not reached yet: {cmp_str}")
        return

    info.date_last_archival = today

    log_paths = get_log_paths_for_archival(today)
    today_str = today.strftime("%Y_%m_%d")
    zip_path = LOGS_ARCHIVE_DIR / f"{today_str}_{days_since_last_archival}.zip"
    zip_and_delete(zip_path, log_paths)

    logger.info("Finished archiving")


def get_log_paths_for_archival(today: datetime.date) -> list[Path]:
    log_paths = get_rotated_logs()
    logger.info(f"Found paths before filtering: {len(log_paths)}")

    min_age_in_days = 7
    log_path_and_date_list: list[tuple[Path, datetime.date]] = []
    for log_path in log_paths:
        date_rotated = get_date_rotated_from_path(log_path)

        if not today >= date_rotated:
            raise RuntimeError(f"Date rotated from the future: {log_path.name}")

        diff_in_days = (today - date_rotated).days
        cmp_str = f"{log_path.name} {diff_in_days}D > {min_age_in_days}D"
        if diff_in_days > min_age_in_days:
            log_path_and_date_list.append((log_path, date_rotated))
            logger.info(f"Archiving: {cmp_str}")
        else:
            logger.info(f"Skipping: not {cmp_str}")

    if not log_path_and_date_list:
        raise RuntimeError("Found zero paths after filtering")

    logger.info(f"Found paths after filtering: {len(log_path_and_date_list)}")
    return [log_path for (log_path, _) in log_path_and_date_list]


def zip_and_delete(zip_path: Path, log_paths: list[Path]) -> None:
    if zip_path.exists():
        raise RuntimeError(f"Target already exists: {zip_path}")

    tmp_zip_path = STORAGE_DIR / "tmp.zip"

    with zipfile.ZipFile(
        tmp_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as zipf:
        for log_path in log_paths:
            zipf.write(log_path, arcname=log_path.name)

    # The zips are downloaded using rsync --remove-source-files, so using create+rename
    # instead of just create eliminates the chance, that an unfinished zip is downloaded
    # and deleted.
    tmp_zip_path.rename(zip_path)

    for log_path in log_paths:
        log_path.unlink()
