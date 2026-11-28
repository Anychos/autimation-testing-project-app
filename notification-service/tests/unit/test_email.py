from uuid import uuid4

import pytest

from notification_service.database import utcnow
from notification_service.email_delivery import build_email
from notification_service.models import Delivery, Notification


@pytest.mark.parametrize("recipient", ["test@example.test", "тест@example.local"])
def test_email_has_diagnostic_headers_and_escapes_html(recipient):
    notification = Notification(
        id=uuid4(), event_id=uuid4(), correlation_id=uuid4(), task_id=uuid4(),
        title="New task created", message='Your task "<img src=x>" has been created.',
        event_occurred_at=utcnow(),
    )
    delivery = Delivery(recipient=recipient, message_id="<stable@taskflow.test>")
    email = build_email(delivery, notification)

    assert email["Subject"] == notification.title
    assert email["To"].addresses[0].addr_spec == recipient
    assert email["Message-ID"] == delivery.message_id
    assert email["X-Event-ID"] == str(notification.event_id)
    assert email["X-Correlation-ID"] == str(notification.correlation_id)
    assert email["X-Notification-ID"] == str(notification.id)
    assert email["X-Task-ID"] == str(notification.task_id)
    assert "<img src=x>" in email.get_body(("plain",)).get_content()
    assert "&lt;img src=x&gt;" in email.get_body(("html",)).get_content()
