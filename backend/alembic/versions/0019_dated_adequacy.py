"""Accept dated adequacy periods with explicit boolean completion."""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_adequacy_analysis", "container_adequacy_analyses", type_="check")
    op.create_check_constraint(
        "ck_adequacy_analysis", "container_adequacy_analyses",
        "jsonb_typeof(analysis) = 'object' AND "
        "analysis->>'id' IS NOT DISTINCT FROM id AND "
        "jsonb_typeof(analysis->'complete') IS NOT DISTINCT FROM 'boolean'",
    )


def downgrade() -> None:
    # The operator must remove dated rows before restoring the complete-only contract.
    op.drop_constraint("ck_adequacy_analysis", "container_adequacy_analyses", type_="check")
    op.create_check_constraint(
        "ck_adequacy_analysis", "container_adequacy_analyses",
        "jsonb_typeof(analysis) = 'object' AND "
        "analysis->>'id' IS NOT DISTINCT FROM id AND "
        "analysis->'complete' IS NOT DISTINCT FROM 'true'::jsonb",
    )
