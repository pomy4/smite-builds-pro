import datetime
import logging
import unittest

from backend.webapi.loggers import cache_logger
from backend.webapi.webapi import format_rfc, is_cached


class TestLastModified(unittest.TestCase):
    def test_is_cached(self) -> None:
        last_modified = datetime.datetime(2012, 12, 12, tzinfo=datetime.timezone.utc)

        same = format_rfc(last_modified)
        with self.assertNoLogs(cache_logger):
            self.assertTrue(is_cached(last_modified, same))

        before = format_rfc(last_modified.replace(day=11))
        with self.assertNoLogs(cache_logger):
            self.assertFalse(is_cached(last_modified, before))

        after = format_rfc(last_modified.replace(day=13))
        with self.assertLogs(cache_logger, logging.INFO):
            self.assertFalse(is_cached(last_modified, after))

        naive = format_rfc(last_modified).replace("GMT", "-0000")
        with self.assertLogs(cache_logger, logging.INFO):
            self.assertTrue(is_cached(last_modified, naive))

        not_rfc = last_modified.isoformat()
        with self.assertLogs(cache_logger, logging.INFO):
            self.assertFalse(is_cached(last_modified, not_rfc))


if __name__ == "__main__":
    unittest.main()
