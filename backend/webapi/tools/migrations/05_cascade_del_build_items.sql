CREATE TABLE build_item (
        build_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        "index" SMALLINT NOT NULL,
        PRIMARY KEY (build_id, item_id),
        FOREIGN KEY(build_id) REFERENCES build (id) ON DELETE CASCADE,
        FOREIGN KEY(item_id) REFERENCES item (id)
)

CREATE INDEX ix_build_item_build_id ON build_item (build_id)

CREATE INDEX ix_build_item_item_id ON build_item (item_id)
