import sys
import json
import os

import updater

if not (input := sys.argv[1:2]) and not (input := os.environ.get('SYSARG')):
  print('Supply filepath of a log please.')
  sys.exit(0)

hmac_key_hex = updater.get_hmac_key_hex_from_env()

builds = []
with open(input, 'r', encoding='utf-8') as f:
  for line in f.readlines():
    line_split = line.split('|')
    if len(line_split) < 3 or line_split[1] != 'Build scraped':
      continue
    build_json = json.loads(line_split[2])
    builds.append(build_json)

updater.send_builds(hmac_key_hex, builds)
