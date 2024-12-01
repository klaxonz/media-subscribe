"""add podcast table

Revision ID: 295f16898a2c
Revises: d87e0a7a650a
Create Date: 2024-11-24 16:18:35.562140

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '295f16898a2c'
down_revision = 'd87e0a7a650a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('podcast_channels',
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('author', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('cover_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('rss_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('website_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('language', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('categories', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rss_url')
    )
    op.create_index(op.f('ix_podcast_channels_title'), 'podcast_channels', ['title'], unique=False)
    op.create_table('podcast_episodes',
    sa.Column('channel_id', sa.Integer(), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('audio_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.Column('cover_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('last_position', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['podcast_channels.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_podcast_episodes_title'), 'podcast_episodes', ['title'], unique=False)
    op.create_table('podcast_subscriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['podcast_channels.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('podcast_subscriptions')
    op.drop_index(op.f('ix_podcast_episodes_title'), table_name='podcast_episodes')
    op.drop_table('podcast_episodes')
    op.drop_index(op.f('ix_podcast_channels_title'), table_name='podcast_channels')
    op.drop_table('podcast_channels')
    # ### end Alembic commands ###