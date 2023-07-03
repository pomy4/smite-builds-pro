import copy
import dataclasses
import typing as t
from unittest.mock import Mock, patch

import pytest

from backend.webapi.post_builds.fix_gods import contains_digits, fix_gods

contains_digits_params = [
    ("", False),
    ("abc", False),
    ("a2c", True),
    ("123", True),
]


@pytest.mark.parametrize("arg,result", contains_digits_params)
def test_contains_digits(arg: str, result: bool) -> None:
    assert contains_digits(arg) == result


builds_orig = [
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


@dataclasses.dataclass
class FixGodsParam:
    builds: list[dict]
    side_effect: list[str] | Exception


def copy_builds() -> list[dict]:
    return copy.deepcopy(builds_orig)


def fix_gods_params_gen() -> t.Iterator[FixGodsParam]:
    # Nothing wrong.
    builds = copy_builds()
    yield FixGodsParam(builds, RuntimeError("Shouldn't be called"))

    # Fixable.
    builds = copy_builds()
    builds[0]["god1"] = "god1"
    builds[1]["god2"] = "god1"
    yield FixGodsParam(builds, ["god-one"])


@pytest.mark.parametrize("p", fix_gods_params_gen())
@patch("backend.webapi.post_builds.fix_gods.get_newest_god")
def test_fix_gods(mock: Mock, p: FixGodsParam) -> None:
    mock.side_effect = p.side_effect
    fix_gods(p.builds)
    assert p.builds == builds_orig
