from __future__ import annotations

import datetime
import logging
import sqlite3
import sys
import traceback

from backend.config import load_log_manager_config
from backend.log_manager.alert import alert, send_notification
from backend.log_manager.archive import archive
from backend.log_manager.info import LOG_MANAGER_NAME, load_info, save_info
from backend.log_manager.rotate import rotate
from backend.shared import STORAGE_DIR, setup_logging
from backend.webapi.models import db_path

logger = logging.getLogger(__name__)


def main() -> None:
    load_log_manager_config()

    try:
        setup_logging(LOG_MANAGER_NAME)
        logger.info("Starting log manager")
        today = datetime.date.today()

        info = load_info(today)
        alert_success = alert(info)
        rotate(today, info)
        archive(today, info)
        save_info(info)

        backup_database()
        logger.info("Finished log manager")

        if not alert_success:
            msg = "Failed to send notification, exiting with non-zero exit code"
            logger.warning(msg)
            sys.exit(1)

    except Exception:
        logger.exception("Unexpected error in log manager")
        send_notification(f"{traceback.format_exc()}\n")
        raise


def backup_database() -> None:
    logger.info("Backing up database")

    backup_path = STORAGE_DIR / "backend.bkp.db"
    if backup_path.exists():
        backup_path.unlink()

    with sqlite3.connect(db_path) as con:
        cursor = con.execute(f"VACUUM INTO '{backup_path}'")
        cursor.close()

    logger.info("Finished backing up database")


if __name__ == "__main__":
    main()
