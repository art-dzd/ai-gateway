"""api_keys: добавить key_id для быстрого поиска ключа.

Revision ID: 0002_api_keys_key_id
Revises: 0001_init
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_api_keys_key_id"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("api_keys", sa.Column("key_id", sa.String(length=64), nullable=True))
    op.create_index("ix_api_keys_key_id", "api_keys", ["key_id"], unique=True)


def downgrade():
    op.drop_index("ix_api_keys_key_id", table_name="api_keys")
    op.drop_column("api_keys", "key_id")

