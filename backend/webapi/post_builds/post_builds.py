from __future__ import annotations

import typing as t

from backend.webapi.post_builds.auto_fixes_logger import auto_fixes_logger as logger
from backend.webapi.post_builds.create_builds import create_builds
from backend.webapi.post_builds.create_items import (
    create_build_items,
    create_item_keys,
    create_item_wips,
    get_or_create_items,
)
from backend.webapi.post_builds.hirez_api import get_god_info

if t.TYPE_CHECKING:
    from backend.webapi.webapi import PostBuildRequest


def post_builds(builds: list[PostBuildRequest]) -> None:
    """Logging wrapper."""
    try:
        logger.info("Start")
        post_builds_inner(builds)
    except Exception:
        logger.info("End (FAIL)")
        raise
    else:
        logger.info("End")


def post_builds_inner(build_models: list["PostBuildRequest"]) -> None:
    god_info = get_god_info()
    build_dicts = [build_model.dict() for build_model in build_models]
    item_keys, build_item_wips = create_item_keys(build_dicts)
    item_wips = create_item_wips(item_keys)
    items = get_or_create_items(item_wips)
    builds = create_builds(god_info, build_dicts)
    create_build_items(builds, items, build_item_wips)
