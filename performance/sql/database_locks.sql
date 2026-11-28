SELECT pid, locktype, relation::regclass, mode, granted, waitstart
FROM pg_locks WHERE database=(SELECT oid FROM pg_database WHERE datname=current_database())
                       OR database IS NULL ORDER BY granted, waitstart NULLS LAST;
