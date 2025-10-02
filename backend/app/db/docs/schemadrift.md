# Database Schema Drift Management

This document outlines how database drift occurs with Alembic migrations and provides strategies for detection, prevention, and recovery.

## What is Schema Drift?

Schema drift occurs when the actual database schema diverges from the expected schema defined in your Alembic migrations and SQLAlchemy models. This creates inconsistencies that can lead to deployment failures, data corruption, or application errors.

## How Drift Occurs

### Manual Changes

- Someone runs `CREATE TABLE` directly in production
- Direct column additions/deletions via SQL
- Index changes outside of migrations
- Data type modifications
- Constraint additions or removals

### Result

Alembic's migration state becomes out of sync with actual database schema, causing:

- Migration failures during deployments
- Inconsistent environments (dev vs staging vs prod)
- Difficult rollbacks and troubleshooting

## Detection Methods

### 1. Alembic Built-in Compare

**Check for drift:**

```bash
alembic check
```

**See differences (dry-run):**

```bash
alembic revision --autogenerate -m "detect_drift" --dry-run
```

### 2. Custom Schema Comparison Tools

**Create a drift detection script:**

```python
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
        return True
    else:
        print("No drift detected")
        return False

if __name__ == "__main__":
    drift_detected = detect_drift()
    exit(1 if drift_detected else 0)
```

### 3. Automated Schema Monitoring

**PostgreSQL DDL change tracking:**

```sql
-- Create schema change log table
CREATE TABLE schema_change_log (
    id SERIAL PRIMARY KEY,
    event_type TEXT,
    object_name TEXT,
    command_tag TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT DEFAULT CURRENT_USER
);

-- Function to log DDL changes
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

-- Create event trigger
CREATE EVENT TRIGGER ddl_logger 
ON ddl_command_end 
EXECUTE FUNCTION log_ddl_changes();
```

## Prevention Strategies

### 1. Access Controls

- **Restrict direct database access** in production
- **Use migration-only database users** for deployments
- **Require code review** for all schema changes
- **Implement least privilege** access policies

### 2. Automated Checks

**Add to CI/CD pipeline:**

```yaml
# In .github/workflows/ci.yml or similar
- name: Check for database drift
  run: |
    alembic check
    python detect_drift.py
```

**Pre-deployment hook:**

```bash
#!/bin/bash
echo "Checking for database drift before deployment..."
alembic check || {
    echo "DRIFT DETECTED - Stopping deployment"
    echo "Please review and reconcile schema differences"
    exit 1
}
```

### 3. Environment Consistency

```python
# Environment-specific validation
def validate_environment_schema():
    """Ensure all environments have consistent schema."""
    environments = ['development', 'staging', 'production']
    schemas = {}
    
    for env in environments:
        engine = create_engine(get_database_url(env))
        metadata = MetaData()
        metadata.reflect(bind=engine)
        schemas[env] = metadata
    
    # Compare schemas between environments
    for env1, env2 in combinations(environments, 2):
        diff = compare_schemas(schemas[env1], schemas[env2])
        if diff:
            raise Exception(f"Schema drift detected between {env1} and {env2}")
```

## Recovery from Drift

### 1. Manual Reconciliation (Recommended)

```bash
# Generate migration to match current state
alembic revision --autogenerate -m "reconcile_drift"

# Review the generated migration carefully
# Edit if needed, then apply
alembic upgrade head
```

**Review checklist for generated migrations:**

- Verify all changes are intentional
- Check for data loss operations (DROP COLUMN, etc.)
- Ensure indexes and constraints are correct
- Test on staging environment first

### 2. Reset Migration State (Dangerous)

```bash
# Mark current database as latest migration (USE WITH CAUTION!)
alembic stamp head

# Then generate new migration from current state
alembic revision --autogenerate -m "baseline_after_drift"
```

**⚠️ Warning:** This approach loses migration history and should only be used as a last resort.

### 3. Schema Rollback

```sql
-- If manual change was recent, rollback the manual change
DROP TABLE unwanted_manual_table;
ALTER TABLE mytable DROP COLUMN unwanted_column;

-- Then ensure migrations are in sync
```

## Best Practices

### 1. Documentation

**Document manual steps in model classes:**

