-- PostgreSQL 17. I/O statistics are aggregated by backend type, object and context.
SELECT backend_type, object, context, reads, writes, op_bytes, read_time, write_time,
       fsyncs, fsync_time, stats_reset
FROM pg_stat_io ORDER BY backend_type, object, context;
