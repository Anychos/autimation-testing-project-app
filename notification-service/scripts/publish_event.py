import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import ValidationError

from notification_service.events import event_adapter
from notification_service.messaging import EVENT_TYPES, connect, declare_topology, publish
from notification_service.settings import get_settings


def main():
    parser = argparse.ArgumentParser(description="Publish a fixture to the local RabbitMQ broker")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--file", type=Path)
    mode.add_argument("--raw")
    mode.add_argument("--invalid", action="store_true")
    parser.add_argument("--allow-invalid", action="store_true", help="Publish an invalid --file")
    parser.add_argument("--type", choices=EVENT_TYPES, default="task.created")
    parser.add_argument("--email", default="test@example.test")
    parser.add_argument("--title", default="Test notification")
    parser.add_argument("--status", choices=("todo", "in_progress", "done"))
    for name in ("event-id", "user-id", "task-id", "correlation-id"):
        parser.add_argument(f"--{name}", type=UUID)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    if args.allow_invalid and args.file is None:
        parser.error("--allow-invalid requires --file")

    raw_mode = args.raw is not None or args.invalid or args.allow_invalid
    if args.file:
        body = args.file.read_bytes()
    elif args.raw is not None:
        body = args.raw.encode()
    else:
        payload = {}
        if args.type.startswith("task."):
            payload.update(
                task_id=args.task_id or uuid4(), title=args.title,
                status=args.status or ("done" if args.type == "task.completed" else "todo"),
            )
        if args.type in {"user.registered", "task.created", "task.completed"}:
            payload["recipient_email"] = args.email
        event = {
            "event_id": args.event_id or uuid4(), "event_type": args.type,
            "schema_version": 1, "occurred_at": datetime.now(UTC).isoformat(),
            "source": "taskflow-backend", "correlation_id": args.correlation_id or uuid4(),
            "user_id": args.user_id or uuid4(), "payload": payload,
        }
        if args.invalid:
            del event["payload"]
        body = json.dumps(event, default=str).encode()

    if not raw_mode:
        try:
            event_adapter.validate_json(body)
        except ValidationError as exc:
            parser.error(str(exc.errors(include_input=False, include_context=False)))
    try:
        data = json.loads(body)
    except (ValueError, RecursionError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    ids = {}
    for key in ("event_id", "correlation_id", "user_id"):
        try:
            ids[key] = str(UUID(data.get(key)))
        except (ValueError, TypeError, AttributeError):
            ids[key] = None
    routing_key = data.get("event_type")
    if routing_key not in EVENT_TYPES:
        routing_key = args.type
    with connect() as connection:
        channel = connection.channel()
        declare_topology(channel)
        channel.confirm_delivery()
        for _ in range(args.repeat):
            publish(channel, get_settings().rabbitmq_exchange, routing_key, body,
                    message_id=ids["event_id"], correlation_id=ids["correlation_id"])
    payload = data.get("payload")
    if isinstance(payload, dict):
        try:
            ids["task_id"] = str(UUID(payload.get("task_id")))
        except (ValueError, TypeError, AttributeError):
            pass
    print(json.dumps({**ids, "routing_key": routing_key, "published": args.repeat}))


if __name__ == "__main__":
    main()
