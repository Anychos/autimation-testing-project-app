-- Run with psql -v owner_id=<UUID> -v search=release -v page_offset=100.
EXPLAIN
SELECT count(*) FROM tasks WHERE owner_id=:'owner_id'::uuid
AND status='todo' AND lower(title) LIKE '%' || lower(:'search') || '%' ESCAPE '/';

EXPLAIN ANALYZE
SELECT * FROM tasks WHERE owner_id=:'owner_id'::uuid
AND status='todo' AND lower(title) LIKE '%' || lower(:'search') || '%' ESCAPE '/'
ORDER BY created_at DESC, id ASC OFFSET :page_offset LIMIT 10;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM tasks WHERE owner_id=:'owner_id'::uuid
ORDER BY due_date ASC NULLS LAST, id ASC OFFSET :page_offset LIMIT 10;

-- The Dashboard reads pagination totals from /tasks for all, in_progress and done.
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM tasks WHERE owner_id=:'owner_id'::uuid;
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM tasks WHERE owner_id=:'owner_id'::uuid AND status='in_progress';
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM tasks WHERE owner_id=:'owner_id'::uuid AND status='done';
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM tasks WHERE owner_id=:'owner_id'::uuid
ORDER BY created_at DESC, id ASC OFFSET :page_offset LIMIT 50;
