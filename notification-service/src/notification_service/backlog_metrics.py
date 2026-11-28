from prometheus_client import REGISTRY
from prometheus_client.core import GaugeMetricFamily
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from notification_service.database import engine


class EmailBacklog:
    def describe(self):
        return ()

    def collect(self):
        try:
            with engine.begin() as db:
                db.execute(text("SET LOCAL statement_timeout = '2s'"))
                pending = db.scalar(text("""
                    SELECT count(*) FROM notification_deliveries
                    WHERE channel = 'EMAIL' AND status IN ('PENDING', 'RETRYING', 'PROCESSING')
                """))
        except SQLAlchemyError:
            yield GaugeMetricFamily(
                "taskflow_smtp_backlog_up", "SMTP backlog query status", value=0,
            )
            return
        yield GaugeMetricFamily("taskflow_smtp_backlog_up", "SMTP backlog query status", value=1)
        yield GaugeMetricFamily(
            "taskflow_smtp_pending", "Unfinished email deliveries", value=pending,
        )


def register_backlog():
    REGISTRY.register(EmailBacklog())
