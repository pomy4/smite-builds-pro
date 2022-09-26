import json
import os
import sys

import updater

if not ((len(sys.argv) > 1) and (input := sys.argv[1])) and not (
    input := os.environ.get("SYSARG")
):
    print("Supply filepath of a log please.")
    sys.exit(0)

config = updater.config_from_env()

builds = []
with open(input, "r", encoding="utf-8") as f:
    for line in f.readlines():
        line_split = line.split("|")
        if len(line_split) < 4 or line_split[2] != "Build scraped":
            continue
        build_json = json.loads(line_split[3])
        builds.append(build_json)

updater.send_builds(config, builds)