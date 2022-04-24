import sys
import pprint
import os
import logging

from selenium import webdriver

import updater

league = updater.spl
phase = 'just a phase'
month = 9
day = 9

if not ((len(sys.argv) > 1) and (input := sys.argv[1])) and not (input := os.environ.get('SYSARG')):
  print('Supply a match id please (e.g. 2455).')
  sys.exit(0)

match_id = int(input)
match_url = f'{league.matches_url}/{match_id}'
logging.basicConfig(filename='logs/tmp.log', level=logging.INFO, format='%(asctime)s|%(levelname)s|%(message)s')
builds = []
with webdriver.Chrome() as driver:
    driver.implicitly_wait(updater.implicit_wait)
    builds = updater.scrape_match(league.name, driver, phase, month, day, match_url, match_id)
    pprint.pprint(builds)
