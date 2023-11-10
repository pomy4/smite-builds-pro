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
        god_class VARCHAR(50),
        god1 VARCHAR(50) NOT NULL,
        player1 VARCHAR(50) NOT NULL,
        team1 VARCHAR(50) NOT NULL,
        god2 VARCHAR(50) NOT NULL,
        player2 VARCHAR(50) NOT NULL,
        team2 VARCHAR(50) NOT NULL,
        PRIMARY KEY (id)
)

CREATE INDEX ix_build_role ON build (role)

CREATE INDEX ix_build_god_class ON build (god_class)

CREATE INDEX ix_build_god1 ON build (god1)

CREATE UNIQUE INDEX ix_build_unique ON build (match_id, game_i, player1)
