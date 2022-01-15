"""Add Wordle channel

Revision ID: e503f105f0b8
Revises: 014003bbe2a0
Create Date: 2022-01-15 16:33:06.510966

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e503f105f0b8'
down_revision = '014003bbe2a0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('guilds', sa.Column('wordle_channel_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('guilds', 'wordle_channel_id')
