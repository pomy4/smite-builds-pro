import dataclasses
import hashlib
import hmac
import json
import logging
import math
import time
import typing as t

import requests
import selenium.common.exceptions as sel_exc
import tqdm
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from backend.config import get_updater_config, load_updater_config
from backend.shared import (
    IMG_URL,
    SCC,
    SPL,
    STORAGE_DIR,
    League,
    delay,
    raise_for_status_with_detail,
    setup_logging,
)

logger = logging.getLogger(__name__)

WebDriver = Chrome
WebDriverOptions = ChromeOptions

IMPLICIT_WAIT = 3
FALLBACK_COOKIES_WAIT = 10
NO_STATS_MESSAGE = "There are no stats for this match"


class NoStats(Exception):
    pass


def main() -> None:
    load_updater_config()
    setup_logging("updater", level=logging.DEBUG, console_level=logging.INFO)

    try:
        options = make_webdriver_options()
        logger.info("Starting browser")
        with WebDriver(options=options) as driver:
            driver.implicitly_wait(IMPLICIT_WAIT)
            logger.info("Scraping SPL schedule")
            matches = scrape_league(driver, SPL)
            logger.info("Scraping SCC schedule")
            matches += scrape_league(driver, SCC)
            logger.info(f"All found matches: {len(matches)}")
            new_matches = [match for match in matches if not match.is_old]
            logger.info(f"Scraping new matches: {len(new_matches)}")
            builds = scrape_matches(driver, new_matches)
            logger.info(f"Posting builds: {len(builds)}")
            last_checked_tooltip = format_last_checked_tooltip(matches)
            post_builds(builds, last_checked_tooltip)
            logger.info("All done")

    except Exception:
        logger.exception("Crash|")
        raise


# --------------------------------------------------------------------------------------
# BACKEND COMMUNICATION
# --------------------------------------------------------------------------------------


def get_all_match_ids(phases: list[str]) -> list[list[int]]:
    all_match_ids_resp = requests.post(
        f"{get_updater_config().backend_url}/api/phases", json=phases
    )
    raise_for_status_with_detail(all_match_ids_resp)
    all_match_ids = all_match_ids_resp.json()
    if len(phases) != len(all_match_ids):
        raise RuntimeError(f"/api/phases returned wrong list: {all_match_ids}")
    return all_match_ids


def post_builds(builds: list[dict], last_checked_tooltip: str) -> None:
    hmac_key = bytearray.fromhex(get_updater_config().hmac_key_hex)
    request_dict = {"builds": builds, "last_checked_tooltip": last_checked_tooltip}
    request_bytes = json.dumps(request_dict).encode("utf-8")
    hmac_obj = hmac.new(hmac_key, request_bytes, hashlib.sha256)
    headers = {"X-HMAC-DIGEST-HEX": hmac_obj.hexdigest()}
    resp = requests.post(
        f"{get_updater_config().backend_url}/api/builds",
        data=request_bytes,
        headers=headers,
    )
    raise_for_status_with_detail(resp)


# --------------------------------------------------------------------------------------
# WEB SCRAPING
# --------------------------------------------------------------------------------------


def make_webdriver_options() -> WebDriverOptions:
    options = WebDriverOptions()
    # https://help.pythonanywhere.com/pages/selenium/
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    # https://stackoverflow.com/a/55254431
    options.add_experimental_option("prefs", {"intl.accept_languages": "en,en_US"})
    # https://stackoverflow.com/a/53970825
    options.add_argument("--disable-dev-shm-usage")
    # https://stackoverflow.com/a/59724330
    options.add_argument("window-size=1600,900")
    return options


@dataclasses.dataclass
class Match:
    league: League
    phase: str
    month: int
    day: int
    id: int
    url: str
    last_slash_i: int
    is_old: bool = False
    is_missing: bool = False

    def to_json(self) -> str:
        match_dict = dataclasses.asdict(self)
        del match_dict["url"]
        del match_dict["last_slash_i"]
        return json.dumps(match_dict, ensure_ascii=False)


