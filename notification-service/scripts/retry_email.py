import argparse
from uuid import UUID

from sqlalchemy import update

from notification_service.database import SessionLocal, utcnow
from notification_service.models import Delivery


def main():
    parser = argparse.ArgumentParser(description="Requeue a FAILED email delivery by its UUID")
    parser.add_argument("delivery_id", type=UUID)
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        delivery_id = db.scalar(update(Delivery).where(
            Delivery.id == args.delivery_id,
            Delivery.channel == "EMAIL",
            Delivery.status == "FAILED",
        ).values(
            status="PENDING", attempt_count=0, next_attempt_at=utcnow(),
            last_error=None, lease_id=None,
        ).returning(Delivery.id))
    if delivery_id is None:
        parser.exit(1, "No FAILED email delivery with this ID\n")
    print(f"Requeued {delivery_id}")


if __name__ == "__main__":
    main()
