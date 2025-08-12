"""Initial SQLAlchemy migration for nachet_0.0.13 schema

Revision ID: 001
Revises: 
Create Date: 2025-08-12 03:04:00.000000

This migration creates the nachet_0.0.13 schema with SQLAlchemy models
corresponding to the existing nachet_0.0.12 database structure.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schema
    op.execute('CREATE SCHEMA IF NOT EXISTS "nachet_0.0.13"')
    
    # Create object_type table
    op.create_table('object_type',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('registration_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('default_set_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create picture_set table
    op.create_table('picture_set',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('picture_set', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('upload_date', sa.Date(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['nachet_0.0.13.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Add foreign key for users.default_set_id
    op.create_foreign_key(None, 'users', 'picture_set', ['default_set_id'], ['id'], source_schema='nachet_0.0.13', referent_schema='nachet_0.0.13')
    
    # Create picture table
    op.create_table('picture',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('picture', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('picture_set_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nb_obj', sa.Integer(), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('upload_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['picture_set_id'], ['nachet_0.0.13.picture_set.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create pipeline table
    op.create_table('pipeline',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create unique index for pipeline default
    op.create_index('nachet_0.0.13_pipeline_default', 'pipeline', ['is_default'], unique=True, schema='nachet_0.0.13', postgresql_where=sa.text('is_default = true'))
    
    # Create seed table
    op.create_table('seed',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('object_type_id', sa.Integer(), server_default=sa.text('1'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create task table
    op.create_table('task',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create inference table
    op.create_table('inference',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('inference', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('picture_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('upload_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feedback_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('update_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['feedback_user_id'], ['nachet_0.0.13.users.id'], ),
        sa.ForeignKeyConstraint(['picture_id'], ['nachet_0.0.13.picture.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['nachet_0.0.13.pipeline.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['nachet_0.0.13.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create model table
    op.create_table('model',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('endpoint_name', sa.Text(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('upload_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('active_version', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['nachet_0.0.13.task.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create picture_seed table
    op.create_table('picture_seed',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('picture_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seed_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('upload_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['picture_id'], ['nachet_0.0.13.picture.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seed_id'], ['nachet_0.0.13.seed.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create pipeline_default table
    op.create_table('pipeline_default',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['pipeline_id'], ['nachet_0.0.13.pipeline.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['nachet_0.0.13.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create model_version table
    op.create_table('model_version',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('upload_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['nachet_0.0.13.model.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Add foreign key for model.active_version
    op.create_foreign_key(None, 'model', 'model_version', ['active_version'], ['id'], source_schema='nachet_0.0.13', referent_schema='nachet_0.0.13', ondelete='SET NULL')
    
    # Create object table
    op.create_table('object',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('box_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('inference_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column('verified_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('valid', sa.Boolean(), nullable=True),
        sa.Column('top_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('upload_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('manual_detection', sa.Boolean(), nullable=False),
        sa.Column('update_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['inference_id'], ['nachet_0.0.13.inference.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['type_id'], ['nachet_0.0.13.object_type.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create pipeline_model table
    op.create_table('pipeline_model',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['nachet_0.0.13.model.id'], ),
        sa.ForeignKeyConstraint(['pipeline_id'], ['nachet_0.0.13.pipeline.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )
    
    # Create seed_obj table
    op.create_table('seed_obj',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('seed_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('object_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['object_id'], ['nachet_0.0.13.object.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seed_id'], ['nachet_0.0.13.seed.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='nachet_0.0.13'
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('seed_obj', schema='nachet_0.0.13')
    op.drop_table('pipeline_model', schema='nachet_0.0.13')
    op.drop_table('object', schema='nachet_0.0.13')
    op.drop_table('model_version', schema='nachet_0.0.13')
    op.drop_table('pipeline_default', schema='nachet_0.0.13')
    op.drop_table('picture_seed', schema='nachet_0.0.13')
    op.drop_table('model', schema='nachet_0.0.13')
    op.drop_table('inference', schema='nachet_0.0.13')
    op.drop_table('task', schema='nachet_0.0.13')
    op.drop_table('seed', schema='nachet_0.0.13')
    op.drop_table('pipeline', schema='nachet_0.0.13')
    op.drop_table('picture', schema='nachet_0.0.13')
    op.drop_table('picture_set', schema='nachet_0.0.13')
    op.drop_table('users', schema='nachet_0.0.13')
    op.drop_table('object_type', schema='nachet_0.0.13')
    
    # Drop schema
    op.execute('DROP SCHEMA IF EXISTS "nachet_0.0.13"')