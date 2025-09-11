# Schema Drift Documentation

## How Drift Occurs

  Manual Changes:

- Someone runs CREATE TABLE directly in production
- Direct column additions/deletions via SQL
- Index changes outside of migrations
- Data type modifications

  Result: Alembic's migration state becomes out of sync with actual database schema.

## Detection Methods

  1. Alembic Compare (Built-in)

    Check for drift

    alembic check

    See differences

    alembic revision --autogenerate -m "detect_drift" --dry-run

  2. Schema Comparison Tools

    Custom drift detection script

    from sqlalchemy import create_engine, MetaData
    from alembic.migration import MigrationContext
    from alembic.autogenerate import compare_metadata

    def detect_drift():
        engine = create_engine(DATABASE_URL)

        # Current database schema
        db_metadata = MetaData()
        db_metadata.reflect(bind=engine)

        # Expected schema from models
        from database import Base
        model_metadata = Base.metadata

        # Compare
        context = MigrationContext.configure(engine.connect())
        diff = compare_metadata(context, model_metadata)

        if diff:
            print("DRIFT DETECTED:")
            for change in diff:
                print(f"  {change}")
        else:
            print("No drift detected")

## Prevention Strategies

  1. Access Controls

    - Restrict direct database access in production
    - Use migration-only database users for deployments
    - Require code review for all schema changes

  2. Automated Checks

    In CI/CD pipeline

    - name: Check for database drift
        run: |
        alembic check
        python detect_drift.py

  3. Database Change Monitoring

  -- PostgreSQL: Track DDL changes
  CREATE OR REPLACE FUNCTION log_ddl_changes()
  RETURNS event_trigger AS $$
  BEGIN
      INSERT INTO schema_change_log (
          event_type,
          object_name,
          command_tag,
          changed_at
      ) VALUES (
          tg_event,
          tg_object_identity,
          tg_tag,
          NOW()
      );
  END;
  $$ LANGUAGE plpgsql;

  CREATE EVENT TRIGGER ddl_logger
  ON ddl_command_end
  EXECUTE FUNCTION log_ddl_changes();

## Recovery from Drift

  1. Manual Reconciliation

  Generate migration to match current state
  alembic revision --autogenerate -m "reconcile_drift"

  Review the generated migration carefully
  Edit if needed, then apply
  alembic upgrade head

  2. Reset Migration State

  Mark current database as latest migration (dangerous!)
  alembic stamp head

  Then generate new migration from current state
  alembic revision --autogenerate -m "baseline_after_drift"

  3. Schema Rollback

  -- If manual change was recent, rollback the manual change
  DROP TABLE unwanted_manual_table;
  -- Then ensure migrations are in sync

## Best Practices

  1. Documentation

  In your models, document any manual changes needed
  class MyTable(Base):
      """
      MANUAL STEPS REQUIRED:
      - Run: CREATE INDEX CONCURRENTLY idx_name ON mytable(column);
      - Reason: Cannot create concurrent index in transaction
      """

  2. Migration Hooks

   In migration file
  def upgrade():
      # Normal migration
      op.create_table(...)

      # Check for drift before proceeding
      connection = op.get_bind()
      result = connection.execute(text(
          "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'unexpected_table'"
      ))
      if result.scalar() > 0:
          raise Exception("Unexpected table found! Manual intervention required.")

  3. Regular Audits

   Weekly drift check
  #!/bin/bash
  echo "Checking for database drift..."
  alembic check || {
      echo "DRIFT DETECTED - Manual review required"
      exit 1
  }

  The key is early detection and preventing direct database access in production environments.
  