import datetime
import logging

import pytest

from backend.webapi.loggers import cache_logger
from backend.webapi.webapi import format_rfc, is_cached

last_modified = datetime.datetime(2012, 12, 12, tzinfo=datetime.timezone.utc)

is_cached_params = [
    (format_rfc(last_modified), True, False),  # same
    (format_rfc(last_modified.replace(day=11)), False, False),  # before
    (format_rfc(last_modified.replace(day=13)), False, True),  # after
    (format_rfc(last_modified).replace("GMT", "-0000"), True, True),  # naive
    (last_modified.isoformat(), False, True),  # not rfc
]


@pytest.mark.parametrize("arg,result,logs", is_cached_params)
def test_is_cached(
    arg: str, result: bool, logs: bool, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=cache_logger.name)
    assert is_cached(last_modified, arg) == result
    assert bool(caplog.records) == logs
