CREATE TABLE polzovateli (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES polzovateli(id)
);

CREATE INDEX user_devices_in
ON devices (user_id);


CREATE TABLE pokazaniya (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id TEXT NOT NULL,
    vremya_zapisi TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL
);

CREATE INDEX device_time_in
ON pokazaniya (device_id, vremya_zapisi);