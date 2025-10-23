from sqlalchemy.orm import configure_mappers
from app.db.model import Base
from app.service.logs import LogService


def validate_orm_classes(logger=None):
    """Validate all registered ORM classes."""
    try:
        if logger:
            logger.info("Running quick ORM validation check")
        model_task = Base.metadata.tables.get("model_task")
        if logger:
            logger.info("Found table", table=str(model_task))
            logger.info("Table columns", columns=str(model_task.columns))
        # This will raise exceptions if there are mapping issues
        configure_mappers()
        if logger:
            logger.info("ORM class definitions are valid")
    except Exception as e:
        if logger:
            logger.error(
                "ORM validation failed", error=str(e), error_type=type(e).__name__
            )
        raise e


# Usage
if __name__ == "__main__":
    # Initialize console-only logging for this script
    LogService.setup_console_only_logging("INFO")
    logger = LogService.get_logger()

    validate_orm_classes(logger=logger)
