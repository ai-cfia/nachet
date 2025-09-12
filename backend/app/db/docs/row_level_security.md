# Row Level Security (RLS) with SQLAlchemy ORM

This document outlines how to implement PostgreSQL Row Level Security with SQLAlchemy ORM for the Nachet application.

## Overview

Row Level Security (RLS) provides database-level access control that automatically filters rows based on the current user context. This ensures data isolation at the database level, preventing unauthorized access even if application logic has bugs.

## 1. Database Setup - Enable RLS

First, enable RLS on your tables and create policies:

```sql
-- Enable RLS on tables that need it
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE folder ENABLE ROW LEVEL SECURITY;
ALTER TABLE picture ENABLE ROW LEVEL SECURITY;
ALTER TABLE annotation ENABLE ROW LEVEL SECURITY;
ALTER TABLE object ENABLE ROW LEVEL SECURITY;

-- Create policies
-- Users can only see their own data
CREATE POLICY user_isolation_policy ON users
    FOR ALL TO application_role
    USING (id = current_setting('app.current_user_id')::uuid);

-- Folders: users see their own + org admin sees org folders
CREATE POLICY folder_access_policy ON folder
    FOR ALL TO application_role
    USING (
        user_id = current_setting('app.current_user_id')::uuid OR
        org_admin_id = current_setting('app.current_user_id')::uuid
    );

-- Pictures: follow folder access
CREATE POLICY picture_access_policy ON picture
    FOR ALL TO application_role
    USING (
        folder_id IN (
            SELECT id FROM folder 
            WHERE user_id = current_setting('app.current_user_id')::uuid
               OR org_admin_id = current_setting('app.current_user_id')::uuid
        )
    );
```

## 2. SQLAlchemy Session Context Manager

Create a context manager to set the current user:

```python
from contextlib import contextmanager
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Generator
import uuid

class RLSSession:
    def __init__(self, session: Session):
        self.session = session
        self.current_user_id: Optional[uuid.UUID] = None
        self.current_org_id: Optional[uuid.UUID] = None

    @contextmanager
    def user_context(self, user_id: uuid.UUID, org_id: Optional[uuid.UUID] = None) -> Generator[Session, None, None]:
        """Set the current user context for RLS."""
        try:
            # Set PostgreSQL session variables for RLS
            self.session.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": str(user_id)}
            )
            
            if org_id:
                self.session.execute(
                    text("SELECT set_config('app.current_org_id', :org_id, true)"),
                    {"org_id": str(org_id)}
                )
            
            self.current_user_id = user_id
            self.current_org_id = org_id
            
            yield self.session
            
        finally:
            # Clean up session variables
            self.session.execute(
                text("SELECT set_config('app.current_user_id', null, true)")
            )
            if org_id:
                self.session.execute(
                    text("SELECT set_config('app.current_org_id', null, true)")
                )
            
            self.current_user_id = None
            self.current_org_id = None
```

## 3. Database Service Layer

Create a service layer that enforces RLS:

```python
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from database import Users, Folder, Picture, Annotation

class DatabaseService:
    def __init__(self, session: Session):
        self.rls_session = RLSSession(session)
    
    def get_user_folders(self, user_id: UUID) -> List[Folder]:
        """Get folders accessible to user (enforced by RLS)."""
        with self.rls_session.user_context(user_id) as session:
            return session.query(Folder).all()  # RLS automatically filters
    
    def get_user_pictures(self, user_id: UUID, folder_id: Optional[UUID] = None) -> List[Picture]:
        """Get pictures accessible to user."""
        with self.rls_session.user_context(user_id) as session:
            query = session.query(Picture)
            if folder_id:
                query = query.filter(Picture.folder_id == folder_id)
            return query.all()  # RLS enforces access control
    
    def create_picture(self, user_id: UUID, folder_id: UUID, **kwargs) -> Picture:
        """Create picture with automatic user context."""
        with self.rls_session.user_context(user_id) as session:
            # Verify user can access this folder (RLS will enforce)
            folder = session.query(Folder).filter(Folder.id == folder_id).first()
            if not folder:
                raise PermissionError("Cannot access folder")
            
            picture = Picture(
                folder_id=folder_id,
                user_id=user_id,
                **kwargs
            )
            session.add(picture)
            session.commit()
            return picture
```

## 4. Advanced RLS Policies

More sophisticated policies based on your schema:

```sql
-- Organization-based isolation
CREATE POLICY org_isolation_policy ON users
    FOR ALL TO application_role
    USING (
        organization = current_setting('app.current_org_id')::uuid OR
        id = current_setting('app.current_user_id')::uuid
    );

-- RBAC-aware policies
CREATE POLICY rbac_folder_policy ON folder
    FOR ALL TO application_role
    USING (
        user_id = current_setting('app.current_user_id')::uuid OR
        org_admin_id = current_setting('app.current_user_id')::uuid OR
        EXISTS (
            SELECT 1 FROM user_role_permissions urp
            WHERE urp.user_id = current_setting('app.current_user_id')::uuid
            AND urp.resource_name = 'folder'
            AND urp.permission_name IN ('read', 'admin')
        )
    );

-- Time-based access (for annotations)
CREATE POLICY annotation_time_policy ON annotation
    FOR SELECT TO application_role
    USING (
        user_id = current_setting('app.current_user_id')::uuid OR
        (date_created > CURRENT_DATE - INTERVAL '30 days' AND 
         picture_id IN (SELECT id FROM picture WHERE user_id = current_setting('app.current_user_id')::uuid))
    );
```

