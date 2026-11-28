#!/bin/sh
set -eu
case "$(printf '%s' "$METRICS_ENABLED" | tr '[:upper:]' '[:lower:]')" in
    1|on|t|true|y|yes)
        PROMETHEUS_MULTIPROC_DIR=$(mktemp -d /tmp/taskflow-metrics.XXXXXX)
        export PROMETHEUS_MULTIPROC_DIR
        ;;
esac
exec gunicorn app.main:app -c python:app.gunicorn_metrics \
    -k uvicorn.workers.UvicornWorker --workers "$BACKEND_WORKERS" \
    --access-logfile - --bind 0.0.0.0:8000
