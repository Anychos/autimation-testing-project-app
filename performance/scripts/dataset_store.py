import os
import re
from contextlib import contextmanager

import psycopg
from app.config import settings

ROOT = "/performance"
API_URL = "http://127.0.0.1:8000"
SCOPE = "taskflow-performance"
DATASET_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
REGISTRY = """
CREATE TABLE IF NOT EXISTS performance.datasets (
    id text PRIMARY KEY,
    seed bigint NOT NULL,
    mode text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'building'
);
CREATE TABLE IF NOT EXISTS performance.accounts (
    dataset_id text NOT NULL REFERENCES performance.datasets ON DELETE CASCADE,
    position integer NOT NULL,
    email text NOT NULL UNIQUE,
    user_id uuid UNIQUE,
    PRIMARY KEY (dataset_id, position)
);
CREATE OR REPLACE FUNCTION performance.track_account() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE performance.accounts SET user_id = NEW.id
    WHERE email = NEW.email AND user_id IS NULL;
    RETURN NEW;
END;
$$;
CREATE OR REPLACE TRIGGER performance_track_account AFTER INSERT ON public.users
FOR EACH ROW WHEN (NEW.email LIKE 'perf-%@example.test')
EXECUTE FUNCTION performance.track_account();
"""


def validate_id(value):
    if not DATASET_ID.fullmatch(value):
        raise ValueError("Dataset ID must contain 1–40 lowercase letters, digits or hyphens")
    return value


def open_db(*, notification=False):
    scope = ("db", "taskflow_performance", "taskflow_perf")
    if settings.app_env != "performance" or (
        settings.db_host, settings.postgres_db, settings.postgres_user
    ) != scope:
        raise RuntimeError("Run this command inside the Performance backend container")

    if notification:
        host, name, user = "notification-db", "notification_performance", "notification_perf"
        password = os.environ["PERF_NOTIFICATION_DB_PASSWORD"]
    else:
        host, name, user = scope
        password = settings.postgres_password
    conn = psycopg.connect(host=host, dbname=name, user=user, password=password,
                           connect_timeout=5, application_name="taskflow-perf-tools")
    try:
        identity = conn.execute("SELECT current_database(), current_user, environment "
                                "FROM performance.identity").fetchall()
        if identity != [(name, user, SCOPE)]:
            raise RuntimeError("Performance database identity check failed")
        conn.commit()
    except Exception:
        conn.close()
        raise
    return conn


@contextmanager
def dataset_session(*, read_only=False, initialize=False):
    with open_db() as db:
        if read_only:
            db.execute("SET TRANSACTION READ ONLY")
            yield db
            return
        if not db.execute("SELECT pg_try_advisory_lock(72150, 1)").fetchone()[0]:
            raise RuntimeError("Another dataset operation is in progress")
        if initialize and db.execute("SELECT to_regclass('performance.accounts')").fetchone()[0] is None:
            db.execute(REGISTRY)
        db.commit()
        yield db


def account_ids(db, dataset_id):
    return [row[0] for row in db.execute(
        "SELECT user_id FROM performance.accounts WHERE dataset_id = %s AND user_id IS NOT NULL",
        (dataset_id,),
    )]
