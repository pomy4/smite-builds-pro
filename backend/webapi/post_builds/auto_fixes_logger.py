import contextlib
import logging
import typing as t
from contextvars import ContextVar

from backend.shared import setup_side_logger

AUTO_FIXES_LOG_NAME = "auto_fixes"
auto_fixes_logger = logging.getLogger(AUTO_FIXES_LOG_NAME)

auto_fixes_game_context_default = "x-x"
auto_fixes_game_context: ContextVar[str] = ContextVar(
    "auto_fixes_game_context", default=auto_fixes_game_context_default
)


def setup_auto_fixes_logging() -> None:
    """
    Keeps track of inconsistencies in the input data that were automatically fixed,
    e.g. a player name with different casing or incorrect role such as Sub/Coach,
    but also inconsistencies which require manual fixing, e.g. a missing build.
    """
    auto_fixes_log_format = "%(asctime)s|%(levelname)s|%(game)s|%(message)s"

    def add_game_filter(record: logging.LogRecord) -> bool:
        record.game = auto_fixes_game_context.get()
        return True

    setup_side_logger(
        AUTO_FIXES_LOG_NAME,
        format_=auto_fixes_log_format,
        filter_=add_game_filter,
    )


@contextlib.contextmanager
def log_curr_game(build: dict) -> t.Iterator[None]:
    game = f"{build['match_id']}-{build['game_i']}"
    auto_fixes_game_context.set(game)
    try:
        yield None
    except Exception as e:
        e.args = (f"Game: {game}", *e.args)
        raise
    finally:
        auto_fixes_game_context.set(auto_fixes_game_context_default)
