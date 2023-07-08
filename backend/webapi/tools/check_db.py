"""
One-off script to check for some inconsistencies in the database.
Kept since it might be useful.
"""
import collections
import pprint

import sqlalchemy as sa

from backend.webapi.models import Build, db_session

# Find games where there is a duplicated player2.
with db_session():
    players = db_session.scalars(sa.select(Build.player1).distinct()).all()
    for player in players:
        games_with_player1 = db_session.execute(
            sa.select(Build.match_id, Build.game_i).where(Build.player1 == player)
        ).all()
        games_with_player2 = db_session.execute(
            sa.select(Build.match_id, Build.game_i).where(Build.player2 == player)
        ).all()

        if len(games_with_player1) == len(games_with_player2):
            continue

        first_time = set()
        for game in games_with_player2:
            if game in first_time:
                print("DUP PLAYER2", player, game)
            else:
                first_time.add(game)

# Find games with missing builds or some issues with role.
with db_session():
    builds = db_session.scalars(sa.select(Build)).all()

games = collections.defaultdict(list)

for build in builds:
    games[(build.match_id, build.game_i)].append(build)

missing_build = []
issue_with_role = []
for game_id, game in games.items():  # type:ignore
    if len(game) != 10:
        missing_build.append(game_id)
        continue

    teams = collections.defaultdict(list)
    for build in game:
        teams[build.team1].append(build)

    if len(teams) != 2:
        issue_with_role.append(game_id)
    if len(list(teams.values())[0]) != 5:
        issue_with_role.append(game_id)
    if len(list(teams.values())[1]) != 5:
        issue_with_role.append(game_id)

    roles = ["ADC", "Jungle", "Mid", "Solo", "Support"]
    for team_i, team in teams.items():
        team_roles = sorted(b.role for b in team)
        if roles != team_roles:
            issue_with_role.append(game_id)

if missing_build:
    print("MISSING BUILD")
    pprint.pprint(missing_build)
if issue_with_role:
    print("ISSUE WITH ROLE")
    pprint.pprint(issue_with_role)
