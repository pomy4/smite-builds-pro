import dataclasses
import logging
import time

from config import get_project_root_dir

STORAGE_DIR = get_project_root_dir() / "storage"

LOG_FORMAT = "%(asctime)s|%(levelname)s|%(message)s"
AUTO_FIXES_LOG_FORMAT = "%(asctime)s|%(levelname)s|%(game)s|%(message)s"


def get_file_handler(name: str) -> logging.Handler:
    path = STORAGE_DIR / "logs" / f"{name}.log"
    return logging.FileHandler(
        path, mode="a", encoding="utf8", errors="backslashreplace"
    )


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
