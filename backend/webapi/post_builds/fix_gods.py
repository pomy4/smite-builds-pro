import typing as t

from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger as logger

BuildDict = dict[str, t.Any]


def fix_gods(builds: list[BuildDict], newest_god: str | None) -> None:
    suspicious_gods1 = []
    suspicious_gods2 = []
    for build_i, build in enumerate(builds):
        if contains_digits(build["god1"]):
            suspicious_gods1.append((build_i, build["god1"]))
        if contains_digits(build["god2"]):
            suspicious_gods2.append((build_i, build["god2"]))

    if not suspicious_gods1 and not suspicious_gods2:
        return

    if newest_god is None:
        logger.warning("Newest god is unknown, cannot fix suspicious gods")
        for build_i, god in suspicious_gods1:
            logger.warning(f"Suspicious god1: {god} ({build_i})")
        for build_i, god in suspicious_gods2:
            logger.warning(f"Suspicious god2: {god} ({build_i})")
        return

    for build_i, old_god in suspicious_gods1:
        logger.info(f"God1|{old_god} -> {newest_god}")
        builds[build_i]["god1"] = newest_god
    for build_i, old_god in suspicious_gods2:
        logger.info(f"God2|{old_god} -> {newest_god}")
        builds[build_i]["god2"] = newest_god


def contains_digits(s: str) -> bool:
    return any("0" <= c <= "9" for c in s)
