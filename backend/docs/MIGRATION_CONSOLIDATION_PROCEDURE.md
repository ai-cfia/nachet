# Alembic Migration Consolidation Procedure

**Status:** Standard Operating Procedure
**Date Created:** 2025-10-13
**Applies To:** All deployment environments (dev, staging, production)

## Purpose

Keep Alembic migration count manageable by periodically consolidating old migrations into a baseline. This prevents:

- Excessive migration files cluttering the repository
- Slow `alembic upgrade head` on fresh database deployments
- Complex migration dependency chains
- Difficult troubleshooting of schema evolution

## Policy

**Migration Retention Window:** Keep only the last **10-15 migrations** for rollback capability.

**Consolidation Frequency:**

- Quarterly (every 3 months)
- Or when migration count exceeds 15
- During planned maintenance windows

## When to Consolidate

### Prerequisites (ALL must be true)

✅ **All environments synchronized**

- Dev, staging, and production are on the latest migration
- Run `alembic current` in each environment to verify

✅ **Databases healthy**

- No ongoing schema issues
- No pending schema changes
- All foreign key constraints valid

✅ **Backups current**

- Full database backups completed within last 24 hours
- Backups tested and verified restorable
- Backup retention policy allows rollback to pre-consolidation state

✅ **No active deployments**

- No code deployments in progress
- No schema changes in flight
- Maintenance window scheduled

✅ **Team notification**

- All developers notified of consolidation
- No one working on schema changes during consolidation
- Code freeze on migration-related changes

## Consolidation Options

### Option 1: Archive Old Migrations (Recommended)

**Best for:** Most situations, preserves git history

**Process:**

1. Keep last 10 migrations active
2. Move older migrations to archive folder
3. Keep archived migrations in git history
4. Create new baseline migration

**Pros:**

- ✅ Safest approach
- ✅ Can recover old migrations from git if needed
- ✅ Maintains historical record

**Cons:**

- ⚠️ Archived migrations still in repo (but in archive folder)

### Option 2: Squash Migrations (Advanced)

**Best for:** Experienced teams, after several consolidations

**Process:**

1. Export schema at consolidation point
2. Create single consolidated migration
3. Delete old migrations entirely
4. Update alembic_version table

**Pros:**

- ✅ Cleanest result
- ✅ Smallest repo size

**Cons:**

- ⚠️ More complex
- ⚠️ Requires manual schema validation
- ⚠️ Loses detailed migration history

## Procedure: Archive Old Migrations (Option 1)

### Step 1: Verify Prerequisites

```bash
# Check current migration in each environment
alembic current

# Expected output: Latest migration revision
# Example: 5fa7cbc5d789 (head) - Issue 409 backend pipeline model
```

```bash
# List all migrations
alembic history

# Count migrations
ls -1 migrations/versions/*.py | wc -l
```

If count > 15, proceed with consolidation.

### Step 2: Identify Consolidation Point

**Determine which migrations to archive:**

```bash
# List migrations by date (oldest first)
ls -lt migrations/versions/*.py | tail -n 20

# Decide: Keep last 10, archive the rest
```

**Example:**

- Total migrations: 23
- Keep: Last 10 migrations (most recent)
- Archive: First 13 migrations (older)

### Step 3: Create Archive Directory

```bash
cd /home/p4r0d1m3pxz/work/nachet/backend/migrations/versions
mkdir -p archive
```

### Step 4: Archive Old Migrations

```bash
# Move old migrations to archive (adjust count as needed)
# This example archives all but the last 10 migrations

# List migrations to archive (verify before moving)
ls -t *.py | tail -n +11

# Move to archive
ls -t *.py | tail -n +11 | xargs -I {} mv {} archive/

# Verify
ls -1 *.py | wc -l  # Should be 10
ls -1 archive/*.py | wc -l  # Should be archived count
```

### Step 5: Create Baseline Migration

```bash
cd /home/p4r0d1m3pxz/work/nachet/backend

# Create new baseline migration from current schema
alembic revision --autogenerate -m "consolidated_baseline_v2"

# Review the generated migration
cat migrations/versions/<new_revision>_consolidated_baseline_v2.py
```

**Important:** The new baseline should be mostly empty (just tracking changes from archive point to now).

### Step 6: Test in Development

```bash
# Test rollback capability
alembic downgrade -1
alembic current  # Verify you went back one migration

# Test upgrade
alembic upgrade head
alembic current  # Verify you're at head

# Test fresh database deployment
# Create new test database
createdb nachet_consolidation_test

# Run all migrations on fresh DB
NACHET_DB_URL="postgresql://...nachet_consolidation_test..." alembic upgrade head

# Verify schema matches production
# Use schema comparison tools or manual verification
```

### Step 7: Commit and Tag

```bash
# Stage changes
git add migrations/versions/
git add migrations/versions/archive/

# Commit
git commit -m "chore: consolidate migrations to baseline v2

- Archived 13 old migrations
- Keep last 10 migrations for rollback
- Created consolidated baseline v2
- All environments on latest migration before consolidation

Consolidation Date: $(date -I)
Archived Migrations: $(ls -1 migrations/versions/archive/*.py | wc -l)
Active Migrations: $(ls -1 migrations/versions/*.py | grep -v __pycache__ | wc -l)"

# Tag the consolidation point
git tag -a migration-baseline-v2 -m "Migration consolidation baseline v2 - $(date -I)"

# Push
git push origin main
git push origin migration-baseline-v2
```

