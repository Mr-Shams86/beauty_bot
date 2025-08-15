"""create appointments table

Revision ID: 0001
Revises:
Create Date: 2025-08-12 00:00:00
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, index=True, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("service", sa.Text, nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), index=True, nullable=False),
        sa.Column("status", sa.String(32), index=True, nullable=False, server_default="Ожидание"),
        sa.Column("event_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    # составной индекс (по желанию)
    op.create_index("ix_appointments_user_date", "appointments", ["user_id", "date"])

def downgrade() -> None:
    op.drop_index("ix_appointments_user_date", table_name="appointments")
    op.drop_table("appointments")
