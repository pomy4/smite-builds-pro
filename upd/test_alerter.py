import logging
import unittest

import upd.alerter


class TestAlerter(unittest.TestCase):
    def test_parse_lines(self) -> None:
        info = ["|INFO|1", "2"]
        self.assertEqual(upd.alerter.parse_lines(info), [])

        warning = ["|WARNING|1", "2"]
        self.assertEqual(upd.alerter.parse_lines(warning), [warning])

        inp = ["0"] + info + warning + warning + info + warning
        out = [warning, warning, warning]
        with self.assertLogs(upd.alerter.logger, logging.WARNING):
            self.assertEqual(upd.alerter.parse_lines(inp), out)


if __name__ == "__main__":
    unittest.main()
