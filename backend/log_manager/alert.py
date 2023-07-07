import logging
import time

import requests

from backend.config import get_log_manager_config
from backend.log_manager.info import LogManagerInfo
from backend.shared import raise_for_status_with_detail

logger = logging.getLogger(__name__)

Alerts = list[list[str]]


def alert(info: LogManagerInfo) -> bool:
    logger.info("Starting alerting")

    name_and_alerts_list: list[tuple[str, Alerts]] = []

    for name, log_info in info.log_infos.items():
        if log_info.lines_read is None:
            logger.info(f"Skipping: {name}")
            continue

        logger.info(f"Checking: {name}")
        with open(log_info.path_str, "r", encoding="utf8") as f:
            lines = f.readlines()
        lines_total = len(lines)

        if lines_total < log_info.lines_read:
            msg = f"Too little lines: {name} {lines_total} < {log_info.lines_read}"
            raise RuntimeError(msg)

        if lines_total == log_info.lines_read:
            logger.info(f"Lines read didn't change: {lines_total}")
            continue

        lines = lines[log_info.lines_read :]

        logger.info(f"Parsing: {len(lines)}")
        alerts = parse_lines(lines)
        if alerts:
            logger.info(f"Found warnings: {len(alerts)}")
            name_and_alerts_list.append((name, alerts))

        log_info.lines_read = lines_total

    if not name_and_alerts_list:
        logger.info("Nothing to send")
        success = True
    else:
        success = send_alerts(name_and_alerts_list)

    logger.info("Finished alerting")
    return success


def parse_lines(lines: list[str]) -> Alerts:
    alerts: Alerts = []
    for start_of_first, line in enumerate(lines):
        if is_starting_line(line):
            break
        else:
            msg1 = f"Line #{start_of_first} doesn't start"
            msg2 = f" with a log:\n{line.rstrip()}"
            logger.warning(msg1 + msg2)
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
    return log[0].split("|")[1] not in ("INFO", "DEBUG")


def send_alerts(name_and_alerts_list: list[tuple[str, Alerts]]) -> bool:
    string_builder: list[str] = []
    for name, alerts in name_and_alerts_list:
        string_builder.extend((name, "\n"))
        for alert in reversed(alerts):
            for line in alert:
                string_builder.append(line)
    data = "".join(string_builder)
    return send_notification(data)


def send_notification(data: str) -> bool:
    # ntfy.sh turns notifications larger than 4096 bytes to attachments. Maximal
    # attachment size is 2 MB. That much is not needed here, so a smaller limit is used.
    max_size = 10_000
    if len(data) > max_size:
        logger.info(f"Truncating message from {len(data)} to {max_size}")
        data = data[: max_size - 4] + "...\n"
    url = f"https://ntfy.sh/{get_log_manager_config().ntfy_topic}"

    max_tries = 3
    for try_i in range(max_tries):
        try:
            logger.info("Sending notification")
            resp = requests.post(url, data=data)
            raise_for_status_with_detail(resp)
            logger.info(f"Sent\n'''\n{data.rstrip()}\n'''")
            return True
        except requests.RequestException:
            msg = f"Failed to send notification ({try_i + 1}/{max_tries})"
            logger.warning(msg, exc_info=True)
            time.sleep(3)
    logger.warning(f"Failed too many times: {max_tries}")
    return False
