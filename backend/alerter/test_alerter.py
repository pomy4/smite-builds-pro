import logging
import unittest

from backend.alerter.alerter import logger, parse_lines


class TestAlerter(unittest.TestCase):
    def test_parse_lines(self) -> None:
        info = ["|INFO|1", "2"]
        self.assertEqual(parse_lines(info), [])

        warning = ["|WARNING|1", "2"]
        self.assertEqual(parse_lines(warning), [warning])

        inp = ["0"] + info + warning + warning + info + warning
        out = [warning, warning, warning]
        with self.assertLogs(logger, logging.WARNING):
            self.assertEqual(parse_lines(inp), out)


if __name__ == "__main__":
    unittest.main()
