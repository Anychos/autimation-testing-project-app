import argparse
import json
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PERF = Path(__file__).resolve().parents[1]
PROJECT = "taskflow-performance"
SAFE_ENV = {
    "APP_ENV", "BACKEND_WORKERS", "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT",
    "DB_POOL_RECYCLE", "DB_POOL_PRE_PING", "NOTIFICATIONS_ENABLED", "METRICS_ENABLED",
    "RABBITMQ_PREFETCH", "SMTP_DELIVERY_CONCURRENCY", "OUTBOX_BATCH_SIZE",
    "OUTBOX_POLL_INTERVAL", "HTTP_CONNECT_TIMEOUT", "HTTP_READ_TIMEOUT", "POSTGRES_DB",
}
LIMITS = {"low": (0.5, 512 * 2**20), "medium": (1, 2**30), "high": (4, 2 * 2**30)}


def run(*args):
    result = subprocess.run(args, capture_output=True, encoding="utf-8", errors="replace",
                            timeout=20, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def available(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def database_stats(container):
    query = """
    SELECT json_build_object(
      'database', current_database(), 'size_bytes', pg_database_size(current_database()),
      'max_connections', current_setting('max_connections')::int,
      'users', (SELECT count(*) FROM users), 'tasks', (SELECT count(*) FROM tasks),
      'outbox_pending', (SELECT count(*) FROM outbox_events WHERE status='PENDING'));
    """
    command = ("docker", "exec", container, "psql", "-XAt", "-U", "taskflow_perf",
               "-d", "taskflow_performance", "-c")
    result = run(*command, query)
    if result is None:
        return None
    stats = json.loads(result)
    rows = run(*command, """
        SELECT coalesce(json_agg(summary),'[]'::json) FROM (
          SELECT d.id, d.status, d.mode, d.seed, count(DISTINCT a.user_id) AS users,
                 count(t.id) AS tasks
          FROM performance.datasets d LEFT JOIN performance.accounts a ON a.dataset_id=d.id
          LEFT JOIN tasks t ON t.owner_id=a.user_id GROUP BY d.id ORDER BY d.id
        ) summary;
    """)
    stats["datasets"] = json.loads(rows) if rows else []
    return stats


def backend_workers(container):
    processes = run("docker", "top", container, "-eo", "pid,ppid,args")
    if not processes:
        return None
    gunicorn = {}
    for line in processes.splitlines()[1:]:
        pid, parent, args = line.split(maxsplit=2)
        if "/bin/gunicorn app.main:app" in args:
            gunicorn[pid] = parent
    return sum(parent in gunicorn for parent in gunicorn.values())


def collect(prometheus_url, grafana_url):
    ids = run("docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}")
    if ids is None:
        raise RuntimeError("Unable to inspect containers through Docker")
    raw = run("docker", "inspect", *ids.split()) if ids else "[]"
    if raw is None:
        raise RuntimeError("Performance containers changed during inspection. Retry.")
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "compose_project": PROJECT,
        "git_commit": run("git", "-C", str(PERF.parent), "rev-parse", "HEAD"),
        "working_tree_dirty": bool(run("git", "-C", str(PERF.parent), "status", "--porcelain")),
        "services": [],
        "resource_profile": "custom/unrestricted",
        "notification_worker_instances": 0,
        "backend_workers_running": None,
        "postgresql": None,
        "notification_postgresql": None,
        "rabbitmq_queues": None,
        "prometheus_available": available(prometheus_url + "/-/ready"),
        "grafana_available": available(grafana_url + "/api/health"),
    }
    for item in json.loads(raw):
        config = item["Config"]
        service = config["Labels"]["com.docker.compose.service"]
        state = item["State"]
        host = item["HostConfig"]
        cpu = host["NanoCpus"] / 1e9
        safe_env = {}
        for entry in config["Env"]:
            key, _, value = entry.partition("=")
            if key in SAFE_ENV:
                safe_env[key] = value
        result["services"].append({
            "service": service, "container": item["Name"].lstrip("/"),
            "status": state["Status"], "health": state.get("Health", {}).get("Status"),
            "image": config["Image"], "image_id": item["Image"],
            "cpus": cpu, "memory_limit_bytes": host["Memory"],
            "restart_count": item["RestartCount"], "oom_killed": state["OOMKilled"],
            "settings": safe_env,
        })
        if service == "backend":
            result["resource_profile"] = next(
                (name for name, values in LIMITS.items() if values == (cpu, host["Memory"])),
                "custom/unrestricted",
            )
        if not state["Running"]:
            continue
        if service == "backend":
            result["backend_workers_running"] = backend_workers(item["Id"])
        if service == "db":
            result["postgresql"] = database_stats(item["Id"])
        if service == "notification-db":
            size = run("docker", "exec", item["Id"], "psql", "-XAt", "-U", "notification_perf",
                       "-d", "notification_performance", "-c",
                       "SELECT json_build_object('size_bytes', pg_database_size(current_database()), "
                       "'max_connections', current_setting('max_connections')::int)")
            result["notification_postgresql"] = json.loads(size) if size else None
        if service == "notification-worker":
            result["notification_worker_instances"] += 1
        if service == "rabbitmq":
            queues = run("docker", "exec", item["Id"], "rabbitmqctl", "-q", "list_queues",
                         "-p", PROJECT, "name", "messages", "messages_ready",
                         "messages_unacknowledged", "consumers", "--formatter=json")
            result["rabbitmq_queues"] = json.loads(queues) if queues else None
    return result


def arguments(*, export=False):
    parser = argparse.ArgumentParser(description="Inspect the local TaskFlow Performance project")
    parser.add_argument("--prometheus-url", default="http://127.0.0.1:19090")
    parser.add_argument("--grafana-url", default="http://127.0.0.1:3001")
    if export:
        parser.add_argument("--output", type=Path,
                            default=PERF / "artifacts" / "environment.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = arguments()
    print(json.dumps(collect(args.prometheus_url, args.grafana_url), indent=2))
