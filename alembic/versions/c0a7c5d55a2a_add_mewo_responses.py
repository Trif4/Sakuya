"""add mewo responses

Revision ID: c0a7c5d55a2a
Revises: 014003bbe2a0
Create Date: 2021-11-05 21:16:44.029130

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0a7c5d55a2a'
down_revision = '014003bbe2a0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('guilds', sa.Column('mewo_enabled', sa.Boolean(), nullable=True))
    op.add_column('members', sa.Column('mewo_text', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('members', 'mewo_text')
    op.drop_column('guilds', 'mewo_enabled')
