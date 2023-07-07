import logging

import pytest

from backend.log_manager.alert import logger, parse_lines

info = ["|INFO|1", "2"]
warning = ["|WARNING|1", "2"]

parse_lines_params = [
    (info, [], False),
    (warning, [warning], False),
    (
        ["0"] + info + warning + warning + info + warning,
        [warning, warning, warning],
        True,
    ),
]


@pytest.mark.parametrize("arg,result,logs", parse_lines_params)
def test_parse_lines(
    arg: list[str],
    result: list[list[str]],
    logs: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=logger.name)
    assert parse_lines(arg) == result
    assert bool(caplog.records) == logs
