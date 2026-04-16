import json
import sqlite3
from pathlib import Path

from backend.webapi.tools.export_archive import ARCHIVE_DB_NAME, export_archive


def test_export_archive(tmp_path: Path) -> None:
    source_path = tmp_path / "backend.db"
    archive_dir = tmp_path / "archive"
    create_source_db(source_path)

    export_archive(source_path, archive_dir)

    options = json.loads((archive_dir / "options.json").read_text("utf8"))
    assert options["season"] == [10]
    assert options["win"] == [True]
    assert options["item"] == ["Bancroft's Talon"]
    assert options["relic"] == ["Purification Beads"]

    last_check = json.loads((archive_dir / "last-check.json").read_text("utf8"))
    assert last_check == {"value": "15 Apr 2026", "tooltip": "Manual export"}

    archive_db_path = archive_dir / ARCHIVE_DB_NAME
    with sqlite3.connect(archive_db_path) as connection:
        build_row = connection.execute("SELECT season, match_url FROM build").fetchone()
        assert build_row == (
            10,
            "https://www.smiteproleague.com/matches/1234",
        )

        build_item_rows = connection.execute(
            """
            SELECT is_relic, search_name, display_name, image_id
            FROM build_item
            ORDER BY is_relic DESC, slot_index ASC
            """
        ).fetchall()
        assert build_item_rows == [
            (1, "Purification Beads", "Purification Beads", 1),
            (0, "Bancroft's Talon", "Evolved Bancroft's Talon", 2),
        ]

        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        assert page_size == 1024


def create_source_db(source_path: Path) -> None:
    with sqlite3.connect(source_path) as connection:
        connection.executescript(
            """
            CREATE TABLE build (
                id INTEGER PRIMARY KEY,
                season INTEGER NOT NULL,
                league TEXT NOT NULL,
                phase TEXT NOT NULL,
                date TEXT NOT NULL,
                match_id INTEGER NOT NULL,
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
                data BLOB NOT NULL
            );

            CREATE TABLE item (
                id INTEGER PRIMARY KEY,
                is_relic INTEGER NOT NULL,
                name TEXT NOT NULL,
                name_was_modified INTEGER NOT NULL,
                image_name TEXT NOT NULL,
                image_id INTEGER
            );

            CREATE TABLE build_item (
                build_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                "index" INTEGER NOT NULL
            );

            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        connection.execute(
            """
            INSERT INTO build (
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                10,
                "SPL",
                "Summer Masters",
                "2024-01-02",
                1234,
                1,
                1,
                "00:31:45",
                3.5,
                7,
                2,
                9,
                "Mid",
                "Mage",
                "Agni",
                "Player One",
                "Jade Dragons",
                "Raijin",
                "Player Two",
                "Leviathans",
            ),
        )
        connection.executemany(
            "INSERT INTO image (id, data) VALUES (?, ?)",
            [(1, b"relic-image"), (2, b"item-image")],
        )
        connection.executemany(
            """
            INSERT INTO item (
                id,
                is_relic,
                name,
                name_was_modified,
                image_name,
                image_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 1, "Purification Beads", 0, "beads", 1),
                (2, 0, "Bancroft's Talon", 2, "bancrofts", 2),
            ],
        )
        connection.executemany(
            'INSERT INTO build_item (build_id, item_id, "index") VALUES (?, ?, ?)',
            [(1, 1, 0), (1, 2, 0)],
        )
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            [
                ("last_checked", "15 Apr 2026"),
                ("last_checked_tooltip", "Manual export"),
            ],
        )
        connection.commit()
