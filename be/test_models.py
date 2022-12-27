import copy
import logging
import unittest.mock
from unittest.mock import Mock

import be.models
import shared
from be.models import MyError

be.models.auto_fixes_logger.setLevel(logging.ERROR)


class TestFixRoles(unittest.TestCase):
    BUILDS = [
        {
            "role": "ADC",
            "team1": "A",
            "god1": "A1",
            "player1": "A1",
            "god2": "B1",
            "player2": "B1",
        },
        {
            "role": "Jungle",
            "team1": "A",
            "god1": "A2",
            "player1": "A2",
            "god2": "B2",
            "player2": "B2",
        },
        {
            "role": "Mid",
            "team1": "A",
            "god1": "A3",
            "player1": "A3",
            "god2": "B3",
            "player2": "B3",
        },
        {
            "role": "Solo",
            "team1": "A",
            "god1": "A4",
            "player1": "A4",
            "god2": "B4",
            "player2": "B4",
        },
        {
            "role": "Support",
            "team1": "A",
            "god1": "A5",
            "player1": "A5",
            "god2": "B5",
            "player2": "B5",
        },
        {
            "role": "ADC",
            "team1": "B",
            "god1": "B1",
            "player1": "B1",
            "god2": "A1",
            "player2": "A1",
        },
        {
            "role": "Jungle",
            "team1": "B",
            "god1": "B2",
            "player1": "B2",
            "god2": "A2",
            "player2": "A2",
        },
        {
            "role": "Mid",
            "team1": "B",
            "god1": "B3",
            "player1": "B3",
            "god2": "A3",
            "player2": "A3",
        },
        {
            "role": "Solo",
            "team1": "B",
            "god1": "B4",
            "player1": "B4",
            "god2": "A4",
            "player2": "A4",
        },
        {
            "role": "Support",
            "team1": "B",
            "god1": "B5",
            "player1": "B5",
            "god2": "A5",
            "player2": "A5",
        },
    ]

    def test_happy(self) -> None:
        builds = copy.deepcopy(self.BUILDS)
        be.models.fix_roles_in_single_game(builds)
        self.assertEqual(builds, self.BUILDS)

    def test_illegal(self) -> None:
        # Three teams.
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["team1"] = "C"
        with self.assertRaises(MyError):
            be.models.fix_roles_in_single_game(builds)

        # One team.
        builds = copy.deepcopy(self.BUILDS)
        for build in builds:
            build["team1"] = "A"
        with self.assertRaises(MyError):
            be.models.fix_roles_in_single_game(builds)

        # Six player vs four players.
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["team1"] = "B"
        with self.assertRaises(MyError):
            be.models.fix_roles_in_single_game(builds)

    @unittest.mock.patch("be.models.get_player_count_with_team")
    def test_fixable_2a(self, mock: Mock) -> None:
        # Situation 2a.
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["role"] = "Coach"
        be.models.fix_roles_in_single_game(builds)
        self.assertEqual(builds, self.BUILDS)

        # Situation 2b.
        mock.side_effect = [0, 1]
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["role"] = "Mid"
        be.models.fix_roles_in_single_game(builds)
        self.assertEqual(builds, self.BUILDS)

        # 2a + 2b.
        mock.side_effect = [0, 1]
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["role"] = "Coach"
        builds[5]["role"] = "Mid"
        be.models.fix_roles_in_single_game(builds)
        self.assertEqual(builds, self.BUILDS)

    @unittest.mock.patch("be.models.get_player_count_with_team")
    def test_unfixable(self, mock: Mock) -> None:
        # Coach + Sub.
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["role"] = "Coach"
        builds[1]["role"] = "Sub"
        be.models.fix_roles_in_single_game(builds)
        self.assertNotEqual(builds, self.BUILDS)

        # Sub + Sub.
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["role"] = "Sub"
        builds[1]["role"] = "Sub"
        be.models.fix_roles_in_single_game(builds)
        self.assertNotEqual(builds, self.BUILDS)

        # Mid + Mid + Mid.
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["role"] = "Mid"
        builds[1]["role"] = "Mid"
        be.models.fix_roles_in_single_game(builds)
        self.assertNotEqual(builds, self.BUILDS)

        # Missing build.
        builds = copy.deepcopy(self.BUILDS)
        del builds[0]
        be.models.fix_roles_in_single_game(builds)
        self.assertNotEqual(builds, self.BUILDS)

        # Mid + Mid (same count).
        mock.side_effect = [1, 1]
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["role"] = "Mid"
        be.models.fix_roles_in_single_game(builds)
        self.assertNotEqual(builds, self.BUILDS)


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
        self.assertFalse(be.models.contains_digits(""))
        self.assertFalse(be.models.contains_digits("abc"))
        self.assertTrue(be.models.contains_digits("a2c"))
        self.assertTrue(be.models.contains_digits("123"))

    @unittest.mock.patch("be.models.get_newest_god")
    def test_happy(self, mock: Mock) -> None:
        mock.side_effect = RuntimeError("Shouldn't be called")
        builds = copy.deepcopy(self.BUILDS)
        be.models.fix_gods(builds)
        self.assertEqual(builds, self.BUILDS)

    @unittest.mock.patch("be.models.get_newest_god")
    def test_fixable(self, mock: Mock) -> None:
        mock.side_effect = ["god-one"]
        builds = copy.deepcopy(self.BUILDS)
        builds[0]["god1"] = "god1"
        builds[1]["god2"] = "god1"
        be.models.fix_gods(builds)
        self.assertEqual(builds, self.BUILDS)


class TestHirezApi(unittest.TestCase):
    """This should run last, as it is slow."""

    newest_god = None

    @classmethod
    def setUpClass(cls) -> None:
        shared.load_default_dot_env()
        if not be.models.are_hirez_api_credentials_set():
            raise unittest.SkipTest("Hi-Rez API credentials are not set")

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.newest_god:
            print(f"\n(newest god is {cls.newest_god})", end="")

    @classmethod
    def test_newest_god(cls) -> None:
        cls.newest_god = be.models.get_newest_god()


if __name__ == "__main__":
    unittest.main()
