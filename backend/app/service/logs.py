"""
Log service module for processing frontend logs and managing logging infrastructure.
"""

import sys
import logging
from contextvars import ContextVar
from typing import Dict, Any, Optional
from loguru import logger
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as HTTPLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as GRPCLogExporter,
)

# Context variables for request tracing
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class LoguruToOTELBridge:
    """Bridge between Loguru and OpenTelemetry logging"""

    def __init__(self, otel_handler):
        self.otel_handler = otel_handler
        self.python_logger = logging.getLogger("nachet")
        self.python_logger.addHandler(otel_handler)
        self.python_logger.setLevel(logging.INFO)

        # Map loguru levels to Python logging levels
        self.level_map = {
            "TRACE": logging.DEBUG,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "SUCCESS": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

    def write(self, message):
        """Write loguru message to OTEL via standard Python logging"""
        if message.strip():
            record = message.record
            level = record["level"].name
            msg = record["message"]

            # Add context to extra
            extra = {
                "correlation_id": LogService.get_correlation_id(),
                "session_id": LogService.get_session_id(),
                "user_id": LogService.get_user_id(),
                "service": "nachet-backend",
                **record.get("extra", {}),
            }

            # Use service_name from record if present (e.g., frontend logs)
            if "service_name" not in extra:
                extra["service_name"] = "nachet-backend"

            self.python_logger.log(
                self.level_map.get(level, logging.INFO), msg, extra=extra
            )


class LogService:
    """
    Service class to handle logging infrastructure and frontend log processing.

    Manages:
    - Logging configuration with OTEL and console output
    - Context variables for correlation_id, session_id, user_id
    - Frontend log processing from HTTP requests
    """

    _initialized: bool = False
    _logger = None

    # Context variable management
    @staticmethod
    def get_correlation_id() -> Optional[str]:
        """Get current correlation ID from context"""
        return correlation_id_var.get()

    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        """Set correlation ID in context"""
        correlation_id_var.set(correlation_id)

    @staticmethod
    def get_session_id() -> Optional[str]:
        """Get current session ID from context"""
        return session_id_var.get()

    @staticmethod
    def set_session_id(session_id: str) -> None:
        """Set session ID in context"""
        session_id_var.set(session_id)

    @staticmethod
    def get_user_id() -> Optional[str]:
        """Get current user ID from context"""
        return user_id_var.get()

    @staticmethod
    def set_user_id(user_id: str) -> None:
        """Set user ID in context"""
        user_id_var.set(user_id)

    @staticmethod
    def _sanitize_error_message(error: Exception) -> str:
        """Sanitize error messages to prevent format string interpretation by the logger."""
        error_str = str(error)
        # Escape % characters to prevent logger from interpreting them as format placeholders
        return error_str.replace("%", "%%")

    @staticmethod
    def custom_formatter(record):
        """Custom formatter for adding context to log records"""
        record["extra"]["correlation_id"] = LogService.get_correlation_id()
        record["extra"]["session_id"] = LogService.get_session_id()
        record["extra"]["user_id"] = LogService.get_user_id()

        # Use service_name from extra if present (e.g., "nachet-frontend"), otherwise default to "nachet-backend"
        service = record["extra"].get("service_name", "nachet-backend")
        record["extra"]["service"] = service

        # Build base format
        base = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[service]} | {extra[correlation_id]}"

        # Add request details if available
        extra_info = []
        if "method" in record["extra"] and "path" in record["extra"]:
            extra_info.append(f"{record['extra']['method']} {record['extra']['path']}")

        if "remote_addr" in record["extra"] and record["extra"]["remote_addr"]:
            extra_info.append(f"from {record['extra']['remote_addr']}")

        if "status_code" in record["extra"]:
            extra_info.append(f"status={record['extra']['status_code']}")

        if "duration_ms" in record["extra"]:
            extra_info.append(f"{record['extra']['duration_ms']}ms")

        # Combine everything with message at the end
        if extra_info:
            return base + " | " + " ".join(extra_info) + " | {message}\n"
        else:
            return base + " | {message}\n"

    @classmethod
    def setup_console_only_logging(cls, log_level: str = "INFO"):
        """
        Setup simple console-only logging without OTEL.

        Use this for scripts, CLI tools, or standalone utilities that don't need
        full observability infrastructure.

        Args:
            log_level: Log level (INFO, DEBUG, WARNING, ERROR)

        Example:
            from app.service import LogService
            LogService.setup_console_only_logging("INFO")
            logger = LogService.get_logger()
        """
        if cls._initialized:
            logger.warning("Logging already initialized, skipping setup")
            return cls._logger

        log_level = log_level.upper()

        # Remove default loguru handler
        logger.remove()

        # Console logging only - no OTEL overhead
        logger.add(sys.stdout, format=cls.custom_formatter, level=log_level)

        logger.info(
            "Console-only logging initialized (OTEL disabled)", log_level=log_level
        )

        cls._initialized = True
        cls._logger = logger
        return logger

    @classmethod
    def setup_logging(cls, config: Optional[Dict[str, Any]] = None):
        """
        Setup logging configuration with optional OTEL support.

        Call this during application startup (in lifespan function).

        Args:
            config: Optional logging configuration dictionary with keys:
                - enable_otel: Enable/disable OTEL (default: True)
                - otel_exporter_protocol: "grpc" or "http"
                - otel_exporter_endpoint: OTEL endpoint URL
                - log_level: Log level (INFO, DEBUG, WARNING, ERROR)
        """
        if cls._initialized:
            logger.warning("Logging already initialized, skipping setup")
            return cls._logger

        # Use provided config or defaults
        if config is None:
            config = {}

        enable_otel = config.get("enable_otel", False)  # Disabled by default
        otel_protocol = config.get("otel_exporter_protocol", "grpc").lower()
        endpoint = config.get(
            "otel_exporter_endpoint", "http://alloy.monitoring.svc.cluster.local:4317"
        )
        log_level = config.get("log_level", "INFO").upper()

        # Remove default loguru handler
        logger.remove()

        # Console logging (always enabled)
        logger.add(sys.stdout, format=cls.custom_formatter, level=log_level)

        # OTEL logging setup (optional)
        if not enable_otel:
            logger.info(
                "OTEL disabled - using console-only logging", log_level=log_level
            )
            cls._initialized = True
            cls._logger = logger
            return logger

        # Try to set up OTEL, but gracefully degrade if it fails
        try:
            # OTEL logging setup
            if otel_protocol == "http":
                if not endpoint.endswith("/v1/logs"):
                    endpoint = endpoint.rstrip("/") + "/v1/logs"

            # Setup OTEL logger provider with service name
            resource = Resource(
                attributes={ResourceAttributes.SERVICE_NAME: "nachet-backend"}
            )
            logger_provider = LoggerProvider(resource=resource)

            # Create exporter based on protocol
            if otel_protocol == "http":
                otlp_exporter = HTTPLogExporter(endpoint=endpoint)
            else:
                otlp_exporter = GRPCLogExporter(endpoint=endpoint, insecure=True)

            # Add processor
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(otlp_exporter)
            )

            # Setup standard Python logging to forward to OTEL
            otel_handler = LoggingHandler(logger_provider=logger_provider)
            otel_handler.setLevel(getattr(logging, log_level, logging.INFO))

            # Add the bridge as a sink
            bridge = LoguruToOTELBridge(otel_handler)
            logger.add(bridge, level=log_level)

            logger.info(
                "OTEL logging initialized",
                protocol=otel_protocol,
                endpoint=endpoint,
                log_level=log_level,
            )

        except Exception as e:
            # OTEL setup failed - log warning and continue with console-only
            logger.warning(
                "OTEL setup failed - falling back to console-only logging",
                error=str(e),
                error_type=type(e).__name__,
                endpoint=endpoint,
            )

        cls._initialized = True
        cls._logger = logger
        return logger

    @classmethod
    def get_logger(cls):
        """Get configured logger instance"""
        if not cls._initialized:
            cls.setup_logging()
        return cls._logger or logger

    @classmethod
    async def process_frontend_log(cls, log_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Process and log frontend error/warning/info messages.

        Args:
            log_data: Dictionary containing:
                - level (str): Log level (ERROR, WARNING, INFO)
                - message (str): Log message
                - error_type (str, optional): Type of error
                - stack_trace (str, optional): Stack trace
                - url (str, optional): URL where error occurred
                - user_agent (str, optional): Browser user agent
                - user_id (str, optional): User ID (added by route)
                - correlation_id (str, optional): Request correlation ID
                - session_id (str, optional): User session ID

        Returns:
            Dictionary with status and correlation_id
        """
        try:
            log = cls.get_logger()

            # Extract log data with defaults
            level = log_data.get("level", "ERROR").upper()
            message = log_data.get("message", "Frontend log")
            error_type = log_data.get("error_type", "UnknownError")
            stack_trace = log_data.get("stack_trace", "")
            url = log_data.get("url", "")
            user_agent = log_data.get("user_agent", "")
            user_id = log_data.get("user_id", "")
            correlation_id = log_data.get("correlation_id")
            session_id = log_data.get("session_id")

            # Build extra context for structured logging
            extra_context = {
                "source": "frontend",
                "service_name": "nachet-frontend",  # Differentiate frontend logs in OTEL
                "error_type": error_type,
                "url": url,
                "user_agent": user_agent,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "session_id": session_id,
            }

            # Only add stack_trace to extra if it exists and isn't empty
            if stack_trace:
                extra_context["stack_trace"] = stack_trace

            # Log based on level using loguru
            if level == "ERROR":
                log.bind(**extra_context).error(f"Frontend error: {message}")
            elif level == "WARNING":
                log.bind(**extra_context).warning(f"Frontend warning: {message}")
            else:
                log.bind(**extra_context).info(f"Frontend log: {message}")

            return {"status": "logged", "correlation_id": correlation_id or "N/A"}

        except Exception as e:
            logger.error(
                f"Error processing frontend log: {cls._sanitize_error_message(e)}"
            )
            return {"status": "error", "error": "Failed to process log"}
