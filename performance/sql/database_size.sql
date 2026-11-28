SELECT current_database() AS database, pg_database_size(current_database()) AS bytes,
       pg_size_pretty(pg_database_size(current_database())) AS size;
SELECT schemaname, relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC;
