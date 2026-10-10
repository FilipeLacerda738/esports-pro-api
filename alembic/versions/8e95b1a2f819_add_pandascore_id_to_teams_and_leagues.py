from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8e95b1a2f819'
down_revision: Union[str, Sequence[str], None] = 'b746d7e4d267'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leagues', sa.Column('pandascore_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_leagues_pandascore_id'), 'leagues', ['pandascore_id'], unique=True)
    op.add_column('teams', sa.Column('pandascore_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_teams_pandascore_id'), 'teams', ['pandascore_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_teams_pandascore_id'), table_name='teams')
    op.drop_column('teams', 'pandascore_id')
    op.drop_index(op.f('ix_leagues_pandascore_id'), table_name='leagues')
    op.drop_column('leagues', 'pandascore_id')
