from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from time import sleep
import pickle
# maybe dataclass for new_build

def text(elem):
    # textContent to remove all caps styling.
    text = elem.get_attribute('textContent')
    if not 1 <= len(text) <= 30:
        raise Exception('Error: text')
    return text

def number(elem):
    number = elem.text
    if not number.isdigit():
        raise Exception('Error: number')
    return number

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
    return short, long

driver = webdriver.Firefox()
driver.get("https://www.smiteproleague.com/schedule/")
driver.implicitly_wait(3)

builds = []

phases = driver.find_elements_by_class_name('phase')
phases.append(driver.find_element_by_class_name('phase-selector'))
for phase in phases[:1]:
    phase.click()
    phase = text(phase)
    days = driver.find_elements_by_class_name('day')
    for day in days[:1]:
        date = text(day.find_element_by_class_name('date'))
        matches = day.find_elements_by_class_name('icon-calendar')
        for match in matches[:1]:
            match.click()
            games = driver.find_elements_by_class_name('game-btn')
            url = driver.current_url.split('/')
            match_id = url[-1]
            if (not match_id.isdigit()):
                raise Exception('Error: match id')
            if '/'.join(url[:-1]) != 'https://www.smiteproleague.com/matches':
                raise Exception('Error: match url')
            for game_i, game in enumerate(games[:1]):
                game.click()
                # Find out teams, game length & which team won.
                tmp = driver.find_elements_by_class_name('content-wrapper')[1]
                teams = tmp.find_elements_by_tag_name('strong')
                team1 = text(teams[0])
                team2 = text(teams[1])
                game_length = text(tmp.find_element_by_class_name('game-duration'))
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
                new_builds = []
                for player_i in range(10):
                    print(player_i)
                    player, role, god, kills, deaths, assists, gpm, relics, build = stats[player_i * 9 : (player_i + 1) * 9]
                    player, role, god, kills, deaths, assists = text(player), text(role), text(god), number(kills), number(deaths), number(assists)
                    relics, build = [item(x) for x in relics.find_elements_by_tag_name('img')], [item(x) for x in build.find_elements_by_tag_name('img')]
                    win, team = (first_team_won, team1) if player_i < 5 else (not first_team_won, team2)
                    new_build = {'league': 'SPL', 'phase': phase, 'date': date, 'game_i': game_i+1, 'match_id': match_id,
                        'win' : win, 'game_length': game_length, 'kills': kills, 'deaths': deaths, 'assists': assists, 'role': role,
                        'player1': player,  'god1': god, 'team1': team, 'relics': relics, 'build': build}
                    if role not in roles:
                        if player_i >= 5:
                            raise Exception('Error: role (1)')
                        roles[role] = player_i
                    else:
                        if player_i < 5:
                            raise Exception('Error role (2)')
                        opp = new_builds[roles[role]]
                        opp['player2'], opp['god2'], opp['team2'] = player, god, team
                        new_build['player2'], new_build['god2'], new_build['team2'] = opp['player1'], opp['god1'], opp['team1']
                    new_builds.append(new_build)
                builds.extend(new_builds)
            driver.back()
            pickle.dump(builds, open('test2.p', 'wb'))
sleep(3)
driver.close()