def scrape_league(driver: WebDriver, league: League) -> list[Match]:
    driver.get(league.schedule_url)

    cookie_accept_button = driver.find_element(By.CLASS_NAME, "approve")
    try:
        cookie_accept_button.click()
    except sel_exc.ElementNotInteractableException:
        time.sleep(FALLBACK_COOKIES_WAIT)
        cookie_accept_button.click()
    time.sleep(0.1)

    phase_elems = driver.find_elements(By.CLASS_NAME, "phase")
    # The filtering is here because in SCC there is (or at least was at one point)
    # an extraenous phase elem with empty text, which would then crash the script.
    phase_elems = [phase_elem for phase_elem in phase_elems if text(phase_elem)]
    phases = [text(phase_elem) for phase_elem in phase_elems]

    all_match_ids = get_all_match_ids(phases)

    matches: list[Match] = []
    for phase_elem, phase, match_ids in zip(phase_elems, phases, all_match_ids):
        match_ids_set = set(match_ids)
        phase_elem.click()
        start = time.time()

        day_elems = driver.find_elements(By.CLASS_NAME, "day")
        for day_elem in day_elems:
            date = text(day_elem.find_element(By.CLASS_NAME, "date"))
            _, month_, day_s = date.split(" ")
            month = MONTH_TO_I[month_]
            day = int(day_s)

            result_link_elems = day_elem.find_elements(By.CLASS_NAME, "results")
            for result_link_elem in result_link_elems:
                match_url = result_link_elem.get_attribute("href")
                last_slash_i, match_id_s = split_on_last_slash(match_url)
                match_id = int(match_id_s)
                match = Match(
                    league=league,
                    phase=phase,
                    month=month,
                    day=day,
                    id=match_id,
                    url=match_url,
                    last_slash_i=last_slash_i,
                )
                matches.append(match)
                if match_id in match_ids_set:
                    match.is_old = True
                    logger.debug(f"Scraped previously|{match.to_json()}")

        delay(0.5, start)

    return matches


def scrape_matches(driver: WebDriver, matches: list[Match]) -> list[dict]:
    match_ids_with_no_stats = get_updater_config().matches_with_no_stats

    builds: list[dict] = []
    for match in t.cast(t.Iterable[Match], tqdm.tqdm(matches)):
        logger.debug(f"Scraping|{match.to_json()}")

        if not check_url_still_same(
            match.league.match_url, match.url, match.last_slash_i
        ):
            logger.warning(f"Unknown match URL|{match.url}")

        try:
            new_builds = scrape_match(driver, match)
            builds.extend(new_builds)
        except NoStats:
            if str(match.id) not in match_ids_with_no_stats:
                match.is_missing = True
                logger.info(f"{NO_STATS_MESSAGE}: {match.id}")
        except Exception:
            logger.exception(f"{match.id}|")

    return builds