## 5. Middleware Integration

Integrate with your FastAPI application:

```python
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps
from typing import Callable, Any
import jwt

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """Extract user ID from JWT token."""
    try:
        # Decode JWT token
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = UUID(payload.get("sub"))
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_user_context(f: Callable) -> Callable:
    """Decorator to ensure user context is set for RLS."""
    @wraps(f)
    async def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Get user_id from dependency injection
        return await f(*args, **kwargs)
    return decorated_function

# In your route handlers
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/folders")
async def get_folders(current_user: UUID = Depends(get_current_user)):
    """Get folders accessible to the current user."""
    with get_db_session() as session:
        db_service = DatabaseService(session)
        folders = db_service.get_user_folders(current_user)
        return [folder_to_dict(f) for f in folders]

@router.post("/api/folders/{folder_id}/pictures")
async def create_picture(
    folder_id: UUID,
    picture_data: dict,
    current_user: UUID = Depends(get_current_user)
):
    """Create a new picture in the specified folder."""
    with get_db_session() as session:
        db_service = DatabaseService(session)
        picture = db_service.create_picture(
            user_id=current_user,
            folder_id=folder_id,
            **picture_data
        )
        return picture_to_dict(picture)

# Alternative: Middleware approach
from fastapi import FastAPI
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class RLSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract user from token and store in request state
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                request.state.current_user_id = UUID(payload.get("sub"))
            except jwt.PyJWTError:
                pass
        
        response = await call_next(request)
        return response

# Add middleware to app
app = FastAPI()
app.add_middleware(RLSMiddleware)
```

## 6. Testing RLS

Create comprehensive tests:

```python
import pytest
from uuid import uuid4

def test_rls_user_isolation(db_session):
    """Test that users can only see their own data."""
    user1_id = uuid4()
    user2_id = uuid4()
    
    # Create test data for both users
    service = DatabaseService(db_session)
    
    # User 1 creates a folder
    with service.rls_session.user_context(user1_id):
        folder1 = Folder(user_id=user1_id, name="User 1 Folder")
        db_session.add(folder1)
        db_session.commit()
    
    # User 2 creates a folder
    with service.rls_session.user_context(user2_id):
        folder2 = Folder(user_id=user2_id, name="User 2 Folder")
        db_session.add(folder2)
        db_session.commit()
    
    # Test isolation
    user1_folders = service.get_user_folders(user1_id)
    user2_folders = service.get_user_folders(user2_id)
    
    assert len(user1_folders) == 1
    assert len(user2_folders) == 1
    assert user1_folders[0].id != user2_folders[0].id

def test_rls_org_admin_access(db_session):
    """Test that org admins can see org data."""
    admin_id = uuid4()
    user_id = uuid4()
    org_id = uuid4()
    
    service = DatabaseService(db_session)
    
    # Create folder with org admin
    with service.rls_session.user_context(user_id):
        folder = Folder(
            user_id=user_id, 
            org_admin_id=admin_id,
            name="Org Folder"
        )
        db_session.add(folder)
        db_session.commit()
    
    # Admin should see the folder
    admin_folders = service.get_user_folders(admin_id)
    assert len(admin_folders) == 1
```

## 7. Performance Considerations

RLS policies can impact performance. Monitor and optimize:

```sql
-- Add indexes to support RLS policies
CREATE INDEX idx_folder_user_id ON folder(user_id);
CREATE INDEX idx_folder_org_admin_id ON folder(org_admin_id);
CREATE INDEX idx_picture_folder_user ON picture(folder_id, user_id);

-- Use EXPLAIN to analyze policy performance
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM folder 
WHERE name LIKE '%test%';
```

## 8. Migration Strategy

Add RLS to existing data:

```python
# Alembic migration
def upgrade():
    # Enable RLS
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE folder ENABLE ROW LEVEL SECURITY")
    
    # Create policies
    op.execute("""
        CREATE POLICY user_isolation_policy ON users
        FOR ALL TO application_role
        USING (id = current_setting('app.current_user_id')::uuid)
    """)

def downgrade():
    op.execute("DROP POLICY IF EXISTS user_isolation_policy ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
```

## Key Benefits

1. **Database-level security** - Cannot be bypassed by application bugs
2. **Automatic enforcement** - No need to remember to add WHERE clauses
3. **Performance** - Policies are optimized by PostgreSQL
4. **Compliance** - Strong isolation for regulatory requirements

## Important Notes

- RLS requires PostgreSQL (not available in SQLite)
- Always test policies thoroughly
- Monitor performance impact
- Use application roles, not superuser accounts
- Consider using connection pooling with role switching

## Implementation Checklist

- [ ] Enable RLS on required tables
- [ ] Create appropriate policies for each table
- [ ] Implement RLSSession context manager
- [ ] Create DatabaseService layer
- [ ] Add middleware integration
- [ ] Write comprehensive tests
- [ ] Add performance monitoring
- [ ] Create migration scripts
- [ ] Document policy changes

This approach provides robust, database-enforced multi-tenancy that integrates well with SQLAlchemy ORM patterns.
