SELECT pid, usename, application_name, state, now()-xact_start AS transaction_age,
       wait_event_type, wait_event, left(query,500) AS query
FROM pg_stat_activity WHERE datname=current_database() AND xact_start IS NOT NULL
AND pid<>pg_backend_pid() ORDER BY xact_start;
