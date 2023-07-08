import typing as t

import sqlalchemy as sa

from backend.webapi.models import Base


def dump(sql: t.Any, *_: t.Any, **__: t.Any) -> None:
    print(sql.compile(dialect=engine.dialect))


engine = sa.create_mock_engine(url="sqlite+pysqlite://", executor=dump)
Base.metadata.create_all(engine, checkfirst=False)
