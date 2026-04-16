from __future__ import annotations

import argparse
import base64
import contextlib
import datetime
import json
import sqlite3
import typing as t
from pathlib import Path

from backend.config import get_project_root_dir
from backend.shared import STORAGE_DIR

REQUEST_CHUNK_SIZE = 1024
ARCHIVE_DIR = get_project_root_dir() / "frontend" / "public" / "archive"
ARCHIVE_DB_NAME = "builds.sqlite3"
OPTIONS_JSON_NAME = "options.json"
LAST_CHECK_JSON_NAME = "last-check.json"
BUILD_FILTER_COLUMNS = [
    "season",
    "league",
    "phase",
    "date",
    "game_i",
    "win",
    "game_length",
    "kda_ratio",
    "kills",
    "deaths",
    "assists",
    "role",
    "god_class",
    "team1",
    "player1",
    "god1",
    "team2",
    "player2",
    "god2",
]


def main() -> None:
    args = parse_args()
    export_archive(source_path=args.source, archive_dir=args.output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export static archive assets for the frontend."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=STORAGE_DIR / "backend.db",
        help="Path to the source SQLite database.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ARCHIVE_DIR,
        help="Directory where the archive assets will be written.",
    )
    return parser.parse_args()


def export_archive(source_path: Path, archive_dir: Path) -> None:
    if not source_path.is_file():
        raise FileNotFoundError(f"Source database does not exist: {source_path}")

    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_db_path = archive_dir / ARCHIVE_DB_NAME
    temp_archive_db_path = archive_db_path.with_suffix(".sqlite3.tmp")

    if temp_archive_db_path.exists():
        temp_archive_db_path.unlink()

    with contextlib.closing(open_source_db(source_path)) as source_connection:
        options = get_options(source_connection)
        last_check = get_last_check(source_connection)
        write_archive_db(source_connection, temp_archive_db_path)

    temp_archive_db_path.replace(archive_db_path)
    write_json_file(archive_dir / OPTIONS_JSON_NAME, options)
    write_json_file(archive_dir / LAST_CHECK_JSON_NAME, last_check)


