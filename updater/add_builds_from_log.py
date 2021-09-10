import sys
import json

import requests

if len(sys.argv) < 2:
  print('Supply filepath of a log please.')
  sys.exit(0)

builds = []
with open(sys.argv[1], 'r', encoding='utf-8') as f:
  for line in f.readlines():
    line_split = line.split('|')
    if len(line_split) < 3 or line_split[1] != 'Build scraped':
      continue
    build_json = json.loads(line_split[2])
    builds.append(build_json)

backend_url = 'http://localhost:8080'
builds_resp = requests.post(f'{backend_url}/builds', json=builds)
builds_resp.raise_for_status()
