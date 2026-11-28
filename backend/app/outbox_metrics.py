from prometheus_client import REGISTRY, Counter, Histogram, start_http_server
from prometheus_client.core import GaugeMetricFamily
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine

ITEMS = Counter("taskflow_outbox_events", "Outbox publication outcomes", ("outcome",))
DURATION = Histogram("taskflow_outbox_publish_seconds", "Publish attempt including DB transaction")
LAG = Histogram("taskflow_outbox_lag_seconds", "Event creation to broker confirmation",
                buckets=(.01, .05, .1, .5, 1, 2, 5, 10, 30, 60, 120, 300, 900))
for outcome in ("published", "confirmed", "error", "retry"):
    ITEMS.labels(outcome)


class OutboxBacklog:
    def describe(self):
        return ()

    def collect(self):
        try:
            with engine.begin() as db:
                db.execute(text("SET LOCAL statement_timeout = '2s'"))
                pending, oldest = db.execute(text("""
                    SELECT count(*), extract(epoch FROM now() - min(created_at))
                    FROM outbox_events WHERE status = 'PENDING'
                """)).one()
        except SQLAlchemyError:
            yield GaugeMetricFamily("taskflow_outbox_backlog_up", "Outbox backlog query status", value=0)
            return
        yield GaugeMetricFamily("taskflow_outbox_backlog_up", "Outbox backlog query status", value=1)
        yield GaugeMetricFamily("taskflow_outbox_pending", "Pending rows including delayed retries",
                                value=pending)
        yield GaugeMetricFamily("taskflow_outbox_oldest_pending_seconds", "Oldest pending row age",
                                value=max(0, oldest or 0))


def observe_publish(event, duration):
    DURATION.observe(duration)
    if event.attempt_count > 1:
        ITEMS.labels("retry").inc()
    if event.status == "PUBLISHED":
        ITEMS.labels("published").inc()
    else:
        ITEMS.labels("error").inc()


def observe_confirmation(event, confirmed_at):
    ITEMS.labels("confirmed").inc()
    LAG.observe(max(0, (confirmed_at - event.created_at).total_seconds()))


def start_metrics():
    REGISTRY.register(OutboxBacklog())
    start_http_server(9101)
