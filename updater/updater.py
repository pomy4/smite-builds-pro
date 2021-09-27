import pathlib
import datetime
import itertools
import logging
import time
import json
import hmac
import hashlib
import os

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tqdm
from dotenv import dotenv_values

spl_schedule_url = 'https://www.smiteproleague.com/schedule'
spl_matches_url = 'https://www.smiteproleague.com/matches'
cdn_images_url = 'https://webcdn.hirezstudios.com/smite/item-icons'
min_click_delay = 0.5
implicit_wait = 3
match_url_retries = 3

HMAC_KEY_HEX = 'HMAC_KEY_HEX'
BACKEND_URL = 'BACKEND_URL'
required_env_vars = [HMAC_KEY_HEX, BACKEND_URL]

month_to_i = {
    'January': 1, 'February': 2, 'March': 3,
    'April': 4, 'May': 5, 'June': 6,
    'July': 7, 'August': 8, 'September': 9,
    'October': 10, 'November': 11, 'December': 12
    }

def text(elem):
    # textContent removes all caps styling.
    return elem.get_attribute('textContent')

def number(number):
    return int(number)

def item(elem):
    name = elem.get_attribute('alt')
    url = elem.get_attribute('src')
    last = url.rfind('/')
    if (base_url := url[:last]) != cdn_images_url:
        logging.warning(f'Unknown URL for the CDN with images|{base_url}')
    image_name = url[last + 1:]
    return name, image_name

def click_delay(start):
    end = time.time()
    time_spent = end - start
    time_remaining = min_click_delay - time_spent
    if time_remaining > 0:
        time.sleep(time_remaining)

def better_raise_for_status(resp: requests.Response):
    if not resp.ok:
        msg  = f'HTTP response was not OK!\n'
        msg += f'Url: {resp.url}\n'
        msg += f'Status code: {resp.status_code}\n'
        msg += f'Status code meaning: {resp.reason}'
        if more_detail := resp.text:
            msg += f'\nMore detail: {more_detail}'
        raise RuntimeError(msg)

def config_from_env():
    config = {**dotenv_values('../.env'), **os.environ}

    for env_var in required_env_vars:
        if env_var not in config:
            raise RuntimeError(f'\"{env_var}\" not set.')

    return config

def send_builds(config, builds):
    hmac_key = bytearray.fromhex(config[HMAC_KEY_HEX])
    builds_bytes = json.dumps(builds).encode('utf-8')
    hmac_obj = hmac.new(hmac_key, builds_bytes, hashlib.sha256)
    headers = {'X-HMAC_DIGEST_HEX': hmac_obj.hexdigest()}
    builds_resp = requests.post(f'{config[BACKEND_URL]}/builds', data=builds_bytes, headers=headers)
    better_raise_for_status(builds_resp)

