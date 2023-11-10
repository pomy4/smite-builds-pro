import collections
import typing as t

import sqlalchemy as sa

from backend.webapi.exceptions import MyValidationError
from backend.webapi.models import Build, db_session
from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger as logger
from backend.webapi.post_builds.auto_fixes_logger import log_curr_game

BuildDict = dict[str, t.Any]


def fix_roles(builds: list[BuildDict]) -> None:
    game_to_builds = collections.defaultdict(list)
    for build in builds:
        game_to_builds[(build["match_id"], build["game_i"])].append(build)

    for game_builds in game_to_builds.values():
        with log_curr_game(game_builds[0]):
            fix_roles_in_single_game(game_builds)


def fix_roles_in_single_game(builds: list[BuildDict]) -> None:
    team_to_builds = collections.defaultdict(list)
    for build in builds:
        team_to_builds[build["team1"]].append(build)

    teams = list(team_to_builds.keys())
    if len(teams) != 2:
        raise MyValidationError(f"Teams must be two: {len(teams), teams}")

    team1, team2 = teams
    team1_builds, team2_builds = team_to_builds[team1], team_to_builds[team2]

    team1_fixed_builds, role_to_team1_build = fix_roles_in_single_team(team1_builds)
    team2_fixed_builds, role_to_team2_build = fix_roles_in_single_team(team2_builds)

    # The wrongly specified role almost certainly caused the fields god2 and player2
    # filled in updater to also be wrong, so we have to also fix them.
    fix_opp_fields(team1_fixed_builds, role_to_team2_build)
    fix_opp_fields(team2_fixed_builds, role_to_team1_build)


ALLOWED_ROLES = {"ADC", "Jungle", "Mid", "Solo", "Support"}


def fix_roles_in_single_team(
    builds: list[BuildDict],
) -> tuple[list[BuildDict], dict[str, BuildDict]]:
    """
    There are two types of issues that can happen in the input data:
    1) Build is missing - not much we can do with that.
    2) Build has the wrong role specified. This happen when there is a sub player,
    and there are two possible sub-issues:
    2a) Quite often their role will be specified as Sub or Coach, instead of their
    actual role.
    2b) This happened only once, but there was a sub that previously played for a
    different team, and their displayed role reflected their role in their previous
    team and not what they actually played. Thus there can be e.g. 2x Mids and 0x Solo.
    """
    if len(builds) > 5:
        raise MyValidationError(f"Too many builds: {len(builds)}")

    correct_roles = []
    fixable_roles = []
    unfixable_roles = []

    MISSING_ROLE = "Missing data"
    for _ in range(5 - len(builds)):
        # Situation 1.
        unfixable_roles.append(MISSING_ROLE)

    role_to_builds = collections.defaultdict(list)
    for build in builds:
        role_to_builds[build["role"]].append(build)

    for role, role_builds in role_to_builds.items():
        if len(role_builds) > 2:
            unfixable_roles.append(role)
        elif len(role_builds) == 2:
            if role not in ALLOWED_ROLES:
                unfixable_roles.append(role)
            else:
                # Situation 2b.
                fixable_roles.append(role)
        else:
            if role not in ALLOWED_ROLES:
                # Situation 2a.
                fixable_roles.append(role)
            else:
                correct_roles.append(role)

    correct_role_to_build: dict[str, BuildDict] = {
        role: role_to_builds[role][0] for role in correct_roles
    }

    # We can only auto-fix when there is at most one (fixable) error.
    # If there is e.g. Coach instead of Solo and Sub instead of Mid, then we don't know
    # whether we should do Coach -> Solo and Sub -> Mid or Coach -> Mid and Sub -> Solo.
    if not (len(fixable_roles) == 1 and len(unfixable_roles) == 0):
        for role in fixable_roles + unfixable_roles:
            if role == MISSING_ROLE:
                logger.info("Missing build")
            else:
                role_builds = role_to_builds[role]
                logger.warning(f"Wrong role: {role} ({len(role_builds)})")
        return [], correct_role_to_build

    role_to_fix = fixable_roles[0]
    builds_to_fix = role_to_builds[role_to_fix]
    missing_roles = {role for role in ALLOWED_ROLES if role not in correct_roles}

    if role_to_fix not in ALLOWED_ROLES:
        # Situation 2a - easy.
        assert len(builds_to_fix) == 1
        assert len(missing_roles) == 1
        build_to_fix = builds_to_fix[0]
        missing_role = next(iter(missing_roles))
    else:
        # Situation 2b - more difficult, we have to decide which player is sub, and we
        # do that based on the number of games either player played with that team.
        assert len(builds_to_fix) == 2
        assert len(missing_roles) == 2
        assert role_to_fix in missing_roles
        missing_roles.remove(role_to_fix)
        missing_role = next(iter(missing_roles))
        build1, build2 = builds_to_fix
        count1 = get_player_count_with_team(build1)
        count2 = get_player_count_with_team(build2)
        if count1 < count2:
            build_to_fix = build1
        elif count1 > count2:
            build_to_fix = build2
        else:
            # If both played the same number, we stop here without auto-fixing.
            logger.warning(f"Wrong role: {role_to_fix} (2) [{count1}]")
            return [], correct_role_to_build

    logger.info(f"Role|{role_to_fix} -> {missing_role}")
    build_to_fix["role"] = missing_role
    correct_role_to_build[missing_role] = build_to_fix
    return [build_to_fix], correct_role_to_build


def get_player_count_with_team(build: BuildDict) -> int:
    result = db_session.scalars(
        sa.select(sa.func.count(Build.id)).where(
            sa.and_(Build.team1 == build["team1"], Build.player1 == build["player1"])
        )
    ).one()
    return result


def fix_opp_fields(
    fixed_builds: list[BuildDict], role_to_opp_build: dict[str, BuildDict]
) -> None:
    for build in fixed_builds:
        role = build["role"]
        if role not in role_to_opp_build:
            # We don't need to log here, since the dictionary contains only correct
            # roles, and if a role is not there, then its error was already logged in
            # the function tasked with fixing roles.
            continue
        opp_build = role_to_opp_build[role]

        logger.info(f"God2|{build['god2']} -> {opp_build['god1']}")
        build["god2"] = opp_build["god1"]
        logger.info(f"Player2|{build['player2']} -> {opp_build['player1']}")
        build["player2"] = opp_build["player1"]
