from __future__ import annotations

import dataclasses
import datetime
import logging
from pathlib import Path

import msgspec

from backend.shared import LOGS_DIR, STORAGE_DIR

logger = logging.getLogger(__name__)

LOG_MANAGER_NAME = "log_manager"
LOG_MANAGER_STATE_PATH = STORAGE_DIR / "log_manager.json"


@dataclasses.dataclass
class LogManagerInfo:
    log_infos: dict[str, LogInfo]
    date_last_archival: datetime.date


@dataclasses.dataclass
class LogInfo:
    path_str: str
    date_found: datetime.date
    lines_read: int | None

    @property
    def path(self) -> Path:
        """Workaround for msgspec not supporting Path."""
        return Path(self.path_str)


def load_info(today: datetime.date) -> LogManagerInfo:
    if not LOG_MANAGER_STATE_PATH.exists():
        info = LogManagerInfo(log_infos={}, date_last_archival=today)
        logger.info("Created new log manager info")
    else:
        with open(LOG_MANAGER_STATE_PATH, "rb") as f:
            info_bytes = f.read()
        info = msgspec.json.decode(info_bytes, type=LogManagerInfo)
        logger.info(f"Found log infos: {len(info.log_infos)}")

        to_remove = []
        for name, log_info in info.log_infos.items():
            if not log_info.path.exists():
                if not log_info.lines_read:
                    msg = f"Discarding probably not yet recreated log info: {name}"
                    logger.info(msg)
                    to_remove.append(name)
                else:
                    msg1 = "Cannot find file but wasn't rotated:"
                    msg2 = f" {name} {log_info.lines_read}"
                    raise RuntimeError(msg1 + msg2)
        for name in to_remove:
            del info.log_infos[name]

    log_paths = get_current_logs()
    logger.info(f"Found log paths: {len(log_paths)}")

    new_log_paths = [x for x in log_paths if x.stem not in info.log_infos]

    if new_log_paths:
        logger.info(f"Found new logs paths: {len(new_log_paths)}")
        for path in new_log_paths:
            path = path.relative_to(Path.cwd())
            lines_read = None if path.stem == LOG_MANAGER_NAME else 0
            info.log_infos[path.stem] = LogInfo(
                path_str=str(path), date_found=today, lines_read=lines_read
            )
            info.log_infos = {
                k: v for k, v in sorted(info.log_infos.items(), key=lambda x: x[0])
            }

    if not today >= info.date_last_archival:
        raise RuntimeError(
            f"Date last archival from the future: {info.date_last_archival}"
        )

    for name, log_info in info.log_infos.items():
        if not today >= log_info.date_found:
            raise RuntimeError(
                f"Date found from the future: {name} {log_info.date_found}"
            )

    return info


def save_info(info: LogManagerInfo) -> None:
    info_bytes = msgspec.json.encode(info)
    info_bytes = msgspec.json.format(info_bytes, indent=2)
    with open(LOG_MANAGER_STATE_PATH, "wb") as f:
        f.write(info_bytes)


def get_current_logs() -> list[Path]:
    return [x for x in get_logs() if len(x.suffixes) == 1]


def get_rotated_logs() -> list[Path]:
    return [x for x in get_logs() if len(x.suffixes) == 2]


def get_logs() -> list[Path]:
    return [x for x in LOGS_DIR.iterdir() if x.suffix == ".log"]
