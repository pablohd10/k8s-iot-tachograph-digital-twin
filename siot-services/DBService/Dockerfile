FROM mariadb:latest

RUN apt-get update && apt-get install -y mariadb-client

ADD initial_script.sql /docker-entrypoint-initdb.d/ddl.sql