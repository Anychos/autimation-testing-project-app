SELECT waiting.pid AS waiting_pid, blocker.pid AS blocker_pid,
       now()-waiting.query_start AS waiting_age,
       left(waiting.query,500) AS waiting_query, left(blocker.query,500) AS blocker_query
FROM pg_stat_activity waiting
CROSS JOIN LATERAL unnest(pg_blocking_pids(waiting.pid)) AS blocking(pid)
JOIN pg_stat_activity blocker ON blocker.pid=blocking.pid
WHERE waiting.datname=current_database() ORDER BY waiting.query_start;
