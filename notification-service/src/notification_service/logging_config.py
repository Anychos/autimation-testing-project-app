import json
import logging
import sys

from notification_service.database import utcnow
from notification_service.settings import get_settings

logger = logging.getLogger("notification_service")


def configure_logging():
    logging.basicConfig(
        level=get_settings().log_level, format="%(message)s", stream=sys.stdout,
    )
    logging.getLogger("pika").setLevel(logging.CRITICAL)


def log(service: str, message: str, *, level: int = logging.INFO, **fields):
    logger.log(level, json.dumps({
        "timestamp": utcnow().isoformat(), "level": logging.getLevelName(level),
        "service": service, "message": message, **fields,
    }, default=str))
