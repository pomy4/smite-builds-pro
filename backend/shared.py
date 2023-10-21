import dataclasses
import io
import logging.handlers
import sys
import time
import typing as t

import requests

from backend.config import get_project_root_dir

STORAGE_DIR = get_project_root_dir() / "storage"
LOGS_DIR = STORAGE_DIR / "logs"
LOGS_ARCHIVE_DIR = STORAGE_DIR / "logs_archive"

# The delimiter being | and the levelname being in the second place
# is depended upon by the log manager when looking for warnings in the log files.
ROOT_LOG_FORMAT = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"
SPECIFIC_LOG_FORMAT = "%(asctime)s|%(levelname)s|%(message)s"


def setup_logging(
    name: str,
    is_root: bool = True,
    format_maybe: str | None = None,
    filter_: logging.Filter | t.Callable[[logging.LogRecord], bool] | None = None,
    level: int = logging.INFO,
    console_level: int | None = None,
) -> None:
    if format_maybe is not None:
        format_ = format_maybe
    elif is_root:
        format_ = ROOT_LOG_FORMAT
    else:
        format_ = SPECIFIC_LOG_FORMAT

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    file_handler = get_file_handler(name)

    stream_handler.setFormatter(logging.Formatter(format_))
    file_handler.setFormatter(logging.Formatter(format_))

    stream_handler.addFilter(filter_python_anywhere_os_error)
    file_handler.addFilter(filter_python_anywhere_os_error)

    if filter_ is not None:
        stream_handler.addFilter(filter_)
        file_handler.addFilter(filter_)

    if console_level is not None:
        stream_handler.setLevel(console_level)

    logger_name = "" if is_root else name
    logger = logging.getLogger(logger_name)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    if is_root:
        app_name = __name__.split(".")[0]

        app_logger = logging.getLogger(app_name)
        main_logger = logging.getLogger("__main__")

        app_logger.setLevel(level)
        main_logger.setLevel(level)
    else:
        logger.setLevel(level)
        logger.propagate = False


def get_file_handler(name: str) -> logging.Handler:
    path = LOGS_DIR / f"{name}.log"
    return MoreRobustWatchedFileHandler(
        path, mode="a", encoding="utf8", delay=True, errors="backslashreplace"
    )


class MoreRobustWatchedFileHandler(logging.handlers.WatchedFileHandler):
    """
    Starting from around 2023-10-19 19:50, restarting a worker leads to the error
    'OSError: [Errno 5] Input/output error' (which causes a 500 to be returned) with
    the following traceback:

    Traceback (most recent call last):
      File "/home/irukandji4/.virtualenvs/sbp/lib/python3.10/site-packages/bottle.py"...
        self.trigger_hook('after_request')
      File "/home/irukandji4/.virtualenvs/sbp/lib/python3.10/site-packages/bottle.py"...
        return [hook(*args, **kwargs) for hook in self._hooks[__name][:]]
      File "/home/irukandji4/.virtualenvs/sbp/lib/python3.10/site-packages/bottle.py"...
        return [hook(*args, **kwargs) for hook in self._hooks[__name][:]]
      File "/home/irukandji4/smite-builds-pro/./backend/webapi/webapi.py", line 57, i...
        log_access()
      File "/home/irukandji4/smite-builds-pro/./backend/webapi/webapi.py", line 117, ...
        access_logger.info(msg1 + msg2)
      File "/usr/local/lib/python3.10/logging/__init__.py", line 1477, in info
        self._log(INFO, msg, args, **kwargs)
      File "/usr/local/lib/python3.10/logging/__init__.py", line 1624, in _log
        self.handle(record)
      File "/usr/local/lib/python3.10/logging/__init__.py", line 1634, in handle
        self.callHandlers(record)
      File "/usr/local/lib/python3.10/logging/__init__.py", line 1696, in callHandlers
        hdlr.handle(record)
      File "/usr/local/lib/python3.10/logging/__init__.py", line 968, in handle
        self.emit(record)
      File "/usr/local/lib/python3.10/logging/handlers.py", line 521, in emit
        self.reopenIfNeeded()
      File "/usr/local/lib/python3.10/logging/handlers.py", line 508, in reopenIfNeeded
        self.stream.close()

    Furthermore, all the following requests then also receive a 500 (!), due to an error
    'ValueError: I/O operation on closed file.' originating from the self.stream.flush()
    line, which is located just before the self.stream.close() line mentioned above.

    I'm not sure if this is due to some race condition which happens during the
    rotation in the log manager, or if this is caused by something being changed in the
    PythonAnywhere environment, or a combination of the two, or something else entirely.

    The WatchedFileHandler bubbles up exceptions that happen when closing/reopening
    the file, so this class overrides the emit method by wrapping it in an exception
    handler, which then skips the 'file cannot be closed because it is closed' error
    by explicitly setting the stream to None, which causes FileHandler to simply open
    the file again.

    It is possible that this will cause some other issues, but it seems to work fine
    for now.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except OSError:
            self.stream = t.cast(io.TextIOWrapper, None)
            super().emit(record)


def filter_python_anywhere_os_error(record: logging.LogRecord) -> bool:
    """
    PythonAnywhere code (more specifically the line 170 in the file
    /bin/user_wsgi_wrapper.py) throws an "OSError: write error" exception several times
    a day, which is logged into the root logger. The error seems to be caused by web
    crawlers aborting connections early. There is nothing we can really do about it,
    so here these errors have their level lowered from ERROR to INFO, so that they don't
    cause unnecesary notifications to be sent.
    """
    if (
        record.levelno == logging.ERROR
        and record.pathname.startswith("/bin/")
        and record.getMessage() == "OSError: write error"
    ):
        record.levelno = logging.INFO
        record.levelname = logging.getLevelName(logging.INFO)
    return True


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
