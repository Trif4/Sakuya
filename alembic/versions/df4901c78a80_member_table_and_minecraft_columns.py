"""Member table and Minecraft columns

Revision ID: df4901c78a80
Revises: e1a522588d35
Create Date: 2020-03-15 21:02:00.015372

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'df4901c78a80'
down_revision = 'e1a522588d35'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('members',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('guild_id', sa.Integer(), nullable=False),
    sa.Column('minecraft_username', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['guild_id'], ['guilds.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'guild_id')
    )
    op.add_column('guilds', sa.Column('minecraft_channel_id', sa.Integer(), nullable=True))
    op.add_column('guilds', sa.Column('minecraft_rcon_address', sa.Text(), nullable=True))
    op.add_column('guilds', sa.Column('minecraft_rcon_pass', sa.Text(), nullable=True))
    op.add_column('guilds', sa.Column('minecraft_role_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('guilds', 'minecraft_role_id')
    op.drop_column('guilds', 'minecraft_rcon_address')
    op.drop_column('guilds', 'minecraft_rcon_pass')
    op.drop_column('guilds', 'minecraft_channel_id')
    op.drop_table('members')
