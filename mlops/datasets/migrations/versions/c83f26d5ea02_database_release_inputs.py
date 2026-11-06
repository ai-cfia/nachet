"""Store release inputs, membership and crop lineage as database entities.

Revision ID: c83f26d5ea02
Revises: a895d501ea01
"""

import sqlalchemy as sa
from alembic import op

revision = "c83f26d5ea02"
down_revision = "a895d501ea01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add draft preparation entities while preserving legacy release registrations."""
    schema = op.get_context().opts.get("version_table_schema")
    with op.batch_alter_table("dataset_release", schema=schema) as batch:
        batch.drop_constraint("ck_dataset_release_status", type_="check")
        batch.create_check_constraint(
            "ck_dataset_release_status", "status IN ('draft', 'staging', 'ready')"
        )
        batch.alter_column("request_sha256", existing_type=sa.String(64), nullable=True)
        batch.create_check_constraint(
            "ck_dataset_release_request",
            "status = 'draft' OR request_sha256 IS NOT NULL",
        )
        batch.add_column(
            sa.Column(
                "database_backed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.add_column(sa.Column("conversion_revision", sa.Text(), nullable=True))
        batch.add_column(sa.Column("conversion_settings", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("generate_crops", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("coco_attributes", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("coco_categories", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("coco_annotations", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("crop_recipe", sa.JSON(), nullable=True))
    parent = f"{schema}.dataset_release.id" if schema else "dataset_release.id"
    op.create_table(
        "dataset_membership",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("release_id", sa.Uuid(), sa.ForeignKey(parent), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("split", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.UniqueConstraint("release_id", "image_id", name="uq_membership_image"),
        sa.UniqueConstraint("release_id", "position", name="uq_membership_position"),
        sa.CheckConstraint(
            "split IN ('train', 'validation', 'test')", name="ck_membership_split"
        ),
        sa.CheckConstraint("length(sha256) = 64", name="ck_membership_hash"),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_membership_dimensions"),
        sa.CheckConstraint("size > 0", name="ck_membership_size"),
        schema=schema,
    )
    op.create_table(
        "dataset_crop",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("release_id", sa.Uuid(), sa.ForeignKey(parent), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("annotation_id", sa.Integer(), nullable=False),
        sa.Column("pixel_box", sa.JSON(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.UniqueConstraint("release_id", "annotation_id", name="uq_crop_annotation"),
        sa.UniqueConstraint("release_id", "position", name="uq_crop_position"),
        sa.CheckConstraint("size > 0", name="ck_crop_size"),
        schema=schema,
    )


def downgrade() -> None:
    """Remove preparation entities only when no database-backed releases would be lost."""
    schema = op.get_context().opts.get("version_table_schema")
    # Refuse to discard authoritative records or invalidate generated releases.
    if op.get_context().as_sql:
        raise RuntimeError(
            "Downgrade requires an online check for database-backed releases"
        )
    release = sa.table("dataset_release", sa.column("database_backed"), schema=schema)
    if op.get_bind().scalar(
        sa.select(sa.func.count())
        .select_from(release)
        .where(release.c.database_backed == sa.true())
    ):
        raise RuntimeError(
            "Cannot downgrade while database-backed releases exist; restore a pre-upgrade backup"
        )
    op.drop_table("dataset_crop", schema=schema)
    op.drop_table("dataset_membership", schema=schema)
    with op.batch_alter_table("dataset_release", schema=schema) as batch:
        batch.drop_constraint("ck_dataset_release_request", type_="check")
        for field in (
            "crop_recipe",
            "coco_annotations",
            "coco_categories",
            "coco_attributes",
            "generate_crops",
            "conversion_settings",
            "conversion_revision",
            "database_backed",
        ):
            batch.drop_column(field)
        batch.alter_column(
            "request_sha256", existing_type=sa.String(64), nullable=False
        )
        batch.drop_constraint("ck_dataset_release_status", type_="check")
        batch.create_check_constraint(
            "ck_dataset_release_status", "status IN ('staging', 'ready')"
        )
