IF DB_ID('rooms_db') IS NULL CREATE DATABASE rooms_db;
GO
IF DB_ID('battle_db') IS NULL CREATE DATABASE battle_db;
GO
IF SUSER_ID('rooms_user') IS NULL
    CREATE LOGIN rooms_user WITH PASSWORD = '$(ROOMS_DB_PASSWORD)', DEFAULT_DATABASE = rooms_db;
ELSE
    ALTER LOGIN rooms_user WITH PASSWORD = '$(ROOMS_DB_PASSWORD)';
GO
IF SUSER_ID('battle_user') IS NULL
    CREATE LOGIN battle_user WITH PASSWORD = '$(BATTLE_DB_PASSWORD)', DEFAULT_DATABASE = battle_db;
ELSE
    ALTER LOGIN battle_user WITH PASSWORD = '$(BATTLE_DB_PASSWORD)';
GO
USE rooms_db;
GO
IF USER_ID('rooms_user') IS NULL CREATE USER rooms_user FOR LOGIN rooms_user;
ALTER ROLE db_owner ADD MEMBER rooms_user;
GO
USE battle_db;
GO
IF USER_ID('battle_user') IS NULL CREATE USER battle_user FOR LOGIN battle_user;
ALTER ROLE db_owner ADD MEMBER battle_user;
GO
