"""Allow fill level 4 (overflowing) in bin_hist."""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_bin_hist_fill_level", "bin_hist", type_="check")
    op.create_check_constraint("ck_bin_hist_fill_level", "bin_hist", "fill_level BETWEEN 0 AND 4")


def downgrade() -> None:
    overflowing = op.get_bind().scalar(sa.text("SELECT count(*) FROM bin_hist WHERE fill_level = 4"))
    if overflowing:
        raise RuntimeError(
            f"Cannot restore the 0..3 fill range: {overflowing} bin_hist rows have fill_level 4"
        )
    op.drop_constraint("ck_bin_hist_fill_level", "bin_hist", type_="check")
    op.create_check_constraint("ck_bin_hist_fill_level", "bin_hist", "fill_level BETWEEN 0 AND 3")
