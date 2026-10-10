from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4e4093882f1'
down_revision: Union[str, Sequence[str], None] = '713f253cb786'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
