"""phase5 import pdf key on base_resumes"""

from collections.abc import Sequence

revision: str = "002_import_source_pdf_key"
down_revision: str | Sequence[str] | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op

    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql as pg

    op.add_column("base_resumes", sa.Column("import_source_pdf_key", sa.Text(), nullable=True))
    op.add_column(
        "base_resumes",
        sa.Column("import_user_profile", pg.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    from alembic import op

    op.drop_column("base_resumes", "import_user_profile")
    op.drop_column("base_resumes", "import_source_pdf_key")
