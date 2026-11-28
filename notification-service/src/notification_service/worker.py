import json
import logging
import signal
from contextlib import suppress
from threading import Event, Thread
from time import perf_counter
from uuid import UUID

import pika
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from notification_service.database import engine
from notification_service.email_delivery import process_delivery
from notification_service.events import TaskPayload, event_adapter
from notification_service.health import clear_heartbeat, delivery_loops, heartbeat
from notification_service.logging_config import configure_logging, log
from notification_service.messaging import DLX, connect, declare_topology, publish
from notification_service.notifications import EventConflict, store_notification
from notification_service.settings import get_settings

SERVICE = "notification-worker"
BROKER_ERRORS = (pika.exceptions.AMQPError, OSError)


def uuid_metadata(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


def process_message(channel, publisher, method, properties, body):
    settings = get_settings()
    headers = properties.headers or {}
    attempt = headers.get("x-notification-attempt", 0)
    if type(attempt) is not int or attempt < 0:
        attempt = 0
    routing_key = headers.get("x-original-routing-key", method.routing_key)
    fields = {
        "event_id": uuid_metadata(properties.message_id),
        "correlation_id": uuid_metadata(properties.correlation_id),
        "attempt_count": attempt + 1,
    }
    try:
        raw = json.loads(body)
        if isinstance(raw, dict):
            for key in ("event_id", "correlation_id", "user_id"):
                fields[key] = uuid_metadata(raw.get(key)) or fields.get(key)
            payload = raw.get("payload")
            if isinstance(payload, dict):
                fields["task_id"] = uuid_metadata(payload.get("task_id"))
    except (ValueError, RecursionError):
        pass
    log(SERVICE, "Event received", **fields)
    metrics = None
    if settings.metrics_enabled:
        from notification_service import worker_metrics as metrics
    retry = False
    try:
        event = event_adapter.validate_json(body)
        fields["event_type"] = event.event_type
        if isinstance(event.payload, TaskPayload):
            fields["task_id"] = event.payload.task_id
        notification_id, created = store_notification(event)
    except ValidationError as exc:
        if metrics:
            metrics.EVENTS.labels("invalid").inc()
        first = exc.errors(include_input=False, include_context=False)[0]
        location = ".".join(str(part) for part in first["loc"])[:160]
        reason = f'{first["type"]} at {location or "envelope"}'
        log(SERVICE, "Invalid event", level=logging.WARNING, error_type="ValidationError", **fields)
    except EventConflict:
        if metrics:
            metrics.EVENTS.labels("conflict").inc()
        reason = "event_id already exists with different content"
    except SQLAlchemyError as exc:
        if metrics:
            metrics.EVENTS.labels("database_error").inc()
        reason = type(exc).__name__
        retry = attempt < settings.event_max_retries
        for loop in delivery_loops():
            clear_heartbeat(loop)
        log(SERVICE, "Event database error", level=logging.WARNING, error_type=reason, **fields)
    else:
        if metrics:
            metrics.observe_event(event, created)
        log(SERVICE, "Notification created" if created else "Duplicate event",
            notification_id=notification_id, **fields)
        channel.basic_ack(method.delivery_tag)
        return

    next_attempt = attempt + 1 if retry else attempt
    transfer_headers = {
        "x-notification-attempt": next_attempt,
        "x-original-routing-key": routing_key,
        "x-notification-error": reason,
    }
    if retry:
        intervals = settings.retry_intervals
        seconds = intervals[min(attempt, len(intervals) - 1)]
        exchange, key = "", f"{settings.rabbitmq_queue}.retry.{seconds}s"
    else:
        exchange, key = DLX, f"{settings.rabbitmq_queue}.dlq"
    publish(publisher, exchange, key, body,
            message_id=fields["event_id"], correlation_id=fields["correlation_id"],
            headers=transfer_headers)
    if metrics:
        metrics.EVENTS.labels("retry" if retry else "dlq").inc()
    channel.basic_ack(method.delivery_tag)
    log(SERVICE, "Event scheduled for retry" if retry else "Event moved to DLQ",
        level=logging.WARNING, error_type=reason, **fields)


def consume(stop: Event):
    while not stop.is_set():
        connection = None
        try:
            connection = connect()
            channel = connection.channel()
            declare_topology(channel)
            publisher = connection.channel()
            publisher.confirm_delivery()
            channel.basic_qos(prefetch_count=get_settings().rabbitmq_prefetch)

            def on_message(ch, method, properties, body, publisher=publisher):
                if not get_settings().metrics_enabled:
                    process_message(ch, publisher, method, properties, body)
                    return

                from notification_service import worker_metrics as metrics

                started = perf_counter()
                metrics.EVENTS.labels("received").inc()
                if method.redelivered:
                    metrics.EVENTS.labels("redelivered").inc()
                with metrics.IN_FLIGHT.track_inprogress():
                    try:
                        process_message(ch, publisher, method, properties, body)
                    except Exception:
                        metrics.EVENTS.labels("callback_error").inc()
                        raise
                    finally:
                        metrics.DURATION.observe(perf_counter() - started)

            tag = channel.basic_consume(get_settings().rabbitmq_queue, on_message, auto_ack=False)
            log(SERVICE, "RabbitMQ consumer connected")
            while tag in channel.consumer_tags and not stop.is_set():
                connection.process_data_events(time_limit=1)
                heartbeat("broker")
            if not stop.is_set():
                log(SERVICE, "RabbitMQ cancelled consumer", level=logging.WARNING)
        except BROKER_ERRORS as exc:
            log(SERVICE, "RabbitMQ unavailable", level=logging.WARNING,
                error_type=type(exc).__name__)
        finally:
            clear_heartbeat("broker")
            # Closing returns any unacknowledged message to the broker.
            if connection is not None and connection.is_open:
                with suppress(*BROKER_ERRORS):
                    connection.close()
        stop.wait(2)


def deliver(stop: Event, loop: str):
    database_available = False
    while not stop.is_set():
        try:
            if get_settings().email_enabled:
                worked = process_delivery()
            else:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                worked = False
            heartbeat(loop)
            if not database_available:
                log(SERVICE, "Notification database connected")
                database_available = True
            if not worked:
                stop.wait(1)
        except SQLAlchemyError as exc:
            clear_heartbeat(loop)
            if database_available:
                log(SERVICE, "Notification database unavailable", level=logging.WARNING,
                    error_type=type(exc).__name__)
            database_available = False
            stop.wait(2)
    clear_heartbeat(loop)


def main():
    configure_logging()
    loops = delivery_loops()
    for loop in ("broker", *loops):
        clear_heartbeat(loop)
    stop = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    settings = get_settings()
    if settings.metrics_enabled:
        from notification_service.worker_metrics import start_metrics

        start_metrics()
    workers = [
        Thread(target=deliver, args=(stop, loop), name=loop)
        for loop in loops
    ]
    for worker in workers:
        worker.start()
    try:
        consume(stop)
    finally:
        stop.set()
        for worker in workers:
            worker.join()
        engine.dispose()


if __name__ == "__main__":
    main()
