CREATE TABLE metadata (
        "key" VARCHAR(50) NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY ("key")
)

CREATE TABLE item (
        id INTEGER NOT NULL,
        is_relic BOOLEAN NOT NULL,
        name VARCHAR(50) NOT NULL,
        name_was_modified SMALLINT NOT NULL,
        image_name VARCHAR(50) NOT NULL,
        image_data BLOB,
        PRIMARY KEY (id)
)


CREATE UNIQUE INDEX ix_item_unique ON item (is_relic, name, name_was_modified, image_name, image_data)

CREATE TABLE build (
        id INTEGER NOT NULL,
        season SMALLINT NOT NULL,
        league VARCHAR(50) NOT NULL,
        phase VARCHAR(50) NOT NULL,
        date DATE NOT NULL,
        match_id INTEGER NOT NULL,
        game_i SMALLINT NOT NULL,
        win BOOLEAN NOT NULL,
        game_length TIME NOT NULL,
        kda_ratio FLOAT NOT NULL,
        kills SMALLINT NOT NULL,
        deaths SMALLINT NOT NULL,
        assists SMALLINT NOT NULL,
        role VARCHAR(50) NOT NULL,
        god1 VARCHAR(50) NOT NULL,
        player1 VARCHAR(50) NOT NULL,
        team1 VARCHAR(50) NOT NULL,
        god2 VARCHAR(50) NOT NULL,
        player2 VARCHAR(50) NOT NULL,
        team2 VARCHAR(50) NOT NULL,
        PRIMARY KEY (id)
)


CREATE INDEX ix_build_role ON build (role)

CREATE INDEX ix_build_god1 ON build (god1)

CREATE UNIQUE INDEX ix_build_unique ON build (match_id, game_i, player1)

CREATE TABLE build_item (
        build_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        "index" SMALLINT NOT NULL,
        PRIMARY KEY (build_id, item_id),
        FOREIGN KEY(build_id) REFERENCES build (id),
        FOREIGN KEY(item_id) REFERENCES item (id)
)

CREATE INDEX ix_build_item_build_id ON build_item (build_id)

CREATE INDEX ix_build_item_item_id ON build_item (item_id)
