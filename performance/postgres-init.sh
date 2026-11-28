#!/bin/sh
set -eu
psql --no-psqlrc --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv exporter_password PERF_EXPORTER_PASSWORD
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE ROLE perf_monitor LOGIN PASSWORD :'exporter_password';
GRANT pg_monitor TO perf_monitor;
CREATE SCHEMA performance;
REVOKE ALL ON SCHEMA performance FROM PUBLIC;
CREATE TABLE performance.identity (environment text PRIMARY KEY);
INSERT INTO performance.identity VALUES ('taskflow-performance');
GRANT USAGE ON SCHEMA performance TO perf_monitor;
GRANT SELECT ON performance.identity TO perf_monitor;
SQL
