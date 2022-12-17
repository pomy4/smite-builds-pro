import dataclasses
import time
from pathlib import Path

import dotenv

HMAC_KEY_HEX = "HMAC_KEY_HEX"
BACKEND_URL = "BACKEND_URL"
USE_WATCHDOG = "USE_WATCHDOG"


def load_default_dot_env() -> None:
    default_dot_env_path = Path(__file__).parent / ".env"
    dotenv.load_dotenv(default_dot_env_path)


LOG_FORMAT = "%(asctime)s|%(levelname)s|%(message)s"

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
