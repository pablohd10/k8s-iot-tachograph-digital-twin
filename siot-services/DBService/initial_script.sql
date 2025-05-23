-- create database
create database tachograph_data;

-- Create a new user (only with local access) and grant privileges to this user on the new database:
grant all privileges on tachograph_data.* TO 'fic_db_user'@'%' identified by 'RP#64nY7*E*H';

-- After modifying the MariaDB grant tables, execute the following command in order to apply the changes:
FLUSH PRIVILEGES;

-- Change to the created database
use tachograph_data;

-- Crear la tabla 'events'
CREATE TABLE events (
    id MEDIUMINT NOT NULL AUTO_INCREMENT,
    tachograph_id VARCHAR(50) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    warning VARCHAR(100) NOT NULL,
    time_stamp DATETIME(6) NOT NULL,
    PRIMARY KEY (id)
);

-- Crear la tabla 'telemetry'
CREATE TABLE telemetry (
    id MEDIUMINT NOT NULL AUTO_INCREMENT,
    tachograph_id VARCHAR(50) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    gps_speed FLOAT NOT NULL,
    current_speed FLOAT NOT NULL,
    current_driver_id VARCHAR(50) NOT NULL,
    time_stamp DATETIME(6) NOT NULL,
    PRIMARY KEY (id)
);