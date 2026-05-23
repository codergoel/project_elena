"""initial schema checkpoint 2_2"""

from collections.abc import Sequence

revision: str = "001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op

    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql as pg

    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("external_sub", sa.String(length=512), nullable=True),
        sa.Column("email", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_sub"),
    )

    op.create_table(
        "resume_documents",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("payload", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "forked_from_id",
            pg.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["forked_from_id"],
            ["resume_documents.id"],
            ondelete="SET NULL",
        ),
    )

    op.create_table(
        "sessions",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash"),
    )

    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"])

    op.create_table(
        "base_resumes",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "active_document_id",
            pg.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["active_document_id"], ["resume_documents.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_base_resumes_user_id", "base_resumes", ["user_id"])

    op.create_table(
        "variants",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("base_resume_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("jd_blob_key", sa.Text(), nullable=True),
        sa.Column(
            "forked_from_document_id",
            pg.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "active_document_id",
            pg.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["base_resume_id"], ["base_resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["forked_from_document_id"], ["resume_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["active_document_id"], ["resume_documents.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_variants_base_resume_id", "variants", ["base_resume_id"])

    op.create_table(
        "conversation_threads",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("langgraph_thread_id", sa.Text(), nullable=False),
        sa.Column("base_resume_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("variant_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["base_resume_id"], ["base_resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["variants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("langgraph_thread_id"),
        sa.CheckConstraint(
            "(base_resume_id IS NOT NULL AND variant_id IS NULL) OR "
            "(base_resume_id IS NULL AND variant_id IS NOT NULL)",
            name="ck_conversation_threads_xor_context",
        ),
    )


def downgrade() -> None:
    from alembic import op

    op.drop_table("conversation_threads")
    op.drop_index("ix_variants_base_resume_id", table_name="variants")
    op.drop_table("variants")
    op.drop_index("ix_base_resumes_user_id", table_name="base_resumes")
    op.drop_table("base_resumes")
    op.drop_index("ix_sessions_token_hash", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("resume_documents")
    op.drop_table("users")
