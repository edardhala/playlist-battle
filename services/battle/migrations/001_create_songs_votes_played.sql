CREATE TABLE songs (
    id        INT IDENTITY(1, 1) PRIMARY KEY,
    room_id   INT NOT NULL,
    title     NVARCHAR(80) NOT NULL,
    artist    NVARCHAR(80) NOT NULL,
    added_by  NVARCHAR(30) NOT NULL,
    added_at  DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE INDEX ix_songs_room_id ON songs (room_id);

CREATE TABLE votes (
    id       INT IDENTITY(1, 1) PRIMARY KEY,
    song_id  INT NOT NULL REFERENCES songs(id),
    voter    NVARCHAR(30) NOT NULL,
    CONSTRAINT uq_votes_song_voter UNIQUE (song_id, voter)
);

CREATE TABLE played (
    id         INT IDENTITY(1, 1) PRIMARY KEY,
    song_id    INT NOT NULL UNIQUE REFERENCES songs(id),
    played_at  DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