def scrape_match(driver, phase, month, day, match_url, match_id):
    for _ in range(match_url_retries):
        driver.get(match_url)
        builds_all = []
        games = driver.find_elements_by_class_name('game-btn')
        if games:
            break

    for game_i, game in enumerate(games, 1):
        game.click()
        start = time.time()
        # Find out teams, game length & which team won.
        tmp = driver.find_elements_by_class_name('content-wrapper')[1]
        teams = tmp.find_elements_by_tag_name('strong')
        teams = (text(teams[0]), text(teams[1]))
        game_length = text(tmp.find_element_by_class_name('game-duration'))
        minutes, seconds = game_length.split(':')
        minutes, seconds = number(minutes), number(seconds)
        win_or_loss = tmp.find_element_by_class_name('team-score').text
        if win_or_loss == 'W':
            wins = (True, False)
        elif win_or_loss == 'L':
            wins = (False, True)
        else:
            raise RuntimeError(f'Could not ascertain victory or loss: {win_or_loss}')
        # Get everything else.
        tables = driver.find_elements_by_class_name('c-PlayerStatsTable')
        if len(tables) != 2:
            raise RuntimeError(f'Wrong number of tables with player stats: {len(tables)}')
        builds = ([], [])
        roles = ({}, {})
        for table_i, table in enumerate(tables):
            stats = table.find_elements_by_class_name('item')
            if not stats or len(stats) % 9 != 0:
                raise RuntimeError(f'Wrong number of player stats in a table: {len(stats)}')
            stats = stats[:-9]
            for player_i in range(len(stats) // 9):
                player, role, god, kills, deaths, assists, gpm, relics, items = stats[player_i * 9 : (player_i + 1) * 9]
                player, role, god, kills, deaths, assists = text(player), text(role), text(god), \
                    number(kills.text), number(deaths.text), number(assists.text)
                if role == 'Hunter': role = 'ADC'
                relics = [item(x) for x in relics.find_elements_by_tag_name('img')]
                items = [item(x) for x in items.find_elements_by_tag_name('img')]
                # Optional values: year, season.
                new_build = {'league': 'SPL', 'phase': phase, 'month': month, 'day': day, 'game_i': game_i,
                    'match_id': match_id, 'win' : wins[table_i], 'minutes': minutes, 'seconds': seconds,
                    'kda_ratio': (kills + assists) / (deaths if deaths > 0 else 1),
                    'kills': kills, 'deaths': deaths, 'assists': assists, 'role': role,
                    'team1': teams[table_i], 'team2': teams[1-table_i], 'relics': relics, 'items': items,
                    'player1': player, 'god1': god}
                builds[table_i].append(new_build)
                roles[table_i][role] = new_build
        for table_i in range(2):
            for build in builds[table_i]:
                if opp := roles[1-table_i].get(build['role']):
                    build['player2'] = opp['player1']
                    build['god2'] = opp['god1']
                else:
                    build['player2'] = 'Missing data'
                    build['god2'] = 'Missing data'
                logging.info(f'Build scraped|{json.dumps(build)}')
        if (builds_cnt := len(builds[0]) + len(builds[1])) < 10:
            logging.warning(f'Missing build(s) in a game|{10 - builds_cnt}')
        builds_all.extend(builds[0])
        builds_all.extend(builds[1])
        click_delay(start)

    if not builds_all:
        raise RuntimeError("Scraped zero builds")

    return builds_all

if __name__ == '__main__':
    try:
        # Set up logging.
        log_folder = pathlib.Path('logs')
        today = datetime.datetime.now().date().isoformat()
        for i in itertools.count():
            suffix = f'({i})' if i else ''
            log_path = log_folder / f'{today}{suffix}.log'
            if not log_path.is_file():
                break
        # https://hg.python.org/cpython/file/5c4ca109af1c/Lib/logging/__init__.py#l399
        logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s|%(levelname)s|%(message)s')

        config = config_from_env()

        if config.get('LAUNCH_WATCHDOG'):
            import subprocess
            subprocess.call(['bash', './watchdog.sh'])

        # Scraping stuff.
        with webdriver.Firefox() as driver:
            driver.get(spl_schedule_url)
            driver.implicitly_wait(implicit_wait)

            phase_elems = driver.find_elements_by_class_name('phase')
            phases = [text(phase_elem) for phase_elem in phase_elems]

            # Backend stuff.
            all_match_ids_resp = requests.post(f'{config[BACKEND_URL]}/phases', json=phases)
            better_raise_for_status(all_match_ids_resp)
            all_match_ids = all_match_ids_resp.json()
            assert len(phases) == len(all_match_ids)

            # Some more scraping stuff.
            to_scrape = []
            for phase_elem, phase, match_ids in zip(phase_elems, phases, all_match_ids):
                match_ids = set(match_ids)
                phase_elem.click()
                start = time.time()
                day_elems = driver.find_elements_by_class_name('day')
                for day_elem in day_elems:
                    date = text(day_elem.find_element_by_class_name('date'))
                    _, month, day = date.split(' ')
                    month = month_to_i[month]
                    day = number(day)
                    result_link_elems = day_elem.find_elements_by_class_name('results')
                    for result_link_elem in result_link_elems:
                        match_url = result_link_elem.get_attribute('href')
                        match_id = number(match_url.split('/')[-1])
                        if match_id not in match_ids:
                            to_scrape.append((phase, month, day, match_url, match_id))
                        else:
                            logging.info(f'Skipping|{phase}|{match_id}')
                click_delay(start)

            builds = []
            for phase, month, day, match_url, match_id in tqdm.tqdm(to_scrape):
                logging.info(f'Scraping|{phase}|{match_id}')
                try:
                    if (base_url := '/'.join(match_url.split('/')[:-1])) != spl_matches_url:
                        logging.warning(f'Unknown URL for the SPL matches|{base_url}')
                    new_builds = scrape_match(driver, phase, month, day, match_url, match_id)
                    builds.extend(new_builds)
                except Exception as e:
                    logging.exception(e)

            # Some more backend stuff.
            send_builds(config, builds)

    except BaseException as e:
        logging.exception(e)
        raise e