```python
class MyTable(Base):
    """
    MANUAL STEPS REQUIRED:
    - Run: CREATE INDEX CONCURRENTLY idx_name ON mytable(column);
    - Reason: Cannot create concurrent index in transaction
    
    PRODUCTION NOTES:
    - This table requires special handling for large datasets
    - Coordinate with DBA team before schema changes
    """
    __tablename__ = "mytable"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    column: Mapped[str] = mapped_column(String(255), index=True)
```

### 2. Migration Hooks

**Add drift detection to migrations:**

```python
# In migration file
def upgrade():
    # Check for unexpected changes before proceeding
    connection = op.get_bind()
    
    # Check for unexpected tables
    result = connection.execute(text("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'unexpected_table' 
        AND table_schema = 'public'
    """))
    
    if result.scalar() > 0:
        raise Exception("Unexpected table found! Manual intervention required.")
    
    # Normal migration operations
    op.create_table(...)
    
    # Verify expected state after migration
    verify_schema_state(connection)

def verify_schema_state(connection):
    """Verify database is in expected state after migration."""
    # Add custom validation logic
    pass
```

### 3. Regular Audits

**Weekly drift check script:**

```bash
#!/bin/bash
# weekly_drift_check.sh

echo "=== Database Schema Drift Check ==="
echo "Date: $(date)"
echo "Environment: $ENV"

# Check for drift
echo "Checking for database drift..."
if ! alembic check; then
    echo "❌ DRIFT DETECTED - Manual review required"
    
    # Generate drift report
    alembic revision --autogenerate -m "drift_check_$(date +%Y%m%d)" --dry-run > drift_report.txt
    
    echo "Drift report generated: drift_report.txt"
    echo "Please review and take appropriate action"
    
    # Notify team (Slack, email, etc.)
    notify_team "Database drift detected in $ENV"
    
    exit 1
else
    echo "✅ No drift detected"
    exit 0
fi
```

### 4. Staging Environment Testing

```python
def test_migration_on_staging():
    """Test migrations on staging before production."""
    # Create staging database copy
    staging_engine = create_engine(STAGING_DATABASE_URL)
    
    # Apply migration
    alembic.command.upgrade(alembic_cfg, "head")
    
    # Verify schema integrity
    verify_schema_integrity(staging_engine)
    
    # Run application tests
    run_integration_tests()
    
    print("✅ Migration tested successfully on staging")
```

## Monitoring and Alerting

### Database Change Alerts

```python
import logging
from sqlalchemy import event

# Log all DDL operations
@event.listens_for(engine, "before_cursor_execute")
def log_ddl_operations(conn, cursor, statement, parameters, context, executemany):
    if any(keyword in statement.upper() for keyword in ['CREATE', 'ALTER', 'DROP']):
        logging.warning(f"DDL Operation: {statement}")
        # Send alert to monitoring system
        send_alert(f"DDL executed: {statement[:100]}...")
```

### Schema Drift Dashboard

```python
def create_drift_dashboard():
    """Create monitoring dashboard for schema drift."""
    return {
        'last_check': datetime.now(),
        'drift_status': 'clean',  # 'clean', 'drift_detected', 'error'
        'environments': {
            'development': check_environment_drift('dev'),
            'staging': check_environment_drift('staging'),
            'production': check_environment_drift('prod')
        },
        'recent_changes': get_recent_schema_changes()
    }
```

## Emergency Response Plan

### When Drift is Detected in Production

1. **Immediate Assessment**
   - Determine scope of drift
   - Assess impact on running application
   - Check if data integrity is affected

2. **Containment**
   - Prevent further manual changes
   - Document current state
   - Notify stakeholders

3. **Resolution**
   - Choose appropriate recovery strategy
   - Test fix in staging environment
   - Apply fix with proper backup procedures

4. **Post-Incident**
   - Conduct root cause analysis
   - Update prevention measures
   - Document lessons learned

## Conclusion

The key to managing schema drift is **early detection** and **preventing direct database access** in production environments. By implementing proper monitoring, access controls, and automated checks, you can maintain schema consistency across all environments while allowing for controlled, migration-based changes.

Remember: **All schema changes should go through the migration system** to maintain consistency and enable proper version control of your database schema.
