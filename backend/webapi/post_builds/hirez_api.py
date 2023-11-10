import dataclasses as dc
import enum
import json
import typing as t

import charybdis

from backend.config import get_webapi_config, load_webapi_config
from backend.shared import STORAGE_DIR
from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger as logger

GODS_PATH = STORAGE_DIR / "gods.json"


class GodClass(enum.Enum):
    ASSASSIN = "Assassin"
    GUARDIAN = "Guardian"
    HUNTER = "Hunter"
    MAGE = "Mage"
    WARRIOR = "Warrior"


Gods: t.TypeAlias = list[dict[str, t.Any]]
NewestGod: t.TypeAlias = str
GodClasses: t.TypeAlias = dict[str, GodClass]


@dc.dataclass
class GodInfo:
    newest_god: NewestGod | None
    god_classes: GodClasses | None


def get_god_info() -> GodInfo:
    api = get_api()

    try:
        gods = api.call_method("getgods", "1")
    except Exception:
        logger.warning("Failed to get gods from Hi-Rez API", exc_info=True)

        if GODS_PATH.exists():
            gods = load_gods_from_file()
        else:
            logger.warning("There is no gods file that can be used as backup")
            return GodInfo(None, None)

    else:
        save_gods_to_file(gods)

    try:
        god_info = parse_god_info(gods)
    except Exception:
        logger.warning("Failed to parse god info from Hi-Rez API", exc_info=True)
        return GodInfo(None, None)

    return god_info


def get_api() -> charybdis.Api:
    return charybdis.Api(
        base_url=charybdis.Api.SMITE_PC_URL,
        dev_id=get_webapi_config().smite_dev_id,
        auth_key=get_webapi_config().smite_auth_key,
    )


def load_gods_from_file() -> Gods:
    gods_str = GODS_PATH.read_text(encoding="utf8")
    gods = json.loads(gods_str)
    return gods


def save_gods_to_file(gods: Gods) -> None:
    gods_str = json.dumps(gods, indent=2, ensure_ascii=False)
    GODS_PATH.write_text(gods_str, encoding="utf8")


def parse_god_info(gods: Gods) -> GodInfo:
    newest_god = get_newest_god(gods)
    god_classes = get_god_classes(gods)
    return GodInfo(newest_god=newest_god, god_classes=god_classes)


def get_newest_god(gods: Gods) -> NewestGod:
    newest_god_candidates = [god["Name"] for god in gods if god["latestGod"] == "y"]
    if len(newest_god_candidates) != 1:
        raise RuntimeError(
            f"Failed to ascertain which god is newest: {newest_god_candidates}"
        )
    return newest_god_candidates[0]


def get_god_classes(gods: Gods) -> GodClasses:
    result = {god["Name"]: GodClass(god["Roles"]) for god in gods}
    return result


if __name__ == "__main__":
    load_webapi_config()
    get_god_info()
