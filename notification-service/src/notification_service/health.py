import sys
from pathlib import Path
from time import time
from urllib.request import urlopen

from notification_service.settings import get_settings


def delivery_loops():
    count = get_settings().smtp_delivery_concurrency
    return ("delivery", *(f"delivery-{index}" for index in range(2, count + 1)))


def heartbeat_path(loop):
    return Path(f"/tmp/notification-worker-{loop}.heartbeat")


def heartbeat(loop):
    path = heartbeat_path(loop)
    scratch = path.with_suffix(".tmp")
    scratch.touch()
    scratch.replace(path)


def clear_heartbeat(loop):
    heartbeat_path(loop).unlink(missing_ok=True)


def worker_healthy():
    now = time()
    try:
        return all(
            0 <= now - heartbeat_path(loop).stat().st_mtime <= (12 if loop == "broker" else 60)
            for loop in ("broker", *delivery_loops())
        )
    except FileNotFoundError:
        return False


if __name__ == "__main__":
    if sys.argv[1] == "worker":
        sys.exit(0 if worker_healthy() else 1)
    with urlopen(f"http://127.0.0.1:{get_settings().app_port}/health/ready", timeout=3) as result:
        sys.exit(0 if result.status == 200 else 1)