def open_source_db(source_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def write_archive_db(
    source_connection: sqlite3.Connection, archive_db_path: Path
) -> None:
    with contextlib.closing(sqlite3.connect(archive_db_path)) as archive_connection:
        archive_connection.execute("PRAGMA journal_mode = DELETE")
        archive_connection.execute(f"PRAGMA page_size = {REQUEST_CHUNK_SIZE}")
        archive_connection.execute("PRAGMA synchronous = OFF")
        create_archive_schema(archive_connection)
        copy_builds(source_connection, archive_connection)
        copy_images(source_connection, archive_connection)
        copy_build_items(source_connection, archive_connection)
        create_archive_indices(archive_connection)
        archive_connection.commit()
        archive_connection.execute("VACUUM")
        archive_connection.execute("ANALYZE")
        archive_connection.commit()


def create_archive_schema(archive_connection: sqlite3.Connection) -> None:
    archive_connection.executescript(
        """
        CREATE TABLE build (
            id INTEGER PRIMARY KEY,
            season INTEGER NOT NULL,
            league TEXT NOT NULL,
            phase TEXT NOT NULL,
            date TEXT NOT NULL,
            match_id INTEGER NOT NULL,
            match_url TEXT NOT NULL,
            game_i INTEGER NOT NULL,
            win INTEGER NOT NULL,
            game_length TEXT NOT NULL,
            kda_ratio REAL NOT NULL,
            kills INTEGER NOT NULL,
            deaths INTEGER NOT NULL,
            assists INTEGER NOT NULL,
            role TEXT NOT NULL,
            god_class TEXT,
            god1 TEXT NOT NULL,
            player1 TEXT NOT NULL,
            team1 TEXT NOT NULL,
            god2 TEXT NOT NULL,
            player2 TEXT NOT NULL,
            team2 TEXT NOT NULL
        );

        CREATE TABLE image (
            id INTEGER PRIMARY KEY,
            mime_type TEXT NOT NULL,
            data TEXT NOT NULL
        );

        CREATE TABLE build_item (
            build_id INTEGER NOT NULL,
            is_relic INTEGER NOT NULL,
            slot_index INTEGER NOT NULL,
            search_name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            image_id INTEGER,
            PRIMARY KEY (build_id, is_relic, slot_index)
        ) WITHOUT ROWID;
        """
    )


def copy_builds(
    source_connection: sqlite3.Connection, archive_connection: sqlite3.Connection
) -> None:
    build_rows = source_connection.execute(
        """
        SELECT
            id,
            season,
            league,
            phase,
            date,
            match_id,
            game_i,
            win,
            game_length,
            kda_ratio,
            kills,
            deaths,
            assists,
            role,
            god_class,
            god1,
            player1,
            team1,
            god2,
            player2,
            team2
        FROM build
        """
    )
    archive_connection.executemany(
        """
        INSERT INTO build (
            id,
            season,
            league,
            phase,
            date,
            match_id,
            match_url,
            game_i,
            win,
            game_length,
            kda_ratio,
            kills,
            deaths,
            assists,
            role,
            god_class,
            god1,
            player1,
            team1,
            god2,
            player2,
            team2
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                row["id"],
                row["season"],
                row["league"],
                row["phase"],
                row["date"],
                row["match_id"],
                get_match_url(row["league"], row["match_id"]),
                row["game_i"],
                row["win"],
                row["game_length"],
                row["kda_ratio"],
                row["kills"],
                row["deaths"],
                row["assists"],
                row["role"],
                row["god_class"],
                row["god1"],
                row["player1"],
                row["team1"],
                row["god2"],
                row["player2"],
                row["team2"],
            )
            for row in build_rows
        ),
    )


def copy_images(
    source_connection: sqlite3.Connection, archive_connection: sqlite3.Connection
) -> None:
    image_rows = source_connection.execute("SELECT id, data FROM image ORDER BY id")
    archive_connection.executemany(
        "INSERT INTO image (id, mime_type, data) VALUES (?, ?, ?)",
        (
            (
                row["id"],
                *normalize_image_data(t.cast(bytes, row["data"])),
            )
            for row in image_rows
        ),
    )


def copy_build_items(
    source_connection: sqlite3.Connection, archive_connection: sqlite3.Connection
) -> None:
    build_item_rows = source_connection.execute(
        """
        SELECT
            build_id,
            item.is_relic,
            build_item."index" AS slot_index,
            item.name AS search_name,
            item.name_was_modified,
            item.image_id
        FROM build_item
        JOIN item ON item.id = build_item.item_id
        ORDER BY build_id, item.is_relic DESC, slot_index
        """
    )
    archive_connection.executemany(
        """
        INSERT INTO build_item (
            build_id,
            is_relic,
            slot_index,
            search_name,
            display_name,
            image_id
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            (
                row["build_id"],
                row["is_relic"],
                row["slot_index"],
                row["search_name"],
                get_display_name(row["search_name"], row["name_was_modified"]),
                row["image_id"],
            )
            for row in build_item_rows
        ),
    )


def create_archive_indices(archive_connection: sqlite3.Connection) -> None:
    archive_connection.execute(
        """
        CREATE INDEX ix_build_order ON build (
            date DESC,
            match_id DESC,
            game_i DESC,
            win DESC,
            role ASC,
            id DESC
        )
        """
    )
    archive_connection.execute(
        """
        CREATE INDEX ix_build_basic_view ON build (
            god1,
            role,
            date DESC,
            match_id DESC,
            game_i DESC,
            win DESC,
            id DESC
        )
        """
    )
    archive_connection.execute(
        """
        CREATE INDEX ix_build_basic_view_with_class ON build (
            god1,
            role,
            god_class,
            date DESC,
            match_id DESC,
            game_i DESC,
            win DESC,
            id DESC
        )
        """
    )
    for column in BUILD_FILTER_COLUMNS:
        archive_connection.execute(
            f"CREATE INDEX ix_build_{column} ON build ({column})"
        )
    archive_connection.execute(
        """
        CREATE INDEX ix_build_item_filter
        ON build_item (is_relic, search_name, build_id)
        """
    )
    archive_connection.execute(
        """
        CREATE INDEX ix_build_item_build
        ON build_item (build_id, is_relic DESC, slot_index ASC)
        """
    )


def get_options(source_connection: sqlite3.Connection) -> dict[str, t.Any]:
    return {
        "season": select_distinct_values(
            source_connection,
            "SELECT DISTINCT season FROM build ORDER BY season ASC",
        ),
        "league": select_distinct_values(
            source_connection,
            "SELECT DISTINCT league FROM build ORDER BY league ASC",
        ),
        "phase": select_distinct_values(
            source_connection,
            "SELECT DISTINCT phase FROM build ORDER BY phase ASC",
        ),
        "date": get_min_max_text(
            source_connection,
            "SELECT MIN(date), MAX(date) FROM build",
            default="2012-05-31",
        ),
        "game_i": select_distinct_values(
            source_connection,
            "SELECT DISTINCT game_i FROM build ORDER BY game_i ASC",
        ),
        "win": [
            bool(value)
            for value in select_distinct_values(
                source_connection,
                "SELECT DISTINCT win FROM build ORDER BY win DESC",
            )
        ],
        "game_length": get_min_max_text(
            source_connection,
            "SELECT MIN(game_length), MAX(game_length) FROM build",
            default=datetime.time().isoformat(),
        ),
        "kda_ratio": get_min_max_number(
            source_connection, "SELECT MIN(kda_ratio), MAX(kda_ratio) FROM build"
        ),
        "kills": get_min_max_number(
            source_connection, "SELECT MIN(kills), MAX(kills) FROM build"
        ),
        "deaths": get_min_max_number(
            source_connection, "SELECT MIN(deaths), MAX(deaths) FROM build"
        ),
        "assists": get_min_max_number(
            source_connection, "SELECT MIN(assists), MAX(assists) FROM build"
        ),
        "role": select_distinct_values(
            source_connection,
            "SELECT DISTINCT role FROM build ORDER BY role ASC",
        ),
        "god_class": select_distinct_values(
            source_connection,
            "SELECT DISTINCT god_class FROM build ORDER BY god_class ASC",
        ),
        "team1": select_distinct_values(
            source_connection,
            "SELECT DISTINCT team1 FROM build ORDER BY team1 ASC",
        ),
        "player1": select_distinct_values(
            source_connection,
            "SELECT DISTINCT player1 FROM build ORDER BY UPPER(player1) ASC",
        ),
        "god1": select_distinct_values(
            source_connection,
            "SELECT DISTINCT god1 FROM build ORDER BY god1 ASC",
        ),
        "team2": select_distinct_values(
            source_connection,
            "SELECT DISTINCT team2 FROM build ORDER BY team2 ASC",
        ),
        "player2": select_distinct_values(
            source_connection,
            "SELECT DISTINCT player2 FROM build ORDER BY UPPER(player2) ASC",
        ),
        "god2": select_distinct_values(
            source_connection,
            "SELECT DISTINCT god2 FROM build ORDER BY god2 ASC",
        ),
        "relic": select_distinct_values(
            source_connection,
            """
            SELECT DISTINCT name
            FROM item
            WHERE is_relic = 1
            ORDER BY name ASC
            """,
        ),
        "item": select_distinct_values(
            source_connection,
            """
            SELECT DISTINCT name
            FROM item
            WHERE is_relic = 0
            ORDER BY name ASC
            """,
        ),
    }


def select_distinct_values(
    source_connection: sqlite3.Connection, query: str
) -> list[t.Any]:
    return [row[0] for row in source_connection.execute(query)]


def get_min_max_text(
    source_connection: sqlite3.Connection, query: str, default: str
) -> list[str]:
    min_value, max_value = source_connection.execute(query).fetchone()
    return [min_value or default, max_value or default]


def get_min_max_number(
    source_connection: sqlite3.Connection, query: str
) -> list[int | float]:
    min_value, max_value = source_connection.execute(query).fetchone()
    return [min_value or 0, max_value or 0]


def get_last_check(source_connection: sqlite3.Connection) -> dict[str, str]:
    metadata = {
        row["key"]: row["value"]
        for row in source_connection.execute("SELECT key, value FROM metadata")
    }
    return {
        "value": metadata.get("last_checked", "unknown"),
        "tooltip": metadata.get("last_checked_tooltip", "Unknown"),
    }


def get_match_url(league_name: str, match_id: int) -> str:
    if league_name == "SPL":
        return f"https://www.smiteproleague.com/matches/{match_id}"
    elif league_name == "SCC":
        return f"https://scc.smiteproleague.com/matches/{match_id}"
    raise RuntimeError(f"Unknown league_name: {league_name}")


def get_display_name(search_name: str, name_was_modified: int) -> str:
    if name_was_modified == 1:
        return search_name + " Upgrade"
    elif name_was_modified == 2:
        return "Evolved " + search_name
    elif name_was_modified == 3:
        return "Greater " + search_name
    return search_name


def normalize_image_data(data: bytes) -> tuple[str, str]:
    try:
        base64_data = data.decode("ascii")
    except UnicodeDecodeError:
        mime_type = get_image_mime_type(data)
        return mime_type, base64.b64encode(data).decode("ascii")

    try:
        decoded_data = base64.b64decode(base64_data, validate=True)
    except ValueError:
        mime_type = get_image_mime_type(data)
        return mime_type, base64.b64encode(data).decode("ascii")

    mime_type = get_image_mime_type(decoded_data)
    return mime_type, base64_data


def get_image_mime_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    raise RuntimeError(f"Unknown image format, first bytes: {data[:16]!r}")


def write_json_file(path: Path, data: t.Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
