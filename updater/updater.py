import pathlib
import datetime
import itertools
import logging
import time
import json
import hmac
import hashlib
import os
import sys

import requests
from selenium import webdriver
import tqdm
from dotenv import load_dotenv

backend_url = 'http://localhost:8080'
spl_schedule_url = 'https://www.smiteproleague.com/schedule'
spl_matches_url = 'https://www.smiteproleague.com/matches'
min_click_delay = 0.333

month_to_i = {
    'January': 1, 'February': 2, 'March': 3,
    'April': 4, 'May': 5, 'June': 6,
    'July': 7, 'August': 8, 'September': 9,
    'October': 10, 'November': 11, 'December': 12
    }

def text(elem):
    # textContent to remove all caps styling.
    text = elem.get_attribute('textContent')
    if not 1 <= len(text) <= 30:
        raise Exception(f'Error text: {text}')
    return text

def number(number):
     # Also checks if is positive.
    if not number.isdigit():
        raise Exception('Error: number')
    return int(number)

def item(elem):
    url = elem.get_attribute('src')
    last = url.rfind('/')
    if last == -1:
        raise Exception('Error: item (1)')
    short = url[last + 1:]
    url = url[:last]
    long = elem.get_attribute('alt')
    if not 1 <= len(short) <= 30 or not 1 <= len(long) <= 30 \
            or url != 'https://webcdn.hirezstudios.com/smite/item-icons':
        raise Exception('Error: item (2)')
    short_evolved, long_evolved  = 'evolved-', 'Evolved '
    if short.startswith(short_evolved) and long.startswith(long_evolved):
        short, long = short[len(short_evolved):], long[len(long_evolved):]
    return short, long

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

def get_hmac_key_hex_from_env():
    load_dotenv('../.env')
    env_var_name = 'HMAC_KEY_HEX'
    if not (hmac_key_hex := os.getenv(env_var_name)):
        logging.critical(f'{env_var_name} not set.')
        sys.exit(1)
    return hmac_key_hex

def send_builds(hmac_key_hex, builds):
    hmac_key = bytearray.fromhex(hmac_key_hex)
    builds_bytes = json.dumps(builds).encode('utf-8')
    hmac_obj = hmac.new(hmac_key, builds_bytes, hashlib.sha256)
    headers = {'X-HMAC_DIGEST_HEX': hmac_obj.hexdigest()}
    builds_resp = requests.post(f'{backend_url}/builds', data=builds_bytes, headers=headers)
    better_raise_for_status(builds_resp)

def scrape_match(driver, phase, month, day, match_url, match_id):
    driver.get(match_url)
    builds_all_games = []
    games = driver.find_elements_by_class_name('game-btn')
    for game_i, game in enumerate(games, 1):
        game.click()
        start = time.time()
        # Find out teams, game length & which team won.
        tmp = driver.find_elements_by_class_name('content-wrapper')[1]
        teams = tmp.find_elements_by_tag_name('strong')
        team1 = text(teams[0])
        team2 = text(teams[1])
        game_length = text(tmp.find_element_by_class_name('game-duration'))
        minutes, seconds = game_length.split(':')
        minutes, seconds = number(minutes), number(seconds)
        win_or_loss = tmp.find_element_by_class_name('team-score').text
        if win_or_loss == 'W':
            first_team_won = True
        elif win_or_loss == 'L':
            first_team_won = False
        else:
            raise Exception('Error: win')
        # Get everything else.
        stats = driver.find_elements_by_class_name('item')
        if len(stats) != 128:
            raise Exception('Error: stats')
        # Remove P&Bs and totals.
        stats = stats[:45] + stats[54:99]
        roles = {}
        builds_one_game = []
        for player_i in range(10):
            player, role, god, kills, deaths, assists, gpm, relics, items = stats[player_i * 9 : (player_i + 1) * 9]
            player, role, god, kills, deaths, assists = text(player), text(role), text(god), \
                number(kills.text), number(deaths.text), number(assists.text)
            relics = [item(x) for x in relics.find_elements_by_tag_name('img')]
            items = [item(x) for x in items.find_elements_by_tag_name('img')]
            win, team = (first_team_won, team1) if player_i < 5 else (not first_team_won, team2)
            # Optional values: year, season.
            new_build = {'league': 'SPL', 'phase': phase, 'month': month, 'day': day, 'game_i': game_i,
                'match_id': match_id, 'win' : win, 'minutes': minutes, 'seconds': seconds,
                'kills': kills, 'deaths': deaths, 'assists': assists, 'role': role,
                'player1': player, 'god1': god, 'team1': team, 'relics': relics, 'items': items}
            if role not in roles:
                if player_i >= 5:
                    raise Exception('Error: role (1)')
                roles[role] = player_i
            else:
                if player_i < 5:
                    raise Exception('Error role (2)')
                opp = builds_one_game[roles[role]]
                opp['player2'], opp['god2'], opp['team2'] = player, god, team
                new_build['player2'], new_build['god2'], new_build['team2'] = opp['player1'], opp['god1'], opp['team1']
            builds_one_game.append(new_build)
        for x in builds_one_game:
            logging.info(f'Build scraped|{json.dumps(x)}')
        builds_all_games.extend(builds_one_game)
        click_delay(start)
    return builds_all_games

if __name__ == '__main__':
    # Set up logging.
    log_folder = pathlib.Path('logs')
    today = datetime.datetime.now().date().isoformat()
    for i in itertools.count():
        suffix = f'({i})' if i else ''
        log_path = log_folder / f'{today}{suffix}.log'
        if not log_path.is_file():
            break
    # https://hg.python.org/cpython/file/5c4ca109af1c/Lib/logging/__init__.py#l399
    logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s|%(message)s')

    hmac_key_hex = get_hmac_key_hex_from_env()

    if os.getenv('LAUNCH_WATCHDOG'):
        import subprocess
        subprocess.call(['bash', './watchdog.sh'])

    try:
        # Scraping stuff.
        with webdriver.Firefox() as driver:
            driver.get(spl_schedule_url)
            driver.implicitly_wait(3)

            phase_elems = driver.find_elements_by_class_name('phase')
            phases = [text(phase_elem) for phase_elem in phase_elems]

            # Backend stuff.
            last_match_ids_resp = requests.post(f'{backend_url}/phases', json=phases)
            better_raise_for_status(last_match_ids_resp)
            last_match_ids = last_match_ids_resp.json()
            assert len(phases) == len(last_match_ids)

            # Some more scraping stuff.
            to_scrape = []
            for phase_elem, phase, last_match_id in zip(phase_elems, phases, last_match_ids):
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
                        match_url_split = match_url.split('/')
                        if '/'.join(match_url_split[:-1]) != spl_matches_url:
                            raise Exception('Error: match url')
                        match_id = number(match_url_split[-1])
                        if match_id > last_match_id:
                            to_scrape.append((phase, month, day, match_url, match_id))
                        else:
                            logging.info(f'Skipping|{phase}|{match_id}')
                click_delay(start)

            builds = []
            for phase, month, day, match_url, match_id in tqdm.tqdm(to_scrape):
                logging.info(f'Scraping|{phase}|{match_id}')
                new_builds = scrape_match(driver, phase, month, day, match_url, match_id)
                builds.extend(new_builds)

            # Some more backend stuff.
            send_builds(hmac_key_hex, builds)

    except BaseException as e:
        logging.exception(e)
        raise e
