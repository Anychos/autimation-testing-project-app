from datetime import timedelta
from typing import Annotated, Literal
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    field_validator,
)

EventType = Literal[
    "user.registered", "task.created", "task.updated", "task.completed", "task.deleted",
]
TaskStatus = Literal["todo", "in_progress", "done"]


def email_parts(value: str) -> tuple[str, str]:
    # TaskFlow accepts .test and seeded .local addresses.
    local_domain = value.lower().endswith(".local")
    candidate = value[:-6] + ".test" if local_domain else value
    try:
        address = validate_email(candidate, check_deliverability=False, test_environment=True)
    except EmailNotValidError as exc:
        raise ValueError("Invalid recipient address") from exc
    domain = address.ascii_domain
    if local_domain:
        domain = domain.removesuffix(".test") + ".local"
    return address.local_part, domain


def valid_email(value: str) -> str:
    email_parts(value)
    return value


Recipient = Annotated[
    str, StringConstraints(max_length=254), Field(json_schema_extra={"format": "email"}),
    AfterValidator(valid_email),
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RegistrationPayload(Contract):
    recipient_email: Recipient


class TaskPayload(Contract):
    task_id: UUID
    title: Annotated[
        str,
        StringConstraints(min_length=3, max_length=100, pattern=r"^[^\s\x00][^\x00]*[^\s\x00]$"),
    ]
    status: TaskStatus


class CreatedPayload(TaskPayload):
    recipient_email: Recipient


class UpdatedPayload(TaskPayload):
    pass


class CompletedPayload(TaskPayload):
    status: Literal["done"]
    recipient_email: Recipient


class DeletedPayload(TaskPayload):
    pass


class Envelope(Contract):
    event_id: UUID
    schema_version: Literal[1]
    occurred_at: AwareDatetime
    source: Literal["taskflow-backend"]
    correlation_id: UUID
    user_id: UUID

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Expected an integer schema version")
        return value

    @field_validator("occurred_at")
    @classmethod
    def utc_timestamp(cls, value):
        if value.utcoffset() != timedelta(0):
            raise ValueError("Expected a UTC timestamp")
        return value


class Registration(Envelope):
    event_type: Literal["user.registered"]
    payload: RegistrationPayload


class Created(Envelope):
    event_type: Literal["task.created"]
    payload: CreatedPayload


class Updated(Envelope):
    event_type: Literal["task.updated"]
    payload: UpdatedPayload


class Completed(Envelope):
    event_type: Literal["task.completed"]
    payload: CompletedPayload


class Deleted(Envelope):
    event_type: Literal["task.deleted"]
    payload: DeletedPayload


Event = Annotated[Registration | Created | Updated | Completed | Deleted,
                  Field(discriminator="event_type")]
event_adapter = TypeAdapter(Event)
