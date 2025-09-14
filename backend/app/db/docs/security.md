# SQLAlchemy Security Guide

This guide outlines key security practices when using SQLAlchemy ORM to prevent SQL injection and other database security vulnerabilities.

## 1. Use ORM Methods (Safest)

**✅ Safe - ORM automatically parameterizes:**

```python
from sqlalchemy.orm import Session
from database import Users, Seed

# Safe - ORM methods
user = session.query(Users).filter(Users.email == user_email).first()
seeds = session.query(Seed).filter(Seed.family == family_name).all()

# Safe - ORM with multiple conditions
results = session.query(Seed).filter(
    Seed.family == family,
    Seed.genus == genus,
    Seed.active == True
).all()
```

## 2. Use Bound Parameters with Raw SQL

**✅ Safe - Bound parameters:**

```python
from sqlalchemy import text

# Safe - named parameters
result = session.execute(
    text("SELECT * FROM seed WHERE family = :family AND genus = :genus"),
    {"family": family_name, "genus": genus_name}
)

# Safe - positional parameters
result = session.execute(
    text("SELECT * FROM seed WHERE family = ? AND genus = ?"),
    (family_name, genus_name)
)
```

## 3. Avoid String Concatenation/Formatting

**❌ DANGEROUS - Never do this:**

```python
# NEVER DO THIS - SQL injection vulnerability
query = f"SELECT * FROM seed WHERE family = '{family_name}'"
result = session.execute(text(query))

# NEVER DO THIS either
query = "SELECT * FROM seed WHERE family = '%s'" % family_name
result = session.execute(text(query))
```

## 4. Validate Input Data

**Use Pydantic models for validation:**

```python
from pydantic import BaseModel, validator
from typing import Optional
import re

class SeedSearchRequest(BaseModel):
    family: str
    genus: Optional[str] = None
    
    @validator('family')
    def validate_family(cls, v):
        # Only allow alphanumeric and common characters
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError('Invalid family name format')
        if len(v) > 100:
            raise ValueError('Family name too long')
        return v

# In your API endpoint
def search_seeds(request: SeedSearchRequest, session: Session):
    return session.query(Seed).filter(
        Seed.family == request.family,
        Seed.genus == request.genus
    ).all()
```

## 5. Be Careful with Dynamic Queries

**✅ Safe dynamic queries:**

```python
def build_seed_query(session, filters: dict):
    query = session.query(Seed)
    
    # Safe - using ORM filter methods
    if 'family' in filters:
        query = query.filter(Seed.family == filters['family'])
    if 'genus' in filters:
        query = query.filter(Seed.genus == filters['genus'])
    if 'active' in filters:
        query = query.filter(Seed.active == filters['active'])
    
    return query.all()
```

**❌ Dangerous dynamic queries:**

```python
def bad_dynamic_query(session, column, value):
    # DANGEROUS - building SQL string directly
    query = f"SELECT * FROM seed WHERE {column} = '{value}'"
    return session.execute(text(query))
```

## 6. Special Cases - Column/Table Names

**When you need dynamic column/table names:**

```python
from sqlalchemy import column, table

# For dynamic column names, validate against whitelist
ALLOWED_COLUMNS = {'family', 'genus', 'species', 'name_code'}

def search_by_column(session, column_name: str, value: str):
    if column_name not in ALLOWED_COLUMNS:
        raise ValueError("Invalid column name")
    
    # Use getattr to safely access model attributes
    column_attr = getattr(Seed, column_name)
    return session.query(Seed).filter(column_attr == value).all()
```

## 7. Complex Queries with Subqueries

**✅ Safe subquery example:**

```python
# Safe - using ORM subquery
subquery = session.query(Object.picture_id).filter(
    Object.top_score > 0.8
).subquery()

high_confidence_pictures = session.query(Picture).filter(
    Picture.id.in_(session.query(subquery.c.picture_id))
).all()
```

## 8. Raw SQL When Necessary

**✅ When you must use raw SQL:**

```python
from sqlalchemy import text

def complex_analytics_query(session, user_id: str, start_date: datetime):
    # Always use bound parameters
    query = text("""
        SELECT 
            p.id,
            COUNT(o.id) as object_count,
            AVG(o.top_score) as avg_confidence
        FROM picture p
        JOIN object o ON p.id = o.picture_id
        WHERE p.user_id = :user_id 
        AND p.date_created >= :start_date
        GROUP BY p.id
        ORDER BY avg_confidence DESC
    """)
    
    return session.execute(query, {
        'user_id': user_id,
        'start_date': start_date
    }).fetchall()
```

## 9. Input Sanitization Helpers

**Create utility functions:**

```python
import re
from typing import Optional

def sanitize_text_input(value: str, max_length: int = 255) -> str:
    """Sanitize text input for database queries."""
    if not isinstance(value, str):
        raise ValueError("Input must be string")
    
    # Remove null bytes and control characters
    value = value.replace('\x00', '')
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    
    # Limit length
    if len(value) > max_length:
        raise ValueError(f"Input too long (max {max_length})")
    
    return value.strip()

def validate_uuid(value: str) -> bool:
    """Validate UUID format."""
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, value.lower()))
```

## 10. Testing for SQL Injection

**Create comprehensive tests:**

```python
import pytest

def test_sql_injection_attempts(session):
    # Test common injection payloads
    malicious_inputs = [
        "'; DROP TABLE seed; --",
        "' OR '1'='1",
        "'; INSERT INTO seed VALUES (...); --",
        "admin'/*",
        "' UNION SELECT * FROM users --"
    ]
    
    for malicious_input in malicious_inputs:
        # Should not cause injection - should treat as literal string
        result = session.query(Seed).filter(
            Seed.family == malicious_input
        ).all()
        
        # Should return empty result, not cause SQL error
        assert isinstance(result, list)
```

## Key Security Principles

### ✅ Do This

1. **Always use ORM methods when possible** - they automatically parameterize
2. **Use bound parameters** for any raw SQL
3. **Validate and sanitize input** before database operations
4. **Use whitelists** for dynamic column/table names
5. **Test with malicious input** to verify protection

### ❌ Never Do This

1. **Never concatenate user input** into SQL strings
2. **Never use string formatting** (`%`, `.format()`, f-strings) for SQL
3. **Never trust user input** without validation
4. **Never expose database errors** to end users
5. **Never use dynamic table/column names** without whitelisting

## Additional Security Measures

### Database-Level Protection

```sql
-- Use least privilege principles
GRANT SELECT, INSERT, UPDATE, DELETE ON seed TO application_user;
REVOKE ALL ON pg_catalog FROM application_user;

-- Enable query logging for suspicious patterns
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_min_duration_statement = 1000;
```

### Application-Level Protection

```python
# Use connection pooling with proper timeouts
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"connect_timeout": 10}
)
```

### Monitoring and Alerting

```python
import logging

# Log all database operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_query_execution(query, params=None):
    logger.info(f"Executing query: {query}")
    if params:
        logger.info(f"Parameters: {params}")
```

## Conclusion

The SQLAlchemy ORM provides excellent protection against SQL injection by default, but developers must remain vigilant when:

- Using raw SQL queries
- Building dynamic queries
- Handling user input
- Working with legacy code

By following these security practices, you can build robust applications that protect against common database vulnerabilities while maintaining the flexibility and power of SQLAlchemy.
