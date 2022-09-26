import json

import requests


def main() -> None:
    url = "https://cms.smitegame.com/wp-json/smite-api/getItems/1"
    items = requests.get(url).json()
    with open("2b_items.json", "w", encoding="utf8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
