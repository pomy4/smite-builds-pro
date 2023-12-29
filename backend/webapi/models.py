from __future__ import annotations

import datetime
import enum
import typing as t

import sqlalchemy as sa
import sqlalchemy.orm as sao

from backend.shared import STORAGE_DIR


class DbVersion(enum.Enum):
    OLD = "0.old"
    ADD_VERSION_TABLE = "1.add_version_table"
    SWITCH_TO_SQLALCHEMY = "2.swich_to_sqlalchemy"
    ADD_GOD_CLASS = "3.add_god_class"
    ADD_IMAGE_TABLE = "4.add_image_table"
    CASCADE_DEL_BUILD_ITEMS = "5.cascade_del_build_items"

    def __init__(self, value: str) -> None:
        self.index = int(value.split(".", 1)[0])


CURRENT_DB_VERSION = list(DbVersion)[-1]

db_path = STORAGE_DIR / "backend.db"
db_engine = sa.create_engine(url=f"sqlite+pysqlite:///{db_path}")
session_maker = sao.sessionmaker(bind=db_engine)
# Thread-local session automatically created on first use.
# https://docs.sqlalchemy.org/en/20/orm/contextual.html#using-thread-local-scope-with-web-applications
db_session = sao.scoped_session(session_factory=session_maker)

STR_MAX_LEN = 50


class Base(sao.MappedAsDataclass, sao.DeclarativeBase):
    def asdict(self) -> dict[str, t.Any]:
        # https://stackoverflow.com/a/30280750
        d = {key: getattr(self, key) for key in self.__mapper__.c.keys()}
        return d


class Metadata(Base):
    __tablename__ = "metadata"

    key: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN), primary_key=True)
    value: sao.Mapped[str] = sao.mapped_column(sa.Text())


class BuildItem(Base):
    __tablename__ = "build_item"

    build_id: sao.Mapped[int] = sao.mapped_column(
        sa.ForeignKey("build.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: sao.Mapped[int] = sao.mapped_column(
        sa.ForeignKey("item.id"), primary_key=True
    )
    item: sao.Mapped[Item] = sao.relationship(lazy="raise", init=False)
    index: sao.Mapped[int] = sao.mapped_column(sa.SmallInteger())


class Image(Base):
    __tablename__ = "image"

    id: sao.Mapped[int] = sao.mapped_column(primary_key=True, init=False)
    # Uniqueness is enforced on the application side, to save on database size.
    data: sao.Mapped[bytes] = sao.mapped_column(sa.LargeBinary)


class Item(Base):
    __tablename__ = "item"

    id: sao.Mapped[int] = sao.mapped_column(primary_key=True, init=False)
    is_relic: sao.Mapped[bool]
    name: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    name_was_modified: sao.Mapped[int] = sao.mapped_column(sa.SmallInteger())
    image_name: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    image_id: sao.Mapped[int | None] = sao.mapped_column(sa.ForeignKey("image.id"))
    image: sao.Mapped[Image | None] = sao.relationship(lazy="raise", init=False)


class Build(Base):
    __tablename__ = "build"

    id: sao.Mapped[int] = sao.mapped_column(primary_key=True, init=False)
    season: sao.Mapped[int] = sao.mapped_column(sa.SmallInteger())
    league: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    phase: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    date: sao.Mapped[datetime.date]
    match_id: sao.Mapped[int]
    game_i: sao.Mapped[int] = sao.mapped_column(sa.SmallInteger())
    win: sao.Mapped[bool]
    game_length: sao.Mapped[datetime.time]

    kda_ratio: sao.Mapped[float]
    kills: sao.Mapped[int] = sao.mapped_column(sa.SmallInteger())
    deaths: sao.Mapped[int] = sao.mapped_column(sa.SmallInteger())
    assists: sao.Mapped[int] = sao.mapped_column(sa.SmallInteger())
    role: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    god_class: sao.Mapped[str] = sao.mapped_column(
        sa.String(STR_MAX_LEN), nullable=True
    )
    god1: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    player1: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    team1: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    god2: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    player2: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))
    team2: sao.Mapped[str] = sao.mapped_column(sa.String(STR_MAX_LEN))

    # When a build is deleted, related build_items are also deleted.
    # https://docs.sqlalchemy.org/en/20/orm/cascades.html#using-foreign-key-on-delete-cascade-with-orm-relationships
    # Also https://stackoverflow.com/a/38770040
    build_items: sao.Mapped[list[BuildItem]] = sao.relationship(
        lazy="raise", init=False, cascade="all", passive_deletes=True
    )


indices = [
    sa.Index("ix_build_item_build_id", BuildItem.build_id),
    sa.Index("ix_build_item_item_id", BuildItem.item_id),
    sa.Index("ix_item_image_id", Item.image_id),
    sa.Index(
        "ix_item_unique",
        Item.is_relic,
        Item.name,
        Item.name_was_modified,
        Item.image_name,
        Item.image_id,
        unique=True,
    ),
    sa.Index("ix_build_role", Build.role),
    sa.Index("ix_build_god_class", Build.god_class),
    sa.Index("ix_build_god1", Build.god1),
    sa.Index(
        "ix_build_unique",
        Build.match_id,
        Build.game_i,
        Build.player1,
        unique=True,
    ),
]


def reorder_indices() -> None:
    """
    SQLAlchemy seems to create the indices in a random order, so this makes sure that
    the order of the indices in the schema follows the definition.
    """
    for ix in indices:
        ix.drop(db_engine)
        ix.create(db_engine)


@sa.event.listens_for(sa.Engine, "connect")
def do_connect(dbapi_connection: t.Any, _: t.Any) -> t.Any:
    # Transactional DDL
    # https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl
    dbapi_connection.isolation_level = None

    # This should make SQLite check foreign keys.
    # https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@sa.event.listens_for(sa.Engine, "begin")
def do_begin(connection: sa.Connection) -> None:
    # Also Transactional DDL
    connection.exec_driver_sql("BEGIN")


T = t.TypeVar("T")


def lst(seq: t.Sequence[T]) -> list[T]:
    assert isinstance(seq, list)
    return seq
