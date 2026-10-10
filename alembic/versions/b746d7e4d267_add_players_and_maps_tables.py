from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b746d7e4d267'
down_revision: Union[str, Sequence[str], None] = '2693c19be894'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
