"""Register immutable reviewed dataset releases.

Revision ID: a895d501ea01
Standalone MLOps registry; independent of the backend Alembic history.
"""

import sqlalchemy as sa
from alembic import op

revision = "a895d501ea01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the release registry with metadata and publication integrity constraints."""
    schema = op.get_context().opts.get("version_table_schema")
    op.create_table(
        "dataset_release",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("has_bounding_boxes", sa.Boolean(), nullable=True),
        sa.Column("has_classes", sa.Boolean(), nullable=True),
        sa.Column("num_classes", sa.Integer(), nullable=True),
        sa.Column("num_multi_object_images", sa.Integer(), nullable=True),
        sa.Column("num_single_object_images", sa.Integer(), nullable=True),
        sa.Column("dataset_cutoff_date", sa.Date(), nullable=True),
        sa.Column("previous_version", sa.Text(), nullable=True),
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
        sa.CheckConstraint("num_classes >= 0", name="ck_dataset_release_num_classes"),
        sa.CheckConstraint(
            "num_multi_object_images >= 0",
            name="ck_dataset_release_num_multi_object_images",
        ),
        sa.CheckConstraint(
            "num_single_object_images >= 0",
            name="ck_dataset_release_num_single_object_images",
        ),
        schema=schema,
    )


def downgrade() -> None:
    """Drop the release registry table from the configured MLOps schema."""
    op.drop_table(
        "dataset_release", schema=op.get_context().opts.get("version_table_schema")
    )
