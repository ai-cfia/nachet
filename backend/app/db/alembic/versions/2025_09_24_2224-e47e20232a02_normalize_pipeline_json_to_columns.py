"""normalize_pipeline_json_to_columns

Revision ID: e47e20232a02
Revises: e63d0798d58d
Create Date: 2025-09-24 22:24:25.759712

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e47e20232a02"
down_revision: Union[str, Sequence[str], None] = "e63d0798d58d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to pipeline table
    op.add_column("pipeline", sa.Column("created_by", sa.Text(), nullable=True))
    op.add_column("pipeline", sa.Column("creation_date", sa.Date(), nullable=True))
    op.add_column("pipeline", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("pipeline", sa.Column("job_name", sa.Text(), nullable=True))
    op.add_column("pipeline", sa.Column("version", sa.Text(), nullable=True))
    op.add_column("pipeline", sa.Column("dataset", sa.Text(), nullable=True))
    op.add_column("pipeline", sa.Column("identifiable", sa.JSON(), nullable=True))
    op.add_column("pipeline", sa.Column("metrics", sa.JSON(), nullable=True))
    op.add_column(
        "pipeline", sa.Column("default", sa.Boolean(), nullable=True, default=False)
    )

    # Migrate existing data from JSON to new columns
    connection = op.get_bind()

    # Get all existing pipeline records
    result = connection.execute(
        sa.text("""
        SELECT id, data FROM pipeline WHERE data IS NOT NULL
    """)
    )

    for row in result:
        pipeline_id = row[0]
        data = row[1]

        # Extract values from JSON with safe defaults
        created_by = data.get("created_by", None) if data else None
        creation_date_str = data.get("creation_date", None) if data else None
        description = data.get("description", None) if data else None
        job_name = data.get("job_name", None) if data else None
        version = data.get("version", None) if data else None
        dataset = data.get("dataset", None) if data else None
        identifiable = data.get("identifiable", None) if data else None
        metrics = data.get("metrics", None) if data else None
        default = data.get("default", False) if data else False

        # Convert creation_date string to date if present
        creation_date = None
        if creation_date_str:
            try:
                from datetime import datetime

                creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                # If parsing fails, keep as None
                pass

        # Update the record with extracted values
        connection.execute(
            sa.text("""
            UPDATE pipeline
            SET created_by = :created_by,
                creation_date = :creation_date,
                description = :description,
                job_name = :job_name,
                version = :version,
                dataset = :dataset,
                identifiable = :identifiable,
                metrics = :metrics,
                "default" = :default
            WHERE id = :pipeline_id
        """),
            {
                "created_by": created_by,
                "creation_date": creation_date,
                "description": description,
                "job_name": job_name,
                "version": version,
                "dataset": dataset,
                "identifiable": identifiable,
                "metrics": metrics,
                "default": default,
                "pipeline_id": pipeline_id,
            },
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Migrate data back to JSON format before dropping columns
    connection = op.get_bind()

    result = connection.execute(
        sa.text("""
        SELECT id, created_by, creation_date, description, job_name, version,
               dataset, identifiable, metrics, "default", data
        FROM pipeline
    """)
    )

    for row in result:
        pipeline_id = row[0]

        # Build JSON object from column values
        json_data = {}

        # Get existing data field or start with empty dict
        existing_data = row[10] if row[10] else {}
        json_data.update(existing_data)

        # Add column values to JSON
        if row[1] is not None:  # created_by
            json_data["created_by"] = row[1]
        if row[2] is not None:  # creation_date
            json_data["creation_date"] = row[2].isoformat()
        if row[3] is not None:  # description
            json_data["description"] = row[3]
        if row[4] is not None:  # job_name
            json_data["job_name"] = row[4]
        if row[5] is not None:  # version
            json_data["version"] = row[5]
        if row[6] is not None:  # dataset
            json_data["dataset"] = row[6]
        if row[7] is not None:  # identifiable
            json_data["identifiable"] = row[7]
        if row[8] is not None:  # metrics
            json_data["metrics"] = row[8]
        if row[9] is not None:  # default
            json_data["default"] = row[9]

        # Update data field
        connection.execute(
            sa.text("""
            UPDATE pipeline SET data = :data WHERE id = :pipeline_id
        """),
            {"data": json_data, "pipeline_id": pipeline_id},
        )

    # Drop the new columns
    op.drop_column("pipeline", "default")
    op.drop_column("pipeline", "metrics")
    op.drop_column("pipeline", "identifiable")
    op.drop_column("pipeline", "dataset")
    op.drop_column("pipeline", "version")
    op.drop_column("pipeline", "job_name")
    op.drop_column("pipeline", "description")
    op.drop_column("pipeline", "creation_date")
    op.drop_column("pipeline", "created_by")
