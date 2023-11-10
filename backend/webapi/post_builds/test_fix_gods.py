import copy
import dataclasses
import typing as t

import pytest

from backend.webapi.post_builds.fix_gods import BuildDict, contains_digits, fix_gods

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
    builds: list[BuildDict]
    newest_god: str | None


def copy_builds() -> list[BuildDict]:
    return copy.deepcopy(builds_orig)


def fix_gods_params_gen() -> t.Iterator[FixGodsParam]:
    # Nothing wrong.
    builds = copy_builds()
    yield FixGodsParam(builds, "god-three")

    # Fixable.
    builds = copy_builds()
    builds[0]["god1"] = "god1"
    builds[1]["god2"] = "god1"
    yield FixGodsParam(builds, "god-one")


@pytest.mark.parametrize("p", fix_gods_params_gen())
def test_fix_gods(p: FixGodsParam) -> None:
    fix_gods(p.builds, p.newest_god)
    assert p.builds == builds_orig
