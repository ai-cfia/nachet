import os
import sys
import logging
from contextvars import ContextVar
from typing import Optional
from loguru import logger
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter as HTTPLogExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter as GRPCLogExporter

# env
OTEL_EXPORTER_PROTOCOL = "OTEL_EXPORTER_PROTOCOL"
OTEL_EXPORTER_ENDPOINT = "OTEL_EXPORTER_ENDPOINT"

# Correlation ID context variable
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context"""
    return correlation_id_var.get()

def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context"""
    correlation_id_var.set(correlation_id)

def get_session_id() -> Optional[str]:
    """Get current session ID from context"""
    return session_id_var.get()

def set_session_id(session_id: str) -> None:
    """Set session ID in context"""
    session_id_var.set(session_id)

def get_user_id() -> Optional[str]:
    """Get current user ID from context"""
    return user_id_var.get()

def set_user_id(user_id: str) -> None:
    """Set user ID in context"""
    user_id_var.set(user_id)

def custom_formatter(record):
    """Custom formatter for adding context to log records"""
    record["extra"]["correlation_id"] = get_correlation_id()
    record["extra"]["session_id"] = get_session_id()
    record["extra"]["user_id"] = get_user_id()
    record["extra"]["service"] = "nachet-backend"
    return "{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[service]} | {extra[correlation_id]} | {message}\n"


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
            "CRITICAL": logging.CRITICAL
        }
    
    def write(self, message):
        """Write loguru message to OTEL via standard Python logging"""
        if message.strip():
            record = message.record
            level = record["level"].name
            msg = record["message"]
            
            # Add context to extra
            extra = {
                "correlation_id": get_correlation_id(),
                "session_id": get_session_id(),
                "user_id": get_user_id(),
                "service": "nachet-backend",
                **record.get("extra", {})
            }
            
            self.python_logger.log(
                self.level_map.get(level, logging.INFO),
                msg,
                extra=extra
            )


def setup_logging():
    """Setup logging configuration with OTEL and console output"""
    
    # Remove default loguru handler
    logger.remove()
    
    # Console logging for development
    logger.add(
        sys.stdout,
        format=custom_formatter,
        level="INFO"
    )
    
    # OTEL logging setup
    otel_protocol = os.getenv(OTEL_EXPORTER_PROTOCOL, "grpc").lower()
    endpoint = os.getenv(OTEL_EXPORTER_ENDPOINT, "http://alloy.monitoring.svc.cluster.local:4317")
    
    if otel_protocol == "http":
        if not endpoint.endswith("/v1/logs"):
            endpoint = endpoint.rstrip("/") + "/v1/logs"
    
    # Setup OTEL logger provider
    logger_provider = LoggerProvider()
    
    # Create exporter based on protocol
    if otel_protocol == "http":
        otlp_exporter = HTTPLogExporter(
            endpoint=endpoint,
            insecure=True
        )
    else:
        otlp_exporter = GRPCLogExporter(
            endpoint=endpoint,
            insecure=True
        )
    
    # Add processor
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(otlp_exporter)
    )
    
    # Setup standard Python logging to forward to OTEL
    otel_handler = LoggingHandler(logger_provider=logger_provider)
    otel_handler.setLevel(logging.INFO)
    
    # Add the bridge as a sink
    bridge = LoguruToOTELBridge(otel_handler)
    logger.add(bridge, level="INFO")
    
    logger.info("OTEL logging initialized", protocol=otel_protocol, endpoint=endpoint)
    
    return logger

def get_logger():
    """Get configured logger instance"""
    return logger
