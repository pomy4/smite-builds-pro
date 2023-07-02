import json
import logging
import sys
import time
from pathlib import Path

import requests

from backend.config import get_alerter_config, load_alerter_config
from backend.shared import (
    LOG_FORMAT,
    STORAGE_DIR,
    get_file_handler,
    raise_for_status_with_detail,
)

logger = logging.getLogger(__name__)

LOG_NAME = "alerter"

Alerts = list[list[str]]


def main() -> None:
    load_alerter_config()
    setup_logging()

    logger.info("Starting alerter...")

    lines_read_path = STORAGE_DIR / "alerter_lines_read.json"
    old_path_to_lines_read: dict[str, int]
    if lines_read_path.exists():
        with open(lines_read_path, "r", encoding="utf8") as f:
            old_path_to_lines_read = json.load(f)
        logger.info(f"JSON file read with {len(old_path_to_lines_read)} file(s)")

    else:
        old_path_to_lines_read = {}
        logger.info("JSON file did not exist")

    new_paths = sorted(str(x) for x in Path(".").rglob("*.log") if x.stem != LOG_NAME)
    logger.info(f"Found {len(new_paths)} files")
    path_to_lines_read = {
        path: old_path_to_lines_read.get(path, 0) for path in new_paths
    }
    path_to_alerts: dict[str, Alerts] = {}
    path_to_lines_total: dict[str, int] = {}

    for path, lines_read in path_to_lines_read.items():
        with open(path, "r", encoding="utf8") as f:
            lines = f.readlines()
        lines_total = len(lines)
        path_to_lines_total[path] = lines_total
        if lines_total == lines_read:
            continue
        logger.info(f"Parsing {path}...")
        lines = lines[lines_read:]
        assert lines
        alerts = parse_lines(lines)
        logger.info(f"Found {len(alerts)} warnings")
        if alerts:
            path_to_alerts[path] = alerts

    if not path_to_alerts:
        logger.info("Nothing to send")
    elif not send_alerts(path_to_alerts):
        logger.warning("Failed to send alerts, exiting...")
        sys.exit(1)

    lines_read_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lines_read_path, "w", encoding="utf8") as f:
        json.dump(path_to_lines_total, f, indent=2, ensure_ascii=False)


def setup_logging() -> None:
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    file_handler = get_file_handler(LOG_NAME)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)


def parse_lines(lines: list[str]) -> Alerts:
    alerts: Alerts = []
    for start_of_first, line in enumerate(lines):
        if is_starting_line(line):
            break
        else:
            logger.warning(
                f"Line #{start_of_first} doesn't start "
                + f"with a log:\n{line.rstrip()}"
            )
    else:
        return []
    current = [lines[start_of_first]]
    for line in lines[start_of_first + 1 :]:
        if is_starting_line(line):
            if is_alert(current):
                alerts.append(current)
            current = [line]
        else:
            current.append(line)
    if is_alert(current):
        alerts.append(current)
    return alerts


def is_starting_line(line: str) -> bool:
    return line.count("|") >= 2


def is_alert(log: list[str]) -> bool:
    return log[0].split("|")[1] != "INFO"


def send_alerts(path_to_alerts: dict[str, Alerts]) -> bool:
    string_builder: list[str] = []
    for path, alerts in path_to_alerts.items():
        string_builder.extend((path, "\n"))
        for alert in reversed(alerts):
            for line in alert:
                string_builder.append(line)
    data = "".join(string_builder)

    # ntfy.sh turns notifications larger than 4096 bytes to attachments. Maximal
    # attachment size is 2 MB. That much is not needed here, so a smaller limit is used.
    max_size = 10_000
    if len(data) > max_size:
        logger.info(f"Truncating message from {len(data)} to {max_size}")
        data = data[: max_size - 4] + "...\n"
    url = f"https://ntfy.sh/{get_alerter_config().ntfy_topic}"

    max_tries = 3
    for try_i in range(max_tries):
        try:
            resp = requests.post(url, data=data)
            raise_for_status_with_detail(resp)
            logger.info(f"Sent\n{data.rstrip()}")
            return True
        except requests.RequestException:
            logger.warning(
                f"Failed to send alerts ({try_i + 1}/{max_tries})", exc_info=True
            )
            time.sleep(3)
    return False
