import dataclasses
import datetime
import hashlib
import hmac
import itertools
import json
import logging
import math
import os
import pathlib
import subprocess
import time
import typing
from typing import Iterable

import requests
import selenium.common.exceptions
import selenium.webdriver
import tqdm
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

import shared
from shared import League

IMPLICIT_WAIT = 3


def main() -> None:
    setup_logging()

    try:
        shared.load_default_dot_env()
        check_required_env_vars()
        if os.getenv(shared.USE_WATCHDOG):
            subprocess.run(["pkill", "watchdog.sh"])
            subprocess.Popen(["./updater/watchdog.sh"])

        options = make_webdriver_options()
        with selenium.webdriver.Chrome(options=options) as driver:
            driver.implicitly_wait(IMPLICIT_WAIT)
            matches = scrape_league(driver, shared.SPL)
            matches += scrape_league(driver, shared.SCC)
            builds = scrape_matches(driver, matches)
            post_builds(builds)

    except BaseException as e:
        logging.exception(e)
        raise e


# --------------------------------------------------------------------------------------
# LOGGING & ENV VARS
# --------------------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s|%(levelname)s|%(message)s"


def setup_logging() -> None:
    log_folder = pathlib.Path("upd/logs")
    if not log_folder.is_dir():
        raise RuntimeError("Log folder does not exist")

    today = datetime.datetime.now().date().isoformat()
    for i in itertools.count():
        suffix = f"({i})" if i else ""
        log_path = log_folder / f"{today}{suffix}.log"
        if log_path.is_file():
            continue
        logging.basicConfig(filename=log_path, level=logging.INFO, format=LOG_FORMAT)
        break


def check_required_env_vars() -> None:
    for env_var in [shared.HMAC_KEY_HEX, shared.BACKEND_URL]:
        if os.getenv(env_var) is None:
            raise RuntimeError(f"Unset env var: {env_var}")


# --------------------------------------------------------------------------------------
# BACKEND COMMUNICATION
# --------------------------------------------------------------------------------------


def get_all_match_ids(phases: list[str]) -> list[list[int]]:
    all_match_ids_resp = requests.post(
        f"{os.getenv(shared.BACKEND_URL)}/api/phases", json=phases
    )
    better_raise_for_status(all_match_ids_resp)
    all_match_ids = all_match_ids_resp.json()
    if len(phases) != len(all_match_ids):
        raise RuntimeError(f"/api/phases returned wrong list: {all_match_ids}")
    return all_match_ids


def post_builds(builds: list[dict]) -> None:
    hmac_key = bytearray.fromhex(os.environ[shared.HMAC_KEY_HEX])
    builds_bytes = json.dumps(builds).encode("utf-8")
    hmac_obj = hmac.new(hmac_key, builds_bytes, hashlib.sha256)
    headers = {"X-HMAC-DIGEST-HEX": hmac_obj.hexdigest()}
    builds_resp = requests.post(
        f"{os.getenv(shared.BACKEND_URL)}/api/builds",
        data=builds_bytes,
        headers=headers,
    )
    better_raise_for_status(builds_resp)


def better_raise_for_status(resp: requests.Response) -> None:
    if not resp.ok:
        msg = "HTTP response was not OK!\n"
        msg += f"Url: {resp.url}\n"
        msg += f"Status code: {resp.status_code}\n"
        msg += f"Status code meaning: {resp.reason}"
        if more_detail := resp.text:
            msg += f"\nMore detail: {more_detail}"
        raise RuntimeError(msg)


# --------------------------------------------------------------------------------------
# WEB SCRAPING
# --------------------------------------------------------------------------------------


def make_webdriver_options() -> ChromeOptions:
    options = ChromeOptions()
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

    def to_json(self) -> str:
        match_dict = dataclasses.asdict(self)
        del match_dict["url"]
        del match_dict["last_slash_i"]
        return json.dumps(match_dict, ensure_ascii=False)


def scrape_league(driver: WebDriver, league: League) -> list[Match]:
    driver.get(league.schedule_url)

    cookie_accept_button = driver.find_element(By.CLASS_NAME, "approve")
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
                if match_id not in match_ids_set:
                    matches.append(match)
                else:
                    logging.info(f"Skipping|{match.to_json()}")

        shared.delay(0.5, start)

    return matches


def scrape_matches(driver: WebDriver, matches: list[Match]) -> list[dict]:
    builds: list[dict] = []
    for match in typing.cast(Iterable[Match], tqdm.tqdm(matches)):
        logging.info(f"Scraping|{match.to_json()}")

        if not check_url_still_same(
            match.league.match_url, match.url, match.last_slash_i
        ):
            logging.warning(f"Unknown match URL|{match.url}")

        try:
            new_builds = scrape_match(driver, match)
            builds.extend(new_builds)
        except Exception as e:
            logging.exception(e)

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
            if text(no_stats) == "There are no stats for this match":
                logging.info("There are no stats for this match")
                return []
        except selenium.common.exceptions.NoSuchElementException:
            pass

        games = driver.find_elements(By.CLASS_NAME, "game-btn")
        if games:
            break

    for game_i, game in enumerate(games, 1):
        game.click()
        start = time.time()

        # Find out teams, game length & which team won.
        tmp = driver.find_elements(By.CLASS_NAME, "content-wrapper")[1]
        teams = tmp.find_elements(By.TAG_NAME, "strong")
        teams = (text(teams[0]), text(teams[1]))
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
        for table_i, table in enumerate(tables):
            stats = table.find_elements(By.CLASS_NAME, "item")
            if not stats or len(stats) % 9 != 0:
                raise RuntimeError(
                    f"Wrong number of player stats in a table: {len(stats)}"
                )
            stats = stats[:-9]

            for player_i in range(len(stats) // 9):
                player, role, god, kills, deaths, assists, gpm, relics, items = stats[
                    player_i * 9 : (player_i + 1) * 9
                ]
                player, role, god, kills, deaths, assists = (
                    text(player),
                    text(role),
                    text(god),
                    int(kills.text),
                    int(deaths.text),
                    int(assists.text),
                )
                role = fix_role(role)
                relics = [item(x) for x in relics.find_elements(By.TAG_NAME, "img")]
                items = [item(x) for x in items.find_elements(By.TAG_NAME, "img")]
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
                roles[table_i][role] = new_build

        for table_i in range(2):
            for build in builds[table_i]:
                if opp := roles[1 - table_i].get(build["role"]):
                    build["player2"] = opp["player1"]
                    build["god2"] = opp["god1"]
                else:
                    build["player2"] = "Missing data"
                    build["god2"] = "Missing data"
                logging.info(f"Build scraped|{json.dumps(build)}")

        if (builds_cnt := len(builds[0]) + len(builds[1])) < 10:
            logging.warning(f"Missing build(s) in a game|{10 - builds_cnt}")

        builds_all.extend(builds[0])
        builds_all.extend(builds[1])
        shared.delay(0.5, start)

    if not builds_all:
        raise RuntimeError("Scraped zero builds")

    return builds_all


def fix_role(role: str) -> str:
    return "ADC" if role == "Hunter" else role


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
    if not check_url_still_same(shared.IMG_URL, img_url, last_slash_i):
        logging.warning(f"Unknown image URL|{img_url}")
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
    elif len(game_length) == 3:
        hours_s, minutes_s, seconds_s = game_length_split
        hours, minutes, seconds = int(hours_s), int(minutes_s), int(seconds_s)
    else:
        raise RuntimeError(f"Could not parse game length: {game_length}")
    return hours, minutes, seconds
