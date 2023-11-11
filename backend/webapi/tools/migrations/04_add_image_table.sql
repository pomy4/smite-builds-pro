CREATE TABLE image (
        id INTEGER NOT NULL,
        data BLOB NOT NULL,
        PRIMARY KEY (id)
)

CREATE TABLE item (
        id INTEGER NOT NULL,
        is_relic BOOLEAN NOT NULL,
        name VARCHAR(50) NOT NULL,
        name_was_modified SMALLINT NOT NULL,
        image_name VARCHAR(50) NOT NULL,
        image_id INTEGER,
        PRIMARY KEY (id),
        FOREIGN KEY(image_id) REFERENCES image (id)
)

CREATE INDEX ix_item_image_id ON item (image_id)

CREATE UNIQUE INDEX ix_item_unique ON item (is_relic, name, name_was_modified, image_name, image_id)
