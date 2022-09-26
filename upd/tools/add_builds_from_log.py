import json
import sys

import shared
import upd.updater


def main() -> None:
    if len(sys.argv) < 2:
        print("Missing log filepath argument", file=sys.stderr)
        sys.exit(1)

    shared.load_default_dot_env()

    builds = []
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        for line in f.readlines():
            line_split = line.split("|")
            if len(line_split) < 4 or line_split[2] != "Build scraped":
                continue
            build_json = json.loads(line_split[3])
            builds.append(build_json)

    upd.updater.post_builds(builds)


if __name__ == "__main__":
    main()
