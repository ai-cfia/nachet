"""Add descriptive metadata and reviewed COCO statistics to dataset releases.

Revision ID: b72e15c4d901
Revises: a895d501ea01
"""

import sqlalchemy as sa
from alembic import op

revision = "b72e15c4d901"
down_revision = "a895d501ea01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = op.get_context().opts.get("version_table_schema")
    # Nullable columns preserve existing immutable registrations without guessing
    # their content. New publications populate statistics from reviewed COCO.
    with op.batch_alter_table("dataset_release", schema=schema) as batch:
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("has_bounding_boxes", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("has_classes", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("num_classes", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("num_multi_object_images", sa.Integer(), nullable=True)
        )
        batch.add_column(
            sa.Column("num_single_object_images", sa.Integer(), nullable=True)
        )
        batch.add_column(sa.Column("dataset_cutoff_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("previous_version", sa.Text(), nullable=True))
        for field in (
            "num_classes",
            "num_multi_object_images",
            "num_single_object_images",
        ):
            batch.create_check_constraint(
                f"ck_dataset_release_{field}", f"{field} >= 0"
            )


def downgrade() -> None:
    schema = op.get_context().opts.get("version_table_schema")
    with op.batch_alter_table("dataset_release", schema=schema) as batch:
        for field in (
            "num_classes",
            "num_multi_object_images",
            "num_single_object_images",
        ):
            batch.drop_constraint(f"ck_dataset_release_{field}", type_="check")
        for field in (
            "previous_version",
            "dataset_cutoff_date",
            "num_single_object_images",
            "num_multi_object_images",
            "num_classes",
            "has_classes",
            "has_bounding_boxes",
            "description",
        ):
            batch.drop_column(field)
