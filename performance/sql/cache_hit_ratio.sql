SELECT datname, blks_read, blks_hit,
       round(100.0*blks_hit/nullif(blks_hit+blks_read,0),2) AS cache_hit_percent
FROM pg_stat_database WHERE datname=current_database();
