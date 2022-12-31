import datetime
from typing import Optional

from be.loggers import cache_logger
from be.models import Build, DbVersion, LastChecked, LastModified, Version


def update_version(new_data: DbVersion) -> None:
    # replace is an 'upsert'.
    Version.replace(id=1, data=new_data.value).execute()


def get_last_modified() -> Optional[datetime.datetime]:
    try:
        last_modified = LastModified.get().data

        if last_modified.tzinfo is not None:
            # This should never happen, but if it does, we log and return None
            # instead of throwing, so that user's request still finishes.
            cache_logger.warning(
                f"Last modified returned from db as aware: {repr(last_modified)}"
            )
            return None

        # Return Aware datetime in UTC.
        return last_modified.replace(tzinfo=datetime.timezone.utc)

    except LastModified.DoesNotExist:
        # This should also not happen,
        # since LastModified is inserted in create_db.
        cache_logger.warning("Last modified does not exist")
        return None


def update_last_modified(new_data: datetime.datetime) -> None:
    cache_logger.info(f"Last modified updated: {new_data.isoformat()}")
    # This function is only used with output from what_time_is_it(),
    # which returns aware datetime in UTC. Make sure this assumption holds:
    assert new_data.tzinfo == datetime.timezone.utc

    # Peewee + SQLite does not support aware datetimes.
    new_data_naive = new_data.replace(tzinfo=None)
    LastModified.replace(id=1, data=new_data_naive).execute()


def get_last_checked() -> Optional[str]:
    try:
        return LastChecked.get().data
    except LastChecked.DoesNotExist:
        return None


def update_last_checked(new_data: str) -> None:
    LastChecked.replace(id=1, data=new_data).execute()


def get_match_ids(phase: str) -> list[int]:
    return [
        b.match_id
        for b in Build.select(Build.match_id).where(Build.phase == phase).distinct()
    ]
