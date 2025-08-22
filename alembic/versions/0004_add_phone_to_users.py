"""add phone to users"""
from alembic import op
import sqlalchemy as sa

revision = "0004_add_phone_to_users"
down_revision = "f4f775f37abe"  # <-- твоя последняя ревизия

def upgrade():
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))
    op.create_index("ix_users_phone", "users", ["phone"], unique=False)

def downgrade():
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_column("users", "phone")
