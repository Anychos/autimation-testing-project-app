"""Local data commands: python -m app.seed [seed|reset --confirm-local-reset]."""
import argparse
from datetime import date
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, select, text

from app.config import settings
from app.database import SessionLocal, engine
from app.models import AuthSession, Task, User
from app.security import passwords


def seed_data(db):
    examples = [
        ("Plan the week", "Choose a few things that matter this week.", "todo", date(2027, 1, 15)),
        ("Read the API documentation", "Explore the endpoints in Swagger UI.", "in_progress", date(2027, 1, 16)),
        ("Organize the workspace", "A little space for a fresh start.", "done", date(2026, 1, 10)),
        ("Review personal goals", "Reflect on progress and choose the next step.", "todo", None),
        ("Learn something new", "Take one small step every day.", "in_progress", date(2027, 2, 1)),
    ]
    for letter in ("a", "b"):
        email = f"user.{letter}@test.local"
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, password_hash=passwords.hash("Test12345!"))
            db.add(user)
            db.flush()
        for index, (title, description, status, due_date) in enumerate(examples):
            task_id = uuid5(NAMESPACE_URL, f"taskflow:seed:{email}:{index}")
            if db.get(Task, task_id) is None:
                db.add(Task(id=task_id, owner_id=user.id, title=title, description=description,
                            status=status, due_date=due_date))


def main():
    parser = argparse.ArgumentParser(description="TaskFlow local development data")
    parser.add_argument("command", choices=["seed", "reset"], nargs="?", default="seed")
    parser.add_argument("--confirm-local-reset", action="store_true")
    args = parser.parse_args()
    if settings.app_env != "development":
        parser.error("Seed/reset is only allowed with APP_ENV=development")
    if args.command == "reset" and not args.confirm_local_reset:
        parser.error("Reset deletes ALL users, sessions and tasks. Add --confirm-local-reset.")
    try:
        with SessionLocal.begin() as db:
            # Serialize local seed/reset commands to avoid duplicate inserts.
            db.execute(text("SELECT pg_advisory_xact_lock(73401921)"))
            if args.command == "reset":
                db.execute(delete(Task))
                db.execute(delete(AuthSession))
                db.execute(delete(User))
            seed_data(db)
        print("Local data ready: user.a@test.local and user.b@test.local, password Test12345!")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
