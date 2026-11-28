from prometheus_client import Counter, Gauge, Histogram, start_http_server

from notification_service.database import utcnow

LAG_BUCKETS = (.01, .05, .1, .5, 1, 2, 5, 10, 30, 60, 120, 300, 900)
EVENTS = Counter("taskflow_notification_events", "Consumer events by outcome", ("outcome",))
DURATION = Histogram("taskflow_notification_processing_seconds", "Consumer callback duration")
IN_FLIGHT = Gauge("taskflow_notification_in_flight", "Consumer callbacks in progress")
EVENT_LAG = Histogram("taskflow_notification_event_lag_seconds",
                      "Event timestamp to notification persistence", buckets=LAG_BUCKETS)
CREATED = Counter("taskflow_notifications_created", "Persisted notifications", ("event_type",))
SMTP = Counter("taskflow_smtp_deliveries", "SMTP outcomes", ("outcome",))
SMTP_DURATION = Histogram("taskflow_smtp_send_seconds", "SMTP send operation duration")
SMTP_LAG = Histogram("taskflow_smtp_event_lag_seconds", "Event timestamp to SMTP acceptance",
                     buckets=LAG_BUCKETS)


def observe_event(event, created):
    EVENTS.labels("processed").inc()
    if created:
        CREATED.labels(event.event_type).inc()
        EVENT_LAG.observe(max(0, (utcnow() - event.occurred_at).total_seconds()))
    else:
        EVENTS.labels("duplicate").inc()


def start_metrics():
    for outcome in ("received", "processed", "invalid", "conflict", "database_error",
                    "redelivered", "duplicate", "retry", "dlq", "callback_error"):
        EVENTS.labels(outcome)
    for outcome in ("attempt", "accepted", "error", "retry", "failed"):
        SMTP.labels(outcome)
    start_http_server(9102)
