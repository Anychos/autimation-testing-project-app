"""Store Notification Service events in the business transaction."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_notification_outbox"
down_revision = "0001"


def upgrade():
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(255)),
        sa.CheckConstraint("status IN ('PENDING', 'PUBLISHED')", name="ck_outbox_status"),
    )
    op.create_index(
        "ix_outbox_pending_schedule", "outbox_events", ["status", "next_attempt_at", "created_at"],
    )


def downgrade():
    op.drop_table("outbox_events")