### Step 8: Update Documentation

Update this file with:

- Date of consolidation
- Number of migrations archived
- Current baseline version
- Any special notes

**Example:**

```markdown
## Consolidation History

### Baseline v2 - 2025-10-13
- Migrations archived: 13
- Migrations active: 10
- Git tag: migration-baseline-v2
- Notes: First consolidation after RBAC refactor
```

### Step 9: Deploy to Staging/Production

**No deployment needed!** The migrations have already been applied in production.

The consolidation only affects:

- Fresh database deployments (faster now)
- New developer onboarding (fewer migrations to understand)
- Git repository cleanliness

**Verify in each environment:**

```bash
alembic current  # Should still show same migration as before
```

## Procedure: Squash Migrations (Option 2)

⚠️ **Advanced - Use only if comfortable with Alembic internals**

### Step 1-2: Same as Option 1

### Step 3: Export Current Schema

```bash
# Dump schema from production database
pg_dump --schema-only --no-owner --no-acl \
  -h $DB_HOST -U $DB_USER -d $DB_NAME \
  -n $NACHET_SCHEMA > schema_baseline_v2.sql
```

### Step 4: Create Consolidated Migration

```bash
# Create empty migration
alembic revision -m "consolidated_baseline_v2"

# Manually edit migration to recreate schema
# This is complex - consider using Option 1 instead
```

### Step 5: Delete Old Migrations

```bash
# DANGER: This deletes migration history
rm migrations/versions/old_*.py

# Commit immediately
git commit -m "squash: consolidated migrations to baseline v2"
```

### Step 6: Update alembic_version Table

```sql
-- In production database
-- Update to new baseline revision
UPDATE alembic_version SET version_num = '<new_baseline_revision>';
```

### Step 7: Test Thoroughly

Test on fresh database, staging, and dev environments before production.

## Rollback Procedure

If consolidation causes issues:

### Rollback Step 1: Revert Code

```bash
# Revert the consolidation commit
git revert <consolidation-commit-hash>

# Or reset to tag before consolidation
git reset --hard migration-baseline-v1
```

### Rollback Step 2: Restore Migration Files

```bash
# Move migrations back from archive
cd migrations/versions
mv archive/*.py .
rmdir archive
```

### Rollback Step 3: Verify Environments

```bash
# Check each environment still works
alembic current
alembic upgrade head  # Should be no-op
```

### Rollback Step 4: Delete Baseline Migration

```bash
# Remove the baseline migration created during consolidation
rm migrations/versions/<baseline_revision>_consolidated_baseline_v2.py

git commit -m "rollback: revert migration consolidation"
git push origin main
```

## Safety Checklist

Before consolidation:

- [ ] All environments on same migration
- [ ] Fresh database backups completed
- [ ] Backups verified restorable
- [ ] Team notified of consolidation
- [ ] Code freeze on schema changes
- [ ] Maintenance window scheduled

During consolidation:

- [ ] Verified prerequisites met
- [ ] Identified consolidation point (keep last 10)
- [ ] Created archive directory
- [ ] Archived old migrations (verified count)
- [ ] Created baseline migration
- [ ] Tested rollback capability
- [ ] Tested fresh database deployment
- [ ] Committed and tagged in git

After consolidation:

- [ ] Verified all environments still work
- [ ] Fresh deployment tested
- [ ] Documentation updated
- [ ] Team notified of completion
- [ ] Monitoring for issues

## Troubleshooting

### Issue: Migrations out of sync after consolidation

**Symptoms:** Alembic reports "Can't locate revision" or "Multiple heads"

**Resolution:**

```bash
# Check current state
alembic heads
alembic branches

# Manually fix alembic_version table
# Update to correct revision
```

### Issue: Fresh database deployment fails

**Symptoms:** `alembic upgrade head` fails on new database

**Resolution:**

1. Check if baseline migration is missing
2. Verify all migrations present in correct order
3. Check for circular dependencies

### Issue: Can't roll back to archived migration

**Symptoms:** Need to rollback beyond retention window

**Resolution:**

1. Recover migration from git archive folder
2. Move back to active migrations folder
3. Run downgrade
4. Move back to archive after rollback complete

## Best Practices

1. **Always consolidate during maintenance windows**
   - Low traffic periods
   - Team available for support
   - Rollback plan ready

2. **Test consolidation in dev first**
   - Run full procedure in dev environment
   - Verify fresh deployments work
   - Test rollback procedure

3. **Keep git tags**
   - Tag each consolidation point
   - Enables easy rollback to known state
   - Documents consolidation history

4. **Document everything**
   - Update this procedure with learnings
   - Track consolidation dates
   - Note any environment-specific issues

5. **Communicate with team**
   - Announce before starting
   - Update during process
   - Confirm completion

## Consolidation History

### Baseline v1 - Initial Schema

- Date: System inception
- Migrations: All pre-baseline migrations
- Notes: Initial database schema

### Baseline v2 - TBD

- Date: (Pending first consolidation)
- Migrations archived: TBD
- Migrations active: TBD
- Git tag: TBD
- Notes: TBD

---

**Document Owner:** DevOps / Database Team
**Review Frequency:** After each consolidation
**Last Updated:** 2025-10-13
