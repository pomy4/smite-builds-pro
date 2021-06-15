from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from time import sleep
import pickle
# import dataclasses
# maybe check lengths of strings

driver = webdriver.Firefox()
driver.get("https://www.smiteproleague.com/scores/")
driver.implicitly_wait(3)

builds = []

phases = []
phases.extend(driver.find_elements_by_class_name('phase'))
phases.append(driver.find_element_by_class_name('phase-selector'))
for phase in phases[:1]:
    phase.click()
    # Loop on weeks.
    while True:
        matches = driver.find_elements_by_class_name('icon-calendar')
        for match in matches[:1]:
            match.click()
            games = driver.find_elements_by_class_name('game-btn')
            match_id = driver.current_url.split('/')[-1]
            if (not match_id.isdigit()):
                raise Exception('Failed to parse match id!')
            for game_i, game in enumerate(games[:1]):
                game.click()
                # Find out game length & which team won.
                tmp = driver.find_elements_by_class_name('game-result-wrapper')[1]
                game_length = tmp.find_element_by_class_name('game-duration').text
                win_or_loss = tmp.find_element_by_class_name('team-score').text
                if win_or_loss == 'W':
                    first_team_won = True
                elif win_or_loss == 'L':
                    first_team_won = False
                else:
                    raise Exception('Failed to parse which team won!')
                # Get everything else.
                stats = driver.find_elements_by_class_name('item')
                if len(stats) != 128:
                    raise Exception('Failed to parse builds!')
                # Remove P&Bs and totals.
                stats = stats[:45] + stats[54:99]
                for player_i in range(10):
                    name, role, god, kills, deaths, assists, gpm, relics, build = stats[player_i * 9 : (player_i + 1) * 9]
                    # textContent to remove all caps styling.
                    name, role, god, kills, deaths, assists = name.get_attribute('textContent'), role.get_attribute('textContent'), \
                        god.get_attribute('textContent'), kills.text, deaths.text, assists.text
                    if not name or not role or not god or not kills.isdigit() or not deaths.isdigit() or not assists.isdigit():
                        raise Exception("Failed to parse build!")
                    builds.append({'name': name, 'role': role, 'god': god, 'kills': int(kills), 'deaths': int(deaths), 'assists': int(assists), 'game_i': int(game_i),
                        'win' : (first_team_won and player_i < 5) or (not first_team_won and player_i >= 5), 'match_id': int(match_id), 'game_length' : game_length})
            driver.back()
            pickle.dump(builds, open('test.p', 'wb'))
        sleep(3)
        break
        # Get to previous week.
        prev = driver.find_element_by_class_name('arrow-container')
        if not prev.is_enabled():
            break
        else:
            prev.click()

driver.close()
