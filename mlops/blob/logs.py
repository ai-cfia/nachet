"""Use the same Loguru logger as the backend without importing its services."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger


class LogService:
    """Keep the copied providers' logging calls independent of application setup."""

    @staticmethod
    def get_logger() -> "Logger":
        """Return the process logger; the consuming application configures sinks."""
        return logger
