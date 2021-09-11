import sys
import pprint
import os

from selenium import webdriver

import updater

phase = 'just a phase'
month = 9
day = 9
if not (match_id := sys.argv[1:2]) and not (match_id := os.environ.get('SYSARG')):
    match_id = 2455
match_url = f'{updater.spl_matches_url}/{match_id}'
builds = []
with webdriver.Firefox() as driver:
    driver.implicitly_wait(updater.implicit_wait)
    builds = updater.scrape_match(driver, phase, month, day, match_url, match_id)
    pprint.pprint(builds)
