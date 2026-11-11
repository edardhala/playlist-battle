CREATE TABLE rooms (
    id    INT IDENTITY(1, 1) PRIMARY KEY,
    code  NVARCHAR(6) NOT NULL UNIQUE,
    name  NVARCHAR(30) NOT NULL
);

CREATE TABLE members (
    id       INT IDENTITY(1, 1) PRIMARY KEY,
    room_id  INT NOT NULL REFERENCES rooms(id),
    name     NVARCHAR(30) NOT NULL,
    is_host  BIT NOT NULL DEFAULT 0,
    CONSTRAINT uq_members_room_name UNIQUE (room_id, name)
);
