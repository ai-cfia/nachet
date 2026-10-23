"""Register immutable reviewed dataset releases.

Revision ID: a895d501ea01
Revises: 030caf3bf366
"""

import sqlalchemy as sa
from alembic import op

revision = "a895d501ea01"
down_revision = "030caf3bf366"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_release",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("date_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("container", sa.Text(), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("manifest_key", sa.Text(), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_dataset_release_name_version"),
        sa.CheckConstraint(
            "status IN ('staging', 'ready')", name="ck_dataset_release_status"
        ),
        sa.CheckConstraint(
            "status != 'ready' OR manifest_sha256 IS NOT NULL",
            name="ck_dataset_release_ready_manifest",
        ),
    )


def downgrade() -> None:
    op.drop_table("dataset_release")
