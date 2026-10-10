from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3e0a2dfec3e'
down_revision: Union[str, Sequence[str], None] = '8e95b1a2f819'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leagues', sa.Column('dark_mode_image_url', sa.String(), nullable=True))
    op.add_column('matches', sa.Column('streams', sa.JSON(), nullable=True))
    op.add_column('matches', sa.Column('tier', sa.String(length=10), nullable=True))
    op.add_column('matches', sa.Column('prizepool', sa.String(), nullable=True))
    op.add_column('teams', sa.Column('dark_mode_image_url', sa.String(), nullable=True))
    op.add_column('teams', sa.Column('location', sa.String(length=5), nullable=True))


def downgrade() -> None:
    op.drop_column('teams', 'location')
    op.drop_column('teams', 'dark_mode_image_url')
    op.drop_column('matches', 'prizepool')
    op.drop_column('matches', 'tier')
    op.drop_column('matches', 'streams')
    op.drop_column('leagues', 'dark_mode_image_url')
