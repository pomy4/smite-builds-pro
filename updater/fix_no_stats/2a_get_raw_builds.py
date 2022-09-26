import json
import time

import requests


def main() -> None:
    match_stats_url = (
        "https://esports.hirezstudios.com/esportsAPI/smite/matchstats/{}/{}"
    )
    # Hardcoding good enough for now.
    fixed_event_ids = {
        "SPL|Pre-Season": None,  # 7261
        "SCC|EU Phase 1": 7285,  # 7284
        "SCC|EU Phase 2": 7292,  # 7284,
        "SCC|NA Phase 2": 7293,  # 7284
        "SPL|Summer Masters": 7270,  # 7261,
    }

    with open("1_empty_matches.json", "r", encoding="utf8") as f:
        empty_matches = json.load(f)

    to_remove = []
    for league_and_phase, matches in empty_matches.items():
        print(league_and_phase)
        if league_and_phase not in fixed_event_ids:
            raise RuntimeError(f"Unknown leageu and phase")
        event_id = fixed_event_ids[league_and_phase]
        if event_id is None:
            to_remove.append(league_and_phase)
            continue

        for match in matches:
            print(match["match_id"], end=" ")
            url = match_stats_url.format(event_id, match["match_id"])
            resp = requests.get(url)
            resp.raise_for_status()
            match["data"] = resp.json()
            if "error" in match["data"]:
                raise RuntimeError(str(match["data"]))
            print(f"OK")
            time.sleep(0.1)

    for league_and_phase in to_remove:
        del empty_matches[league_and_phase]

    with open("2a_raw_builds.json", "w", encoding="utf8") as f:
        json.dump(empty_matches, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
