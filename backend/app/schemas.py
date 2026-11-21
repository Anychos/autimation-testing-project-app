from uuid import UUID
from datetime import date, datetime
from typing import Annotated, Literal
import re

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, BeforeValidator, field_validator, model_validator


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=64)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        try:
            value = value.strip()
            # .local is reserved for local networks and is required by the seed contract.
            local_domain = value.lower().endswith(".local")
            candidate = value[:-6] + ".test" if local_domain else value
            normalized = validate_email(candidate, check_deliverability=False,
                                        test_environment=True).normalized.lower()
            return normalized[:-5] + ".local" if local_domain else normalized
        except EmailNotValidError as exc:
            raise ValueError("Invalid email format") from exc


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str


class CsrfOut(BaseModel):
    csrf_token: str


TaskStatus = Literal["todo", "in_progress", "done"]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=100)]
Description = Annotated[str, StringConstraints(max_length=500)]


def date_only(value):
    if value is None or type(value) is date:
        return value
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Date must use YYYY-MM-DD")
    return value


DueDate = Annotated[date | None, BeforeValidator(date_only)]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title
    description: Description = ""
    status: TaskStatus = "todo"
    due_date: DueDate = None


class TaskPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Defaults permit omission; the non-null types reject explicit null.
    title: Title = Field(default=None)
    description: Description = Field(default=None)
    status: TaskStatus = Field(default=None)
    due_date: DueDate = None

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class TaskOut(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class TaskList(BaseModel):
    items: list[TaskOut]
    pagination: Pagination
