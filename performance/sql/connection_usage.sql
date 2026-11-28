SELECT current_setting('max_connections')::integer AS max_connections,
       current_setting('superuser_reserved_connections')::integer AS reserved_for_superusers,
       count(*) AS connections, count(*) FILTER (WHERE state='active') AS active,
       count(*) FILTER (WHERE state='idle') AS idle,
       count(*) FILTER (WHERE state LIKE 'idle in transaction%') AS idle_in_transaction
FROM pg_stat_activity WHERE backend_type='client backend';
