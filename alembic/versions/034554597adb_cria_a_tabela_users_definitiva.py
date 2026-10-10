from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '034554597adb'
down_revision: Union[str, Sequence[str], None] = 'a4e4093882f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
