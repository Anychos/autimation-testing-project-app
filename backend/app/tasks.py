from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select

from app.errors import ApiError, ERROR_RESPONSES
from app.models import Task, utcnow
from app.outbox import log_committed, stage_task_event
from app.schemas import TaskCreate, TaskList, TaskOut, TaskPatch, TaskStatus
from app.security import CurrentSession, Db, require_csrf

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"], responses=ERROR_RESPONSES)


def owned_task(db, task_id, user_id, *, lock=False):
    query = select(Task).where(Task.id == task_id, Task.owner_id == user_id)
    task = db.scalar(query.with_for_update() if lock else query)
    if task is None:
        raise ApiError(404, "TASK_NOT_FOUND", "Task not found")
    return task


@router.post("", status_code=201, response_model=TaskOut, dependencies=[Depends(require_csrf)])
def create_task(body: TaskCreate, session: CurrentSession, db: Db, request: Request):
    task = Task(owner_id=session.user_id, **body.model_dump())
    db.add(task)
    event = stage_task_event(db, "task.created", task, request.state.correlation_id)
    db.commit()
    log_committed(event)
    return task


@router.get("", response_model=TaskList)
def list_tasks(session: CurrentSession, db: Db,
               status: TaskStatus | None = None, q: str | None = None,
               sort: Literal["created_desc", "created_asc", "due_date_asc"] = "created_desc",
               page: Annotated[int, Query(ge=1)] = 1,
               limit: Annotated[int, Query(ge=1, le=50)] = 10):
    filters = [Task.owner_id == session.user_id]
    if status is not None:
        filters.append(Task.status == status)
    if q is not None:
        # Escape LIKE wildcards so q is a literal substring.
        filters.append(Task.title.icontains(q, autoescape=True))
    total = db.scalar(select(func.count()).select_from(Task).where(*filters))
    order = {"created_desc": Task.created_at.desc(), "created_asc": Task.created_at.asc(),
             "due_date_asc": Task.due_date.asc().nulls_last()}[sort]
    items = db.scalars(select(Task).where(*filters).order_by(order, Task.id.asc())
                       .offset((page - 1) * limit).limit(limit)).all()
    return {"items": items, "pagination": {"page": page, "limit": limit,
            "total": total, "pages": (total + limit - 1) // limit}}


@router.get("/{id}", response_model=TaskOut)
def get_task(id: UUID, session: CurrentSession, db: Db):
    return owned_task(db, id, session.user_id)


@router.patch("/{id}", response_model=TaskOut, dependencies=[Depends(require_csrf)])
def patch_task(id: UUID, body: TaskPatch, session: CurrentSession, db: Db, request: Request):
    task = owned_task(db, id, session.user_id, lock=True)
    old_status = task.status
    changes = {field: value for field, value in body.model_dump(exclude_unset=True).items()
               if getattr(task, field) != value}
    for field, value in changes.items():
        setattr(task, field, value)
    task.updated_at = utcnow()
    event = None
    if changes:
        event_type = "task.completed" if old_status != "done" and task.status == "done" else "task.updated"
        event = stage_task_event(db, event_type, task, request.state.correlation_id)
    db.commit()
    log_committed(event)
    return task


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_csrf)])
def delete_task(id: UUID, session: CurrentSession, db: Db, request: Request):
    task = owned_task(db, id, session.user_id, lock=True)
    event = stage_task_event(db, "task.deleted", task, request.state.correlation_id)
    db.delete(task)
    db.commit()
    log_committed(event)
    return Response(status_code=204)
