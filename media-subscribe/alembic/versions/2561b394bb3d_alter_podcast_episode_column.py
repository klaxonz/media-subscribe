"""alter podcast episode column

Revision ID: 2561b394bb3d
Revises: 295f16898a2c
Create Date: 2024-11-24 17:07:26.253800

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2561b394bb3d'
down_revision = '295f16898a2c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('podcast_episodes', 'description',
               existing_type=mysql.VARCHAR(length=255),
               type_=sa.Text(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('podcast_episodes', 'description',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(length=255),
               existing_nullable=True)
    # ### end Alembic commands ###
