import argparse
import csv
import json
import math
import random
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
from app.config import settings
from app.schemas import Credentials, TaskCreate
from app.security import passwords

from dataset_store import API_URL, ROOT, account_ids, dataset_session, validate_id

DATASETS = json.loads(Path(ROOT, "datasets", "presets.json").read_text())
SUBJECTS = ("release", "billing", "reports", "search", "dashboard", "onboarding", "notifications")
ACTIONS = ("verify", "update", "review", "prepare", "investigate", "document")
STATUSES = ("todo", "in_progress", "done")


def parse_args():
    parser = argparse.ArgumentParser(description="Seed an isolated Performance dataset")
    parser.add_argument("--dataset", choices=DATASETS, default="smoke")
    parser.add_argument("--users", type=int)
    parser.add_argument("--tasks-per-user", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dataset-id", type=validate_id)
    parser.add_argument("--mode", choices=("db", "api"), default="db")
    parser.add_argument("--base-url", default=API_URL)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--status-weights", type=float, nargs=3, default=(50, 30, 20),
                        metavar=("TODO", "IN_PROGRESS", "DONE"))
    parser.add_argument("--distribution", choices=("uniform", "skewed"), default="uniform")
    parser.add_argument("--allow-large", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    preset = DATASETS[args.dataset]
    args.users = preset["users"] if args.users is None else args.users
    args.tasks_per_user = preset["tasks_per_user"] if args.tasks_per_user is None else args.tasks_per_user
    total = args.users * args.tasks_per_user
    if not (1 <= args.users <= 10000 and 0 <= args.tasks_per_user and total <= 2_000_000
            and 1 <= args.batch_size <= 10000 and 1 <= args.concurrency <= 16
            and -(2**63) <= args.seed < 2**63):
        parser.error("Dataset size, concurrency, batch size or seed out of bounds")
    if (not all(math.isfinite(value) and 0 <= value <= 1e9 for value in args.status_weights)
            or sum(args.status_weights) == 0):
        parser.error("Use three finite nonnegative status weights with positive total")
    if (total >= 100_000 or args.users >= 1000 or (args.mode == "api" and total > 10_000)
            ) and not (args.allow_large or args.dry_run):
        parser.error("Use --allow-large to confirm this dataset size")
    args.base_url = args.base_url.rstrip("/")
    if args.base_url not in {API_URL, "http://localhost:8000"}:
        parser.error(f"Run inside Performance backend with --base-url {API_URL}")
    return args


def tasks_for_user(args, position, count):
    rng = random.Random(f"{args.seed}:{position}")
    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        subject = rng.choice(SUBJECTS)
        action = rng.choice(ACTIONS)
        body = TaskCreate(
            title=f"{action.capitalize()} {subject} {position + 1:04d}-{index + 1:06d}",
            description=(f"Plan, validate and record results for {subject}. " * rng.randint(0, 10))[:500],
            status=rng.choices(STATUSES, args.status_weights)[0],
            due_date=None if rng.random() < .25 else epoch.date() + timedelta(days=rng.randrange(730)),
        )
        created = epoch + timedelta(seconds=rng.randrange(31_536_000))
        updated = created + timedelta(seconds=rng.randrange(604800))
        yield body, created, updated


def task_counts(args):
    total = args.users * args.tasks_per_user
    if args.distribution == "uniform" or args.users == 1:
        return [args.tasks_per_user] * args.users
    heavy_users = max(1, args.users // 10)
    heavy_tasks = total * 8 // 10
    return [n // users + int(i < n % users)
            for n, users in [(heavy_tasks, heavy_users), (total - heavy_tasks, args.users - heavy_users)]
            for i in range(users)]


def save_db(args, db, position, credentials, count):
    owner_id = uuid4()
    with db.transaction():
        db.execute("INSERT INTO users (id, email, password_hash, created_at) VALUES (%s,%s,%s,now())",
                   (owner_id, credentials.email, passwords.hash(credentials.password)))
    rows = (
        (uuid4(), owner_id, task.title, task.description, task.status, task.due_date, created, updated)
        for task, created, updated in tasks_for_user(args, position, count)
    )
    while batch := list(islice(rows, args.batch_size)):
        with db.transaction(), db.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO tasks (id, owner_id, title, description, status, due_date, "
                "created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", batch,
            )


def save_api(args, position, credentials, count):
    with httpx.Client(base_url=args.base_url + "/api/v1/", headers={"Origin": settings.origins[0]},
                      timeout=10, trust_env=False, follow_redirects=False) as client:
        for route in ("register", "login"):
            client.post(f"auth/{route}", json=credentials.model_dump()).raise_for_status()
        csrf = client.get("auth/csrf").raise_for_status().json()["csrf_token"]
        for task, _, _ in tasks_for_user(args, position, count):
            client.post("tasks", json=task.model_dump(mode="json"),
                        headers={"X-CSRF-Token": csrf}).raise_for_status()


def write_credentials(path, credentials):
    with path.open("x", encoding="utf-8", newline="") as file:
        if path.suffix == ".csv":
            writer = csv.DictWriter(file, fieldnames=["email", "password"])
            writer.writeheader()
            writer.writerows(credentials)
        else:
            json.dump(credentials, file, indent=2)


def main():
    args = parse_args()
    counts = task_counts(args)
    nonce = secrets.token_hex(8)
    dataset_id = args.dataset_id or f"{args.dataset}-{nonce}"
    plan = {"dataset_id": dataset_id, "mode": args.mode,
            "requested_users": args.users, "requested_tasks": sum(counts), "seed": args.seed}
    if args.dry_run:
        print(json.dumps(plan))
        return 0

    artifact_dir = Path(ROOT, "artifacts").resolve()
    output = (args.output or artifact_dir / f"{dataset_id}.{args.format}").resolve()
    if output.suffix not in {".csv", ".json"} or not output.is_relative_to(artifact_dir):
        raise ValueError("Use a .json or .csv path under /performance/artifacts")
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        Credentials(email=f"perf-{nonce}-{i+1:05d}@example.test", password=secrets.token_urlsafe(18))
        for i in range(args.users)
    ]
    started = perf_counter()
    errors = 0
    with dataset_session(initialize=True) as db:
        with db.transaction(), db.cursor() as cursor:
            cursor.execute("INSERT INTO performance.datasets (id,seed,mode) VALUES (%s,%s,%s)",
                           (dataset_id, args.seed, args.mode))
            cursor.executemany(
                "INSERT INTO performance.accounts (dataset_id,position,email) VALUES (%s,%s,%s)",
                [(dataset_id, index, entry.email) for index, entry in enumerate(entries)],
            )

        if args.mode == "db":
            for args_for_user in zip(range(args.users), entries, counts, strict=True):
                try:
                    save_db(args, db, *args_for_user)
                except Exception as exc:
                    print(f"DB generation stopped after {type(exc).__name__}")
                    errors += 1
                    break
        else:
            with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
                jobs = [executor.submit(save_api, args, *item)
                        for item in zip(range(args.users), entries, counts, strict=True)]
                for job in jobs:
                    try:
                        job.result()
                    except Exception as exc:
                        errors += 1
                        print(f"API generation error: {type(exc).__name__}")

        ids = account_ids(db, dataset_id)
        emails = {row[0] for row in db.execute(
            "SELECT email FROM performance.accounts WHERE dataset_id=%s AND user_id IS NOT NULL",
            (dataset_id,),
        )}
        total = db.execute("SELECT count(*) FROM tasks WHERE owner_id = ANY(%s)", (ids,)).fetchone()[0]
        errors = max(errors, int(len(ids) != args.users or total != sum(counts)))
        if args.analyze and args.mode == "db":
            db.execute("ANALYZE users, tasks")
        db.execute("UPDATE performance.datasets SET status=%s WHERE id=%s",
                   ("partial" if errors else "ready", dataset_id))
        db.commit()
        write_credentials(output, [entry.model_dump() for entry in entries if entry.email in emails])
    print(json.dumps(plan | {"users": len(ids), "tasks": total, "errors": errors,
                             "duration_seconds": round(perf_counter() - started, 3),
                             "credentials": str(output)}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
