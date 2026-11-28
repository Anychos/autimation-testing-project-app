from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from notification_service.events import EventType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    user_id: UUID
    event_type: EventType
    task_id: UUID | None
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    page: int
    page_size: int


class UnreadCount(BaseModel):
    count: int


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_id: UUID
    channel: Literal["IN_APP", "EMAIL"]
    recipient: str | None
    status: Literal["PENDING", "PROCESSING", "RETRYING", "SENT", "FAILED"]
    attempt_count: int
    next_attempt_at: datetime | None
    last_error: str | None
    created_at: datetime
    sent_at: datetime | None
    message_id: str | None


class HealthOut(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorDetail(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorOut(BaseModel):
    error: ErrorBody
