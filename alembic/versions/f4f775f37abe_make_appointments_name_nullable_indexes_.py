"""make appointments.name nullable + indexes + seed services

Revision ID: f4f775f37abe
Revises: 0003
Create Date: 2025-08-20 22:12:23.960347
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4f775f37abe'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
