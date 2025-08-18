"""add users and services tables, refactor appointments

Revision ID: 0002
Revises: 0001
Create Date: 2025-08-17
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger, unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "services",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("duration_min", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
    )

    # appointments: добавляем поля и убираем текстовое service
    op.add_column("appointments", sa.Column("service_id", sa.BigInteger, sa.ForeignKey("services.id"), nullable=True))
    op.add_column("appointments", sa.Column("duration_min", sa.Integer, nullable=True))

    # если хочешь — миграция данных из старого text service в services тут (опционально)

    op.drop_column("appointments", "service")


def downgrade() -> None:
    op.add_column("appointments", sa.Column("service", sa.Text, nullable=False))
    op.drop_column("appointments", "duration_min")
    op.drop_column("appointments", "service_id")
    op.drop_table("services")
    op.drop_table("users")
