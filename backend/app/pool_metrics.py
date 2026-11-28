from time import perf_counter

from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import event
from sqlalchemy.exc import TimeoutError
from sqlalchemy.pool import QueuePool

ACQUIRE = Histogram("taskflow_db_pool_acquisition_seconds", "Time to acquire a DB connection",
                    buckets=(.001, .005, .01, .025, .05, .1, .25, .5, 1, 2, 5, 10, 30))
TIMEOUTS = Counter("taskflow_db_pool_timeouts", "Pool acquisition timeouts")
CHECKOUTS = Counter("taskflow_db_pool_checkouts", "Successful SQLAlchemy checkout events")
CHECKINS = Counter("taskflow_db_pool_checkins", "SQLAlchemy check-in events")
INVALIDATIONS = Counter("taskflow_db_pool_invalidations", "Hard connection invalidations")
CHECKED_OUT = Gauge("taskflow_db_pool_checked_out", "Checked-out pool slots",
                    multiprocess_mode="livesum")
CHECKED_IN = Gauge("taskflow_db_pool_checked_in", "Idle connections in the pool",
                   multiprocess_mode="livesum")
OVERFLOW = Gauge("taskflow_db_pool_overflow", "Connections above persistent pool size",
                 multiprocess_mode="livesum")
CAPACITY = Gauge("taskflow_db_pool_capacity", "Maximum connections in the backend pools",
                 multiprocess_mode="livesum")


class InstrumentedPool(QueuePool):
    def snapshot(self):
        CHECKED_OUT.set(self.checkedout())
        CHECKED_IN.set(self.checkedin())
        OVERFLOW.set(max(0, self.overflow()))

    def connect(self):
        started = perf_counter()
        try:
            return super().connect()
        except TimeoutError:
            TIMEOUTS.inc()
            raise
        finally:
            ACQUIRE.observe(perf_counter() - started)
            self.snapshot()

    def _return_conn(self, record):
        super()._return_conn(record)
        self.snapshot()


def instrument_pool(pool):
    from app.config import settings

    CAPACITY.set(settings.db_pool_size + settings.db_max_overflow)
    event.listen(pool, "checkout", lambda *_: CHECKOUTS.inc())
    event.listen(pool, "checkin", lambda *_: CHECKINS.inc())
    event.listen(pool, "invalidate", lambda *_: INVALIDATIONS.inc())
