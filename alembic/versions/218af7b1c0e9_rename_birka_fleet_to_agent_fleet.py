"""rename_birka_fleet_to_agent_fleet

Revision ID: 218af7b1c0e9
Revises: 61f2b2393b09
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '218af7b1c0e9'
down_revision: Union[str, Sequence[str], None] = '61f2b2393b09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename birka_fleet table to agent_fleet."""
    op.rename_table('birka_fleet', 'agent_fleet')


def downgrade() -> None:
    """Rename agent_fleet table back to birka_fleet."""
    op.rename_table('agent_fleet', 'birka_fleet')
