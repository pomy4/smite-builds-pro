import sys
import time

import requests


def main() -> None:
    match_stats_url = (
        "https://esports.hirezstudios.com/esportsAPI/smite/matchstats/{}/{}"
    )
    match_i = int(sys.argv[1])
    start_event_i = sys.argv[2] if len(sys.argv) > 2 else 7250
    end_event_i = sys.argv[3] if len(sys.argv) > 3 else 9999
    for event_i in range(start_event_i, end_event_i + 1):
        url = match_stats_url.format(event_i, match_i)
        print(f"Trying {event_i}! ", end="")
        resp = requests.get(url)
        if resp.text == '{"error":"Match does not belong to this event."}':
            print("No dice")
        else:
            # Can also be {"error":"Match not found."}
            print(resp.text)
            return
        time.sleep(0.25)


if __name__ == "__main__":
    main()
