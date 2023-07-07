import copy
import dataclasses
import typing as t
from unittest.mock import Mock, patch

import pytest

from backend.webapi.exceptions import MyValidationError
from backend.webapi.post_builds.fix_roles import fix_roles_in_single_game

builds_orig = [
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


def copy_builds() -> list[dict]:
    return copy.deepcopy(builds_orig)


@dataclasses.dataclass
class FixRolesParams:
    builds: list[dict]
    val_error: bool = False
    success: bool = True
    mock: list[int] | None = None


def fix_roles_params_gen() -> t.Iterator[FixRolesParams]:
    # Nothing wrong.
    builds = copy_builds()
    yield FixRolesParams(builds)

    # Three teams.
    builds = copy_builds()
    builds[0]["team1"] = "C"
    yield FixRolesParams(builds, val_error=True)

    # One team.
    builds = copy_builds()
    for build in builds:
        build["team1"] = "A"
    yield FixRolesParams(builds, val_error=True)

    # Six player vs four players.
    builds = copy_builds()
    builds[0]["team1"] = "B"
    yield FixRolesParams(builds, val_error=True)

    # Situation 2a.
    builds = copy_builds()
    builds[0]["role"] = "Coach"
    yield FixRolesParams(builds)

    # Situation 2b.
    builds = copy_builds()
    builds[0]["role"] = "Mid"
    yield FixRolesParams(builds, mock=[0, 1])

    # 2a + 2b.
    builds = copy_builds()
    builds[0]["role"] = "Coach"
    builds[5]["role"] = "Mid"
    yield FixRolesParams(builds, mock=[0, 1])

    # Coach + Sub.
    builds = copy_builds()
    builds[0]["role"] = "Coach"
    builds[1]["role"] = "Sub"
    yield FixRolesParams(builds, success=False)

    # Sub + Sub.
    builds = copy_builds()
    builds[0]["role"] = "Sub"
    builds[1]["role"] = "Sub"
    yield FixRolesParams(builds, success=False)

    # Mid + Mid + Mid.
    builds = copy_builds()
    builds[0]["role"] = "Mid"
    builds[1]["role"] = "Mid"
    yield FixRolesParams(builds, success=False)

    # Missing build.
    builds = copy_builds()
    del builds[0]
    yield FixRolesParams(builds, success=False)

    # Mid + Mid (same count).
    builds = copy_builds()
    builds[0]["role"] = "Mid"
    yield FixRolesParams(builds, success=False, mock=[1, 1])


@pytest.mark.parametrize("p", fix_roles_params_gen())
@patch("backend.webapi.post_builds.fix_roles.get_player_count_with_team")
def test_fix_roles(mock: Mock, p: FixRolesParams) -> None:
    if p.mock is not None:
        mock.side_effect = p.mock
    if p.val_error:
        with pytest.raises(MyValidationError):
            fix_roles_in_single_game(p.builds)
    else:
        fix_roles_in_single_game(p.builds)
        assert (p.builds == builds_orig) == p.success
