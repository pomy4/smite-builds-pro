"""
One-off script to check for some inconsistencies in the database.
Kept since it might be useful.
"""
import collections
import pprint

import be.models
from be.models import Build

# Find games where there is a duplicated player2.
with be.models.db:
    players = [b.player1 for b in Build.select(Build.player1).distinct()]
    for player in players:
        games_with_player1 = [
            (b.match_id, b.game_i)
            for b in Build.select(Build.match_id, Build.game_i).where(
                Build.player1 == player
            )
        ]
        games_with_player2 = [
            (b.match_id, b.game_i)
            for b in Build.select(Build.match_id, Build.game_i).where(
                Build.player2 == player
            )
        ]

        if len(games_with_player1) == len(games_with_player2):
            continue

        first_time = set()
        for game in games_with_player2:
            if game in first_time:
                print("DUP PLAYER2", player, game)
            else:
                first_time.add(game)

# Find games with missing builds or some issues with role.
with be.models.db:
    builds = list(Build.select())

games = collections.defaultdict(list)

for build in builds:
    games[(build.match_id, build.game_i)].append(build)

missing_build = []
issue_with_role = []
for game_i, game in games.items():  # type:ignore
    if len(game) != 10:
        missing_build.append(game_i)
        continue

    teams = collections.defaultdict(list)
    for build in game:
        teams[build.team1].append(build)

    if len(teams) != 2:
        issue_with_role.append(game_i)
    if len(list(teams.values())[0]) != 5:
        issue_with_role.append(game_i)
    if len(list(teams.values())[1]) != 5:
        issue_with_role.append(game_i)

    roles = ["ADC", "Jungle", "Mid", "Solo", "Support"]
    for team_i, team in teams.items():
        team_roles = sorted(b.role for b in team)
        if roles != team_roles:
            issue_with_role.append(game_i)

if missing_build:
    print("MISSING BUILD")
    pprint.pprint(missing_build)
if issue_with_role:
    print("ISSUE WITH ROLE")
    pprint.pprint(issue_with_role)
