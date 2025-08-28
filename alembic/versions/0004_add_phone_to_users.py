"""add phone to users"""
from alembic import op

revision = "0004_add_phone_to_users"
down_revision = "f4f775f37abe"

def upgrade():
    op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(32)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)')

def downgrade():
    op.execute('DROP INDEX IF EXISTS ix_users_phone')
    op.execute('ALTER TABLE users DROP COLUMN IF EXISTS phone')
