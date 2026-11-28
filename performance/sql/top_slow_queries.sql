SELECT queryid, calls, total_exec_time, mean_exec_time, max_exec_time, rows,
       shared_blks_hit, shared_blks_read, shared_blks_dirtied, shared_blks_written,
       temp_blks_read, temp_blks_written, query
FROM pg_stat_statements WHERE dbid = (SELECT oid FROM pg_database WHERE datname=current_database())
AND calls >= 1 ORDER BY mean_exec_time DESC LIMIT 30;
