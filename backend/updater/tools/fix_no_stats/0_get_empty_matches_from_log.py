import json
import sys


def main() -> None:
    with open(sys.argv[1], "r", encoding="utf8") as f:
        lines = f.read().splitlines()

    empty_matches = get_empty_matches(lines)

    with open("1_empty_matches.json", "w", encoding="utf8") as f:
        json.dump(empty_matches, f, indent=2, ensure_ascii=False)


def get_empty_matches(lines: list[str]) -> dict:
    empty_matches: dict = {}
    for i, line in enumerate(lines):
        line_split = line.split("|")
        if line_split[2] == "There are no stats for this match":
            prev_line_split = lines[i - 1].split("|")
            empty_match_all = json.loads(prev_line_split[3])
            empty_match_key = f'{empty_match_all["league"]}|{empty_match_all["phase"]}'
            empty_match_value = {
                "month": empty_match_all["month"],
                "day": empty_match_all["day"],
                "match_id": empty_match_all["match_id"],
            }
            empty_matches.setdefault(empty_match_key, []).append(empty_match_value)
    return empty_matches


if __name__ == "__main__":
    main()
