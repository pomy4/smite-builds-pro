import copy
import unittest
from unittest.mock import Mock, patch

from backend.config import ConfigError, load_webapi_config
from backend.webapi.post_builds.fix_gods import (
    contains_digits,
    fix_gods,
    get_newest_god,
)


class TestFixGods(unittest.TestCase):
    BUILDS = [
        {
            "god1": "god-one",
            "god2": "god-two",
        },
        {
            "god1": "god-two",
            "god2": "god-one",
        },
        {
            "god1": "god-three",
            "god2": "god-four",
        },
    ]

    def test_contains_digits(self) -> None:
        self.assertFalse(contains_digits(""))
        self.assertFalse(contains_digits("abc"))
        self.assertTrue(contains_digits("a2c"))
        self.assertTrue(contains_digits("123"))

    @patch("backend.webapi.post_builds.fix_gods.get_newest_god")
    def test_happy(self, mock: Mock) -> None:
        mock.side_effect = RuntimeError("Shouldn't be called")
        builds = copy.deepcopy(self.BUILDS)
        fix_gods(builds)
        self.assertEqual(builds, self.BUILDS)

    @patch("backend.webapi.post_builds.fix_gods.get_newest_god")
    def test_fixable(self, mock: Mock) -> None:
        mock.side_effect = ["god-one"]
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["god1"] = "god1"
        builds[1]["god2"] = "god1"
        fix_gods(builds)
        self.assertEqual(builds, self.BUILDS)


class TestHirezApi(unittest.TestCase):
    """This should run last, as it is slow."""

    newest_god = None

    @classmethod
    def setUpClass(cls) -> None:
        try:
            load_webapi_config()
        except ConfigError as e:
            if "SMITE" in str(e):
                raise unittest.SkipTest("Hi-Rez API credentials are not set")
            else:
                raise

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.newest_god:
            print(f"\n(newest god is {cls.newest_god})", end="")

    @classmethod
    def test_newest_god(cls) -> None:
        cls.newest_god = get_newest_god()


if __name__ == "__main__":
    unittest.main()
