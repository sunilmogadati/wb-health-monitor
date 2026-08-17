"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

EVERY MIGRATION IN THIS HISTORY MUST REVERSE. `downgrade()` is not optional and must not be left as
`pass`: the round trip from empty is asserted by CI, not by review. A migration that applies and
cannot reverse fails the build.

SET `down_revision` TO THE CURRENT HEAD at the time this revision is authored. There is exactly one
history and exactly one head at all times. Two branches each generating a revision from the same
parent produce two heads; the gate fails the build rather than letting it surface at deployment.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