def scrape_match(driver: WebDriver, match: Match) -> list[dict]:
    builds_all: list[dict] = []
    games: list[WebElement] = []
    match_url_retries = 3
    for _ in range(match_url_retries):
        driver.get(match.url)

        # Sometimes the match page is just a single h1 element saying there are no
        # stats, so this code attempts to idenfity this situation to avoid a false
        # positive Scraped zero builds exception.
        try:
            match_details = driver.find_element(By.CLASS_NAME, "match-details")
            no_stats = match_details.find_element(By.TAG_NAME, "h1")
            if text(no_stats) == NO_STATS_MESSAGE:
                raise NoStats()
        except sel_exc.NoSuchElementException:
            pass

        games = driver.find_elements(By.CLASS_NAME, "game-btn")
        if games:
            break

    for game_i, game in enumerate(games, 1):
        game.click()
        start = time.time()

        # Find out teams, game length & which team won.
        tmp = driver.find_elements(By.CLASS_NAME, "content-wrapper")[1]
        team_elems = tmp.find_elements(By.TAG_NAME, "strong")
        teams = (text(team_elems[0]), text(team_elems[1]))
        game_length = text(tmp.find_element(By.CLASS_NAME, "game-duration"))
        hours, minutes, seconds = parse_game_length(game_length)
        win_or_loss = tmp.find_element(By.CLASS_NAME, "team-score").text
        if win_or_loss == "W":
            wins = (True, False)
        elif win_or_loss == "L":
            wins = (False, True)
        else:
            raise RuntimeError(f"Could not ascertain victory or loss: {win_or_loss}")

        # Get everything else.
        tables = driver.find_elements(By.CLASS_NAME, "c-PlayerStatsTable")
        if len(tables) != 2:
            raise RuntimeError(
                f"Wrong number of tables with player stats: {len(tables)}"
            )
        builds: tuple[list[dict], list[dict]] = ([], [])
        roles: tuple[dict, dict] = ({}, {})
        duplicated_roles: tuple[set, set] = (set(), set())
        for table_i, table in enumerate(tables):
            stats = table.find_elements(By.CLASS_NAME, "item")
            if not stats or len(stats) % 9 != 0:
                raise RuntimeError(
                    f"Wrong number of player stats in a table: {len(stats)}"
                )
            stats = stats[:-9]

            for player_i in range(len(stats) // 9):
                (
                    player_elem,
                    role_elem,
                    god_elem,
                    kills_elem,
                    deaths_elem,
                    assists_elem,
                    gpm_elem,
                    relic_elems,
                    item_elems,
                ) = stats[player_i * 9 : (player_i + 1) * 9]
                player, role, god, kills, deaths, assists = (
                    text(player_elem),
                    text(role_elem),
                    text(god_elem),
                    int(kills_elem.text),
                    int(deaths_elem.text),
                    int(assists_elem.text),
                )
                role = fix_role(role)
                relics = [
                    item(x) for x in relic_elems.find_elements(By.TAG_NAME, "img")
                ]
                items = [item(x) for x in item_elems.find_elements(By.TAG_NAME, "img")]
                # Optional values: year, season.
                new_build = {
                    "league": match.league.name,
                    "phase": match.phase,
                    "month": match.month,
                    "day": match.day,
                    "game_i": game_i,
                    "match_id": match.id,
                    "win": wins[table_i],
                    "hours": hours,
                    "minutes": minutes,
                    "seconds": seconds,
                    "kda_ratio": kda_ratio(kills, deaths, assists),
                    "kills": kills,
                    "deaths": deaths,
                    "assists": assists,
                    "role": role,
                    "team1": teams[table_i],
                    "team2": teams[1 - table_i],
                    "relics": relics,
                    "items": items,
                    "player1": player,
                    "god1": god,
                }
                builds[table_i].append(new_build)
                if role in roles[table_i]:
                    duplicated_roles[table_i].add(role)
                roles[table_i][role] = new_build

        # Remove duplicated (or morecated) roles,
        # so that opponent gets set to Missing data.
        for table_i in range(2):
            for duplicated_role in duplicated_roles[table_i]:
                del roles[table_i][duplicated_role]

        for table_i in range(2):
            for build in builds[table_i]:
                if opp := roles[1 - table_i].get(build["role"]):
                    build["player2"] = opp["player1"]
                    build["god2"] = opp["god1"]
                else:
                    build["player2"] = "Missing data"
                    build["god2"] = "Missing data"
                logger.debug(f"Build scraped|{json.dumps(build)}")

        builds_all.extend(builds[0])
        builds_all.extend(builds[1])
        delay(0.5, start)

    if not builds_all:
        # For debugging in case it is not reproducible.
        debug_file = STORAGE_DIR / "zero_builds.html"
        debug_file.write_text(driver.page_source, encoding="utf8")
        raise RuntimeError("Scraped zero builds")

    return builds_all


def fix_role(role: str) -> str:
    return "ADC" if role in ["Carry", "Hunter"] else role


def kda_ratio(kills: int, deaths: int, assists: int) -> float:
    return (kills + assists) / max(deaths, 1)


def split_on_last_slash(s: str) -> tuple[int, str]:
    i = s.rfind("/")
    if i == -1:
        raise RuntimeError(f"No slash found: {s}")
    return i, s[i + 1 :]


def check_url_still_same(base_url: str, url: str, last_slash_i: int) -> bool:
    return len(base_url) == last_slash_i and url.startswith(base_url)


MONTH_TO_I = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def text(elem: WebElement) -> str:
    # textContent removes all caps styling.
    return elem.get_attribute("textContent")


def item(elem: WebElement) -> tuple[str, str]:
    name = elem.get_attribute("alt")
    img_url = elem.get_attribute("src")
    last_slash_i, image_name = split_on_last_slash(img_url)
    if not check_url_still_same(IMG_URL, img_url, last_slash_i):
        logger.warning(f"Unknown image URL|{img_url}")
    return name, image_name


def parse_game_length(game_length: str) -> tuple[int, int, int]:
    game_length_split = game_length.split(":")
    if len(game_length_split) == 2:
        minutes_s, seconds_s = game_length_split
        minutes, seconds = int(minutes_s), int(seconds_s)
        if minutes < 60:
            hours = 0
        else:
            hours = math.floor(minutes / 60)
            minutes = minutes % 60
    elif len(game_length_split) == 3:
        hours_s, minutes_s, seconds_s = game_length_split
        hours, minutes, seconds = int(hours_s), int(minutes_s), int(seconds_s)
    else:
        raise RuntimeError(f"Could not parse game length: {game_length}")
    return hours, minutes, seconds


# --------------------------------------------------------------------------------------
# OTHER
# --------------------------------------------------------------------------------------


@dataclasses.dataclass
class MatchCount:
    old = 0
    new = 0
    missing = 0


def format_last_checked_tooltip(matches: list[Match]) -> str:
    spl = get_match_count(SPL, matches)
    scc = get_match_count(SCC, matches)
    return f"""Matches Log
Bad | Good
SPL: {spl.missing} | {spl.new + spl.old}
SCC: {scc.missing} | {scc.new + scc.old}
"""


def get_match_count(league: League, matches: list[Match]) -> MatchCount:
    match_count = MatchCount()
    matches_league = [match for match in matches if match.league is league]
    for match in matches_league:
        if match.is_old:
            match_count.old += 1
        elif match.is_missing:
            match_count.missing += 1
        else:
            match_count.new += 1
    return match_count


if __name__ == "__main__":
    main()
