"""Create notifications and per-channel deliveries."""

import sqlalchemy as sa
from alembic import op

revision = "0001_notifications"
down_revision = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_digest", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("task_id", sa.Uuid()),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_event_id", "notifications", ["event_id"], unique=True)
    for column in ("user_id", "task_id", "event_type", "created_at", "is_read"):
        op.create_index(f"ix_notifications_{column}", "notifications", [column])
    op.create_index("ix_notifications_user_order", "notifications", ["user_id", "created_at", "id"])

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("notification_id", sa.Uuid(), sa.ForeignKey("notifications.id"), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("recipient", sa.String(254)),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("message_id", sa.String(100)),
        sa.Column("lease_id", sa.Uuid()),
        sa.UniqueConstraint("notification_id", "channel", name="uq_delivery_notification_channel"),
        sa.CheckConstraint("channel IN ('IN_APP', 'EMAIL')", name="ck_delivery_channel"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'RETRYING', 'SENT', 'FAILED')",
            name="ck_delivery_status",
        ),
    )
    op.create_index(
        "ix_delivery_schedule", "notification_deliveries", ["channel", "status", "next_attempt_at"]
    )


def downgrade():
    op.drop_table("notification_deliveries")
    op.drop_table("notifications")
