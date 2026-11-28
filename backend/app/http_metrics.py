import os
from time import perf_counter

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from starlette.responses import Response

METHODS = frozenset("GET HEAD POST PUT PATCH DELETE OPTIONS TRACE CONNECT".split())
BUCKETS = (.005, .01, .025, .05, .1, .2, .3, .5, .75, 1, 2, 5, 10)
LABELS = ("method", "route", "status")
REQUESTS = Counter("taskflow_http_requests", "HTTP requests completed", LABELS)
LATENCY = Histogram("taskflow_http_request_duration_seconds", "HTTP response duration",
                    LABELS, buckets=BUCKETS)
IN_FLIGHT = Gauge("taskflow_http_in_flight", "Requests currently in progress",
                  ("method",), multiprocess_mode="livesum")
EXCEPTIONS = Counter("taskflow_http_unhandled_exceptions", "Exceptions propagated by the app",
                     ("method", "route"))
REQUEST_BYTES = Counter("taskflow_http_request_body_bytes", "Request body bytes read", LABELS)
RESPONSE_BYTES = Counter("taskflow_http_response_body_bytes", "Response body bytes sent", LABELS)


class HttpMetrics:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] in {
            "/metrics", "/health", "/health/ready", "/health/live",
        }:
            await self.app(scope, receive, send)
            return

        method = scope["method"] if scope["method"] in METHODS else "OTHER"
        status = 500
        request_bytes = response_bytes = 0
        started = perf_counter()
        finished = None
        failed = False

        async def count_receive():
            nonlocal request_bytes
            message = await receive()
            request_bytes += len(message.get("body", b""))
            return message

        async def count_send(message):
            nonlocal status, response_bytes, finished
            await send(message)
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body":
                response_bytes += len(message.get("body", b""))
                if not message.get("more_body"):
                    finished = perf_counter()

        with IN_FLIGHT.labels(method).track_inprogress():
            try:
                await self.app(scope, count_receive, count_send)
            except Exception:
                failed = True
                raise
            finally:
                route = getattr(scope.get("route"), "path", "__unmatched__")
                labels = (method, route, str(status))
                REQUESTS.labels(*labels).inc()
                LATENCY.labels(*labels).observe((finished or perf_counter()) - started)
                REQUEST_BYTES.labels(*labels).inc(request_bytes)
                RESPONSE_BYTES.labels(*labels).inc(response_bytes)
                if failed:
                    EXCEPTIONS.labels(method, route).inc()


def metrics():
    registry = REGISTRY
    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    return Response(generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST})


def instrument_http(app):
    app.add_middleware(HttpMetrics)
    app.add_api_route("/metrics", metrics, methods=["GET"], include_in_schema=False)
