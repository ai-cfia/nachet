from sqlalchemy.orm import configure_mappers
import traceback
from app.controller.db.database import Base  # Import your models

def validate_orm_classes():
    """Validate all registered ORM classes."""
    try:
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
