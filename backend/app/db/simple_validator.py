from sqlalchemy.orm import configure_mappers
import traceback
from app.db.model import Base


def validate_orm_classes():
    """Validate all registered ORM classes."""
    try:
        schema_version = Base.metadata.tables.get("schema_version")
        print(f"Found table: {schema_version}")
        print(f"Columns: {schema_version.columns}")
        # This will raise exceptions if there are mapping issues
        configure_mappers()
        print("✅ All ORM classes are valid")
        return True
    except Exception as e:
        print(f"❌ ORM validation failed: {e}")
        traceback.print_exc()
        return False


# Usage
if __name__ == "__main__":
    is_valid = validate_orm_classes()
