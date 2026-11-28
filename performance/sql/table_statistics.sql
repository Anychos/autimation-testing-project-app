SELECT s.schemaname, s.relname, s.seq_scan, s.idx_scan, s.n_live_tup, s.n_dead_tup,
       s.n_tup_ins, s.n_tup_upd, s.n_tup_del, i.heap_blks_read, i.heap_blks_hit,
       s.last_analyze, s.last_autoanalyze
FROM pg_stat_user_tables s JOIN pg_statio_user_tables i USING (relid)
ORDER BY s.seq_scan DESC;
