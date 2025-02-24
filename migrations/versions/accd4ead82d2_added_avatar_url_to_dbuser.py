"""Added avatar_url to DBUser

Revision ID: accd4ead82d2
Revises: 
Create Date: 2024-12-26 13:13:53.964614

"""
from typing import Sequence, Union
import sqlmodel

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'accd4ead82d2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dbuser', sa.Column('avatar_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('dbuser', 'avatar_url')
    # ### end Alembic commands ###
