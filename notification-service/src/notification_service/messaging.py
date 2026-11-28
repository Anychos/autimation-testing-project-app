from typing import get_args

import pika

from notification_service.events import EventType
from notification_service.settings import get_settings

EVENT_TYPES = get_args(EventType)
DLX = "notification.dlx"


def connect():
    settings = get_settings()
    return pika.BlockingConnection(pika.ConnectionParameters(
        host=settings.rabbitmq_host, port=settings.rabbitmq_port,
        virtual_host=settings.rabbitmq_vhost,
        credentials=pika.PlainCredentials(
            settings.rabbitmq_user, settings.rabbitmq_password.get_secret_value(),
        ),
        heartbeat=15, socket_timeout=3, stack_timeout=5, blocked_connection_timeout=5,
    ))


def declare_topology(channel):
    settings = get_settings()
    queue = settings.rabbitmq_queue
    exchange = settings.rabbitmq_exchange
    channel.exchange_declare(exchange, exchange_type="topic", durable=True)
    channel.queue_declare(queue, durable=True)
    for key in EVENT_TYPES:
        channel.queue_bind(queue, exchange, key)
    channel.exchange_declare(DLX, exchange_type="direct", durable=True)
    dlq = f"{queue}.dlq"
    channel.queue_declare(dlq, durable=True)
    channel.queue_bind(dlq, DLX, dlq)
    for seconds in settings.retry_intervals:
        channel.queue_declare(f"{queue}.retry.{seconds}s", durable=True, arguments={
            "x-queue-type": "quorum",
            "x-message-ttl": seconds * 1000,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": queue,
            "x-dead-letter-strategy": "at-least-once",
            "x-overflow": "reject-publish",
        })


def publish(channel, exchange, key, body, *, message_id=None, correlation_id=None, headers=None):
    channel.basic_publish(
        exchange, key, body, mandatory=True,
        properties=pika.BasicProperties(
            content_type="application/json", delivery_mode=2, message_id=message_id,
            correlation_id=correlation_id, headers=headers,
        ),
    )
