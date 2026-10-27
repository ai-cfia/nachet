"""Standard-library logging boundary for the copied provider implementations."""

import logging


class StorageLogger(logging.LoggerAdapter):
    def process(self, message, kwargs):
        # The backend logger accepts structured keyword fields. Keep that calling
        # convention without importing the backend's service/logging lifecycle.
        fields = {
            key: kwargs.pop(key)
            for key in list(kwargs)
            if key not in ("exc_info", "extra", "stack_info", "stacklevel")
        }
        if fields:
            message = f"{message} {fields}"
        return message, kwargs


class LogService:
    @staticmethod
    def get_logger() -> StorageLogger:
        return StorageLogger(logging.getLogger("mlops_blob"), {})
