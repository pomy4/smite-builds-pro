"""
One-off script to convert tsv from Blues' spreadsheet to the structure returned
by the SPL website backend (for the 3_get_builds.py script).
"""

import collections as cc
import csv
import json

FILE, EVENT_IN, EVENT_OUT = "s10.tsv.log", "SWC 2024", "SPL|SMITE World Championship"

SET_INFO = {
    "Ferrymen vs. Scarabs": {
        "month": 1,
        "day": 12,
        "match_id": 4452,
    },
    "Dragons vs. Ravens": {
        "month": 1,
        "day": 12,
        "match_id": 4453,
    },
    "Leviathans vs. Mambo": {
        "month": 1,
        "day": 12,
        "match_id": 4454,
    },
    "Warriors vs. Kings": {
        "month": 1,
        "day": 12,
        "match_id": 4455,
    },
    "Ferrymen vs. Dragons": {
        "month": 1,
        "day": 13,
        "match_id": 4456,
    },
    "Leviathans vs. Warriors": {
        "month": 1,
        "day": 13,
        "match_id": 4457,
    },
    "Dragons vs. Warriors": {
        "month": 1,
        "day": 14,
        "match_id": 4458,
    },
}

with open(FILE, "r", encoding="utf8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    all_builds = [row for row in reader if row["Event"] == EVENT_IN]

print(len(all_builds))

# Split into sets and games
sets: dict = cc.defaultdict(lambda: {"games": cc.defaultdict(list)})
for build in all_builds:
    set_name = build["Set"]
    game_i = build["Game #"]
    sets[set_name]["games"][game_i].append(build)

# Turn games to arrays
for set in sets.values():
    last_game_i = max(map(int, set["games"].keys()))
    new_games = [set["games"][str(game_i)] for game_i in range(1, last_game_i + 1)]
    set["games"] = new_games

# Add set info
for set_name, set in sets.items():
    set.update(SET_INFO[set_name])

# Prepare games
for set in sets.values():
    new_games = []
    for players in set["games"]:

        team_plus_wl_set = sorted(
            {(player["Team Abb."], player["W / L"]) for player in players}
        )
        assert len(team_plus_wl_set) == 2
        team_totals = [{"team": team} for team, _ in team_plus_wl_set]
        winning_team = 0 if team_plus_wl_set[0][1] == "1" else 1

        game_duration_set = {player["Game Length"] for player in players}
        assert len(game_duration_set) == 1
        total_seconds = float(game_duration_set.pop()) * 1440
        assert total_seconds < 3600
        minutes = int(total_seconds / 60)
        seconds = int(total_seconds % 60)
        game_duration = f"{minutes}:{seconds:02}"

        new_games.append(
            {
                "players": players,
                "team_totals": team_totals,
                "winning_team": winning_team,
                "game_duration": game_duration,
            }
        )
    set["data"] = {"games": new_games}
    del set["games"]


def prepare_player(player: dict) -> dict:
    relics: list[str] = [player[f"Relic {i}"] for i in range(1, 2 + 1)]
    items: list[str] = [player[f"Item {i}"] for i in range(1, 6 + 1)]
    return {
        "name": player["Player"],
        "team": player["Team Abb."],
        "god": player["God"],
        "role": player["Role"],
        "kills": int(player["Kills"]),
        "deaths": int(player["Deaths"]),
        "assists": int(player["Assists"]),
        "relics": [rename_item(relic) for relic in relics if relic],
        "build": [rename_item(item) for item in items if item],
    }


def rename_item(item: str) -> str:
    return {"Gem of Fate": "Gem Of Fate"}.get(item, item)


# Prepare players
for set in sets.values():
    for game in set["data"]["games"]:
        game["players"] = [prepare_player(player) for player in game["players"]]

# Sets to array
result = {EVENT_OUT: [set for set in sets.values()]}

with open("2a_raw_builds.json", "w", encoding="utf8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
