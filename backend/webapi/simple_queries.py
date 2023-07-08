import datetime
import logging

import sqlalchemy as sa

from backend.webapi.models import Build, DbVersion, Metadata, db_engine, db_session, lst

logger = logging.getLogger(__name__)


def get_match_ids(phase: str) -> list[int]:
    match_ids = db_session.scalars(
        sa.select(Build.match_id).where(Build.phase == phase).distinct()
    ).all()
    return lst(match_ids)


VERSION_KEY = "version"


def get_version() -> DbVersion:
    if sa.inspect(db_engine).has_table(Metadata.__tablename__):
        version_str = get_metadata(VERSION_KEY)
        # Version is always inserted in create_db.
        assert version_str is not None
        return DbVersion(version_str)
    elif sa.inspect(db_engine).has_table("version"):
        return DbVersion.ADD_VERSION_TABLE
    else:
        return DbVersion.OLD


def update_version(version: DbVersion) -> None:
    update_metadata(VERSION_KEY, version.value)


LAST_MODIFIED_KEY = "last_modified"


def get_last_modified() -> datetime.datetime | None:
    last_modified_str = get_metadata(LAST_MODIFIED_KEY)

    if last_modified_str is None:
        # This should never happen, since LastModified is always inserted in create_db.
        # But since this is called by endpoints for frontend, we log and return None
        # instead of throwing, so that user's request still finishes.
        logger.warning("Last modified does not exist")
        return None

    try:
        last_modified = datetime.datetime.fromisoformat(last_modified_str)
    except ValueError:
        # Same here.
        msg = f"Last modified is not an isoformat datetime: {last_modified_str}"
        logger.warning(msg)
        return None

    if last_modified.tzinfo is None:
        # Same here.
        logger.warning(f"Last modified is not aware: {last_modified_str}")
        return None

    return last_modified


def update_last_modified(last_modified: datetime.datetime) -> None:
    # This function is only used with output from what_time_is_it(),
    # which returns aware datetime in UTC.
    assert last_modified.tzinfo == datetime.timezone.utc
    last_modified_str = last_modified.isoformat()
    logger.info(f"New last modified: {last_modified_str}")
    update_metadata(LAST_MODIFIED_KEY, last_modified_str)


LAST_CHECKED_KEY = "last_checked"
LAST_CHECKED_TOOLTIP_KEY = "last_checked_tooltip"


def get_last_checked() -> tuple[str | None, str | None]:
    last_checked = get_metadata(LAST_CHECKED_KEY)
    last_checked_tooltip = get_metadata(LAST_CHECKED_TOOLTIP_KEY)
    return last_checked, last_checked_tooltip


def update_last_checked(last_checked: str, last_checked_tooltip: str) -> None:
    update_metadata(LAST_CHECKED_KEY, last_checked)
    update_metadata(LAST_CHECKED_TOOLTIP_KEY, last_checked_tooltip)


def get_metadata(key: str) -> str | None:
    metadata = db_session.scalars(
        sa.select(Metadata).where(Metadata.key == key)
    ).one_or_none()
    value = metadata.value if metadata is not None else None
    return value


def update_metadata(key: str, value: str) -> None:
    metadata = db_session.scalars(
        sa.select(Metadata).where(Metadata.key == key)
    ).one_or_none()
    if metadata is not None:
        metadata.value = value
    else:
        db_session.add(Metadata(key=key, value=value))
