"""Remove Minecraft role

Revision ID: 014003bbe2a0
Revises: df4901c78a80
Create Date: 2020-03-15 22:19:37.547094

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014003bbe2a0'
down_revision = 'df4901c78a80'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('guilds', 'minecraft_role_id')


def downgrade():
    op.add_column('guilds', sa.Column('minecraft_role_id', sa.INTEGER(), nullable=True))
