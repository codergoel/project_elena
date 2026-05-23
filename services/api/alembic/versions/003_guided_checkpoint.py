"""phase6 guided intake checkpoint JSON on base_resumes"""

from collections.abc import Sequence

revision: str = "003_guided_checkpoint"
down_revision: str | Sequence[str] | None = "002_import_source_pdf_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op

    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql as pg

    op.add_column(
        "base_resumes",
        sa.Column("guided_checkpoint", pg.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    from alembic import op

    op.drop_column("base_resumes", "guided_checkpoint")
