import logging
import pprint
import sys

from backend.shared import LOG_FORMAT, SCC, SPL
from backend.updater.updater import IMPLICIT_WAIT, Match, WebDriver, scrape_match


def main() -> None:
    # If needed, phase/month/day could be supplied on the command line,
    # probably using the argparse module. Alternatively, they could be read
    # from the database, if the match was already scraped in the past.
    if len(sys.argv) < 2:
        print("Missing match ID argument", file=sys.stderr)
        sys.exit(1)
    match_id = int(sys.argv[1])

    if match_id >= 0:
        league = SPL
    else:
        league = SCC
        match_id *= -1

    logging.basicConfig(
        filename=f"{match_id}.log",
        level=logging.INFO,
        format=LOG_FORMAT,
    )

    with WebDriver() as driver:
        driver.implicitly_wait(IMPLICIT_WAIT)
        match = Match(
            league=league,
            phase="a phase",
            month=9,
            day=9,
            id=match_id,
            url=f"{league.match_url}/{match_id}",
            last_slash_i=len(league.match_url),
        )
        builds = scrape_match(driver, match)
        pprint.pprint(builds)


if __name__ == "__main__":
    main()
