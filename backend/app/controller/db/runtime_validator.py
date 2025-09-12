from app.controller.db.database import Base
from app.api.config import Settings
from sqlalchemy import create_engine, inspect

def get_table_names(engine):
    inspector = inspect(engine)
    return inspector.get_table_names()

def validate_orm_classes():
    """Validate all registered ORM classes."""
    try:
        # This will raise exceptions if there are mapping issues
        engine = create_engine(Settings().db_conn_info["url"])
        Base.metadata.create_all(engine)  # Accessing this attribute triggers mapper configuration
        print("✅ All ORM classes are valid")

        # print table list to confirm connection
        tables = get_table_names(engine)
        print(f"Tables in the database: {tables}")
        return True
    except Exception as e:
        print(f"❌ ORM validation failed: {e}")
        return False

if __name__ == "__main__":
    is_valid = validate_orm_classes()
