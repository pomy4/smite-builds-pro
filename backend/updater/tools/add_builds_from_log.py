import json
import sys

import upd.updater
from config import load_updater_config


def main() -> None:
    if len(sys.argv) < 2:
        print("Missing log filepath argument", file=sys.stderr)
        sys.exit(1)

    load_updater_config()

    builds = []
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        for line in f.readlines():
            line_split = line.split("|")
            if len(line_split) < 4 or line_split[2] != "Build scraped":
                continue
            build_json = json.loads(line_split[3])
            builds.append(build_json)

    upd.updater.post_builds(builds, "FROM LOG")


if __name__ == "__main__":
    main()
