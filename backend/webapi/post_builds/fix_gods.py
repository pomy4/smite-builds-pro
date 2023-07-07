import charybdis

from backend.config import get_webapi_config
from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger

BuildDict = dict


def fix_gods(builds: list[BuildDict]) -> None:
    suspicious_gods1 = []
    suspicious_gods2 = []
    for build_i, build in enumerate(builds):
        if contains_digits(build["god1"]):
            suspicious_gods1.append((build_i, build["god1"]))
        if contains_digits(build["god2"]):
            suspicious_gods2.append((build_i, build["god2"]))

    if not suspicious_gods1 and not suspicious_gods2:
        return

    try:
        newest_god = get_newest_god()
    except Exception:
        auto_fixes_logger.warning(
            "Failed to get newest god from Hi-Rez API", exc_info=True
        )
        for build_i, god in suspicious_gods1:
            auto_fixes_logger.warning(f"Suspicious god1: {god} ({build_i})")
        for build_i, god in suspicious_gods2:
            auto_fixes_logger.warning(f"Suspicious god2: {god} ({build_i})")
        return

    for build_i, old_god in suspicious_gods1:
        auto_fixes_logger.info(f"God1|{old_god} -> {newest_god}")
        builds[build_i]["god1"] = newest_god
    for build_i, old_god in suspicious_gods2:
        auto_fixes_logger.info(f"God2|{old_god} -> {newest_god}")
        builds[build_i]["god2"] = newest_god


def contains_digits(s: str) -> bool:
    return any("0" <= c <= "9" for c in s)


def get_newest_god() -> str:
    api = charybdis.Api(
        base_url=charybdis.Api.SMITE_PC_URL,
        dev_id=get_webapi_config().smite_dev_id,
        auth_key=get_webapi_config().smite_auth_key,
    )
    gods = api.call_method("getgods", "1")
    newest_god_candidates = [god["Name"] for god in gods if god["latestGod"] == "y"]
    if len(newest_god_candidates) != 1:
        raise RuntimeError(
            f"Failed to ascertain which god is newest: {newest_god_candidates}"
        )
    return newest_god_candidates[0]
