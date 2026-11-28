import argparse
import json
import os
from time import sleep

import httpx
from app.config import settings

from dataset_store import account_ids, dataset_session, open_db, validate_id

OUTBOX = "payload->>'user_id' = ANY(%s)"
QUERIES = {
    "users": ("users", "id = ANY(%s)"),
    "tasks": ("tasks", "owner_id = ANY(%s)"),
    "sessions": ("sessions", "user_id = ANY(%s)"),
}
VHOST = "taskflow-performance"


def queue_state():
    response = httpx.get(
        f"http://rabbitmq:15672/api/queues/{VHOST}",
        auth=("taskflow_perf", os.environ["PERF_RABBITMQ_PASSWORD"]), timeout=5, trust_env=False,
    )
    response.raise_for_status()
    queues = response.json()
    if not any(queue["name"] == "notification.events" for queue in queues):
        raise RuntimeError("Performance RabbitMQ topology could not be verified")
    return [
        {"name": queue["name"], "depth": int(queue["messages"]),
         "consumers": int(queue["consumers"])}
        for queue in queues
    ]


def mail_ids(client, emails):
    offset = 0
    while emails:
        response = client.get("messages", params={"start": offset, "limit": 100})
        response.raise_for_status()
        messages = response.json()["messages"] or []
        for message in messages:
            recipients = {entry["Address"].lower() for entry in message.get("To") or []}
            copied = (message.get("Cc") or []) + (message.get("Bcc") or [])
            if recipients and recipients <= emails and not copied:
                yield message["ID"]
        if len(messages) < 100:
            break
        offset += len(messages)


def remove_notification_data(db, ids, emails, *, apply):
    with httpx.Client(base_url="http://mailpit:8025/api/v1/", timeout=5, trust_env=False) as mail:
        counts = {
            "notifications": db.execute(
                "SELECT count(*) FROM notifications WHERE user_id=ANY(%s)", (ids,),
            ).fetchone()[0],
            "deliveries": db.execute(
                "SELECT count(*) FROM notification_deliveries d JOIN notifications n "
                "ON n.id=d.notification_id WHERE n.user_id=ANY(%s)", (ids,),
            ).fetchone()[0],
        }
        messages = list(mail_ids(mail, emails))
        counts["mailpit_messages"] = len(messages)
        if apply:
            for index in range(0, len(messages), 100):
                mail.request("DELETE", "messages", json={"IDs": messages[index:index + 100]}).raise_for_status()
            db.execute(
                "DELETE FROM notification_deliveries USING notifications "
                "WHERE notification_id=notifications.id AND notifications.user_id=ANY(%s)", (ids,),
            )
            db.execute("DELETE FROM notifications WHERE user_id=ANY(%s)", (ids,))
    return counts


def main():
    parser = argparse.ArgumentParser(description="Remove one registered Performance dataset")
    parser.add_argument("--dataset-id", required=True, type=validate_id)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--workers-stopped", action="store_true")
    args = parser.parse_args()
    with dataset_session(read_only=not args.apply) as db:
        if db.execute("SELECT to_regclass('performance.datasets')").fetchone()[0] is None:
            parser.error("No registered datasets")
        if not db.execute("SELECT 1 FROM performance.datasets WHERE id=%s", (args.dataset_id,)).fetchone():
            parser.error("Unknown dataset")
        ids = account_ids(db, args.dataset_id)
        emails = {row[0] for row in db.execute(
            "SELECT email FROM performance.accounts WHERE dataset_id=%s AND user_id IS NOT NULL",
            (args.dataset_id,),
        )}
        counts = {
            name: db.execute(f"SELECT count(*) FROM {table} WHERE {predicate}", (ids,)).fetchone()[0]
            for name, (table, predicate) in QUERIES.items()
        }
        counts["outbox"] = db.execute(
            f"SELECT count(*) FROM outbox_events WHERE {OUTBOX}", ([str(user) for user in ids],),
        ).fetchone()[0]
        if counts["outbox"] and not settings.notifications_enabled:
            parser.error("This dataset has Outbox history. Start Full mode for cleanup.")
        if settings.notifications_enabled:
            if args.apply and not args.workers_stopped:
                parser.error("Use cleanup.ps1 -Full -Apply to verify stopped publisher and workers")
            queues = queue_state()
            if args.apply:
                # Management statistics can lag the live state checked by rabbitmqctl.
                for _ in range(5):
                    if not any(queue["depth"] or queue["consumers"] for queue in queues):
                        break
                    sleep(2)
                    queues = queue_state()
                if any(queue["depth"] or queue["consumers"] for queue in queues):
                    parser.error("Queues must be empty with no consumers before Full cleanup")
            counts["rabbitmq"] = queues
            with open_db(notification=True) as notification:
                counts.update(remove_notification_data(notification, ids, emails, apply=args.apply))
        if args.apply:
            db.execute(f"DELETE FROM outbox_events WHERE {OUTBOX}", ([str(user) for user in ids],))
            db.execute("DELETE FROM users WHERE id=ANY(%s)", (ids,))
            db.execute("DELETE FROM performance.datasets WHERE id=%s", (args.dataset_id,))
            db.commit()
    print(json.dumps({"dataset_id": args.dataset_id, "applied": args.apply, **counts}))


if __name__ == "__main__":
    main()
