import json
import math


# TODO: move to updater.
def parse_game_length(game_length: str) -> tuple[int, int, int]:
    game_length = game_length.split(":")
    if len(game_length) == 2:
        minutes, seconds = game_length
        minutes, seconds = int(minutes), int(seconds)
        if minutes < 60:
            hours = 0
        else:
            hours = math.floor(minutes / 60)
            minutes = minutes % 60
    elif len(game_length) == 3:
        hours, minutes, seconds = game_length
        hours, minutes, seconds = int(hours), int(minutes), int(seconds)
    else:
        raise RuntimeError(f"Could not parse game length: {game_length}")
    return hours, minutes, seconds


def do_items(name_to_img_url: dict, old_items: list[str]) -> list[tuple[str, str]]:
    new_items = []
    for name in old_items:
        if name == "null":
            continue
        elif name in name_to_img_url:
            img_url = name_to_img_url[name]
        # Removed items.
        elif name == "Jotunn's Ferocity":
            img_url = "jotunns-ferocity.jpg"
        elif name == "Nimble Rod of Tahuti":
            img_url = "nimble-rod-of-tahuti.jpg"
        else:
            raise RuntimeError(f"Unknown item: {name}")
        new_items.append((name, img_url))
    return new_items


def main() -> None:
    with open("2b_items.json", "r", encoding="utf8") as f:
        all_items = json.load(f)
    cdn_images_url = "https://webcdn.hirezstudios.com/smite/item-icons"
    name_to_img_url = {}
    for item in all_items:
        img_url = item["itemIcon_URL"]
        last = img_url.rfind("/")
        if (base_url := img_url[:last]) != cdn_images_url:
            raise RuntimeError(f"Unknown URL for the CDN with images: {base_url}")
        name_to_img_url[item["DeviceName"]] = img_url[last + 1 :]

    with open("2a_raw_builds.json", "r", encoding="utf8") as f:
        raw_builds = json.load(f)

    builds = []
    for league_and_phase, matches in raw_builds.items():
        league, phase = league_and_phase.split("|")
        for match in matches:
            month = match["month"]
            day = match["day"]
            match_id = match["match_id"]
            for game_i, game in enumerate(match["data"]["games"], 1):
                hours, minutes, seconds = parse_game_length(game["game_duration"])
                team1 = game["team_totals"][0]["team"]
                team2 = game["team_totals"][1]["team"]
                if game["winning_team"] == 0:
                    winner = team1
                elif game["winning_team"] == 1:
                    winner = team2
                else:
                    raise RuntimeError(f"Unknown winning_team: {game['winning_team']}")
                other_teams = {team1: team2, team2: team1}
                teams = {team1: {}, team2: {}}
                for player in game["players"]:
                    teams[player["team"]][player["role"]] = (
                        player["name"],
                        player["god"],
                    )
                for player in game["players"]:
                    team, role = player["team"], player["role"]
                    other_team = other_teams[team]
                    if role == "Hunter":
                        role = "ADC"
                    if role in teams[other_team]:
                        player2, god2 = teams[other_team][role]
                    else:
                        player2, god2 = "Missing data", "Missing data"
                    kills, deaths, assists = (
                        player["kills"],
                        player["deaths"],
                        player["assists"],
                    )
                    relics = do_items(name_to_img_url, player["relics"])
                    items = do_items(name_to_img_url, player["build"])
                    builds.append(
                        {
                            "league": league,
                            "phase": phase,
                            "month": month,
                            "day": day,
                            "game_i": game_i,
                            "match_id": match_id,
                            "win": team == winner,
                            "hours": hours,
                            "minutes": minutes,
                            "seconds": seconds,
                            "kda_ratio": (kills + assists)
                            / (deaths if deaths > 0 else 1),
                            "kills": kills,
                            "deaths": deaths,
                            "assists": assists,
                            "role": role,
                            "team1": team,
                            "team2": other_team,
                            "relics": relics,
                            "items": items,
                            "player1": player["name"],
                            "god1": player["god"],
                            "player2": player2,
                            "god2": god2,
                        }
                    )

    with open("3_builds.json", "w", encoding="utf8") as f:
        json.dump(builds, f, indent=2, ensure_ascii=False)
    builds_log = [
        f"|INFO|Build scraped|{json.dumps(build, ensure_ascii=False)}"
        for build in builds
    ]
    with open("3_builds.log", "w", encoding="utf8") as f:
        f.write("\n".join(builds_log))


if __name__ == "__main__":
    main()
