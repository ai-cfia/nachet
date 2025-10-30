"""change_image_processing_state_primary_key_to_workflow_id

Revision ID: 3c39d84f1293
Revises: a0c6f0016e06
Create Date: 2025-10-30 06:17:16.777391

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c39d84f1293"
down_revision: Union[str, Sequence[str], None] = "a0c6f0016e06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Changes:
    1. Drop old primary key constraint on picture_id
    2. Make workflow_id NOT NULL (required for primary key)
    3. Add new primary key constraint on workflow_id
    4. Add index on picture_id (now a regular foreign key)
    """
    # Step 1: Drop old primary key constraint on picture_id
    op.drop_constraint(
        "image_processing_state_pkey", "image_processing_state", type_="primary"
    )

    # Step 2: Make workflow_id NOT NULL (required for primary key)
    op.alter_column(
        "image_processing_state",
        "workflow_id",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
        existing_comment="DBOS workflow UUID for image processing workflow (upload/scan/sanitize)",
    )

    # Step 3: Add new primary key constraint on workflow_id
    op.create_primary_key(
        "image_processing_state_pkey", "image_processing_state", ["workflow_id"]
    )

    # Step 4: Drop old workflow_id indexes (no longer needed since it's now primary key)
    op.drop_index(
        "idx_processing_state_workflow",
        table_name="image_processing_state",
        if_exists=True,
    )
    op.drop_index(
        "ix_image_processing_state_workflow_id",
        table_name="image_processing_state",
        if_exists=True,
    )

    # Step 5: Add index on picture_id for fast lookups
    op.create_index(
        "idx_processing_state_picture",
        "image_processing_state",
        ["picture_id"],
        unique=False,
    )
    op.create_index(
        "ix_image_processing_state_picture_id",
        "image_processing_state",
        ["picture_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema.

    Reverse the changes:
    1. Drop picture_id indexes
    2. Drop workflow_id primary key constraint
    3. Make workflow_id nullable again
    4. Add back primary key constraint on picture_id
    5. Re-create workflow_id indexes
    """
    # Step 1: Drop picture_id indexes
    op.drop_index(
        "ix_image_processing_state_picture_id",
        table_name="image_processing_state",
        if_exists=True,
    )
    op.drop_index(
        "idx_processing_state_picture",
        table_name="image_processing_state",
        if_exists=True,
    )

    # Step 2: Drop workflow_id primary key constraint
    op.drop_constraint(
        "image_processing_state_pkey", "image_processing_state", type_="primary"
    )

    # Step 3: Make workflow_id nullable again
    op.alter_column(
        "image_processing_state",
        "workflow_id",
        existing_type=sa.VARCHAR(length=255),
        nullable=True,
        existing_comment="DBOS workflow UUID for image processing workflow (upload/scan/sanitize)",
    )

    # Step 4: Add back primary key constraint on picture_id
    op.create_primary_key(
        "image_processing_state_pkey", "image_processing_state", ["picture_id"]
    )

    # Step 5: Re-create workflow_id indexes
    op.create_index(
        "ix_image_processing_state_workflow_id",
        "image_processing_state",
        ["workflow_id"],
        unique=False,
    )
    op.create_index(
        "idx_processing_state_workflow",
        "image_processing_state",
        ["workflow_id"],
        unique=False,
    )
