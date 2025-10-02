from sqlalchemy.orm import configure_mappers
from app.db.model import Base


def validate_orm_classes():
    """Validate all registered ORM classes."""
    try:
        print("🔍 Running quick ORM validation check...")
        semver = Base.metadata.tables.get("semver")
        print(f"Found table: {semver}")
        print(f"Columns: {semver.columns}")
        # This will raise exceptions if there are mapping issues
        configure_mappers()
        print("✅ ORM class definitions are valid")
    except Exception as e:
        print(f"❌ ORM validation failed: {e}")
        raise e


# Usage
if __name__ == "__main__":
    validate_orm_classes()
