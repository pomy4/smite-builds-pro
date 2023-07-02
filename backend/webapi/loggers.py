import contextlib
import logging
from contextvars import ContextVar
from typing import Iterator

import shared

auto_fixes_logger = logging.getLogger("auto-fixes")
auto_fixes_game_context_default = "x-x"
auto_fixes_game_context: ContextVar[str] = ContextVar(
    "auto_fixes_game_context", default=auto_fixes_game_context_default
)


def setup_auto_fixes_logger() -> None:
    """
    Keeps track of inconsistencies in the input data that were automatically fixed,
    e.g. a player name with different casing or incorrect role such as Sub/Coach,
    but also inconsistencies which require manual fixing, e.g. a missing build.
    """

    def add_game(record: logging.LogRecord) -> bool:
        record.game = auto_fixes_game_context.get()
        return True

    handler = shared.get_file_handler("auto_fixes")
    handler.setFormatter(logging.Formatter(shared.AUTO_FIXES_LOG_FORMAT))
    handler.addFilter(add_game)
    auto_fixes_logger.setLevel(logging.INFO)
    auto_fixes_logger.propagate = False
    auto_fixes_logger.addHandler(handler)


@contextlib.contextmanager
def log_curr_game(build: dict) -> Iterator[None]:
    game = f"{build['match_id']}-{build['game_i']}"
    auto_fixes_game_context.set(game)
    try:
        yield None
    except Exception as e:
        e.args = (f"Game: {game}", *e.args)
        raise
    finally:
        auto_fixes_game_context.set(auto_fixes_game_context_default)


cache_logger = logging.getLogger("be-cache")


def setup_cache_logger() -> None:
    handler = shared.get_file_handler("cache")
    handler.setFormatter(logging.Formatter(shared.LOG_FORMAT))
    cache_logger.setLevel(logging.INFO)
    cache_logger.propagate = False
    cache_logger.addHandler(handler)


error_logger = logging.getLogger("be-error")


def setup_error_logger() -> None:
    handler = shared.get_file_handler("error")
    handler.setFormatter(logging.Formatter(shared.LOG_FORMAT))
    error_logger.setLevel(logging.INFO)
    error_logger.propagate = False
    error_logger.addHandler(handler)
