"""phase 5 product CSV imports

Revision ID: 20260812_04
Revises: 20260812_03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260812_04"
down_revision: str | None = "20260812_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

import_type = sa.Enum("PRODUCT_MASTER", name="csv_import_type")
import_status = sa.Enum("PROCESSING", "SUCCEEDED", "FAILED", name="csv_import_status")


def upgrade() -> None:
    op.create_table(
        "csv_import_jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("import_type", import_type, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("status", import_status, nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("success_rows", sa.Integer(), nullable=False),
        sa.Column("error_rows", sa.Integer(), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_csv_import_jobs_status", "csv_import_jobs", ["status"])
    op.create_index("ix_csv_import_jobs_accepted_at", "csv_import_jobs", ["accepted_at"])
    op.create_table(
        "csv_import_errors",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "csv_import_job_id",
            sa.BigInteger(),
            sa.ForeignKey("csv_import_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=50), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.String(length=200), nullable=False),
        sa.Column("input_value", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_csv_import_errors_csv_import_job_id",
        "csv_import_errors",
        ["csv_import_job_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_csv_import_errors_csv_import_job_id", table_name="csv_import_errors")
    op.drop_table("csv_import_errors")
    op.drop_index("ix_csv_import_jobs_accepted_at", table_name="csv_import_jobs")
    op.drop_index("ix_csv_import_jobs_status", table_name="csv_import_jobs")
    op.drop_table("csv_import_jobs")
    import_status.drop(op.get_bind(), checkfirst=True)
    import_type.drop(op.get_bind(), checkfirst=True)
