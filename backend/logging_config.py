import os
import json
from contextvars import ContextVar
from typing import Optional
from loguru import logger
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

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

def json_formatter(record):
    """Custom JSON formatter for structured logging"""
    # Base log record
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "service": "nachet-backend",
        "file": record["file"].name,
        "function": record["function"],
        "line": record["line"]
    }
    
    if get_correlation_id():
        log_entry["correlation_id"] = get_correlation_id()
    if get_session_id():
        log_entry["session_id"] = get_session_id()
    if get_user_id():
        log_entry["user_id"] = get_user_id()
    
    # Add extra fields from the record
    if "extra" in record:
        log_entry.update(record["extra"])
    
    return json.dumps(log_entry)

def setup_logging():
    """Setup logging configuration with OTEL and console output"""
    
    # Remove default loguru handler
    logger.remove()
    
    # Console logging for development
    logger.add(
        sink=lambda msg: print(msg, end=''),
        format=json_formatter,
        level="INFO"
    )
    
    # OTEL logging - always enabled
    # Determine which exporter to use (HTTP or GRPC)
    otel_protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").lower()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy.monitoring.svc.cluster.local:4317")
    
    if otel_protocol == "http":
        if not endpoint.endswith("/v1/logs"):
            endpoint = endpoint.rstrip("/") + "/v1/logs"
    
    # Setup OTEL logger provider
    logger_provider = LoggerProvider()
    
    # Create exporter
    otlp_exporter = OTLPLogExporter(
        endpoint=endpoint,
        insecure=True
    )
    
    # Add processor
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(otlp_exporter)
    )
    
    # Add OTEL handler to loguru
    otel_handler = LoggingHandler(logger_provider=logger_provider)
    logger.add(
        sink=otel_handler.emit,
        format=json_formatter,
        level="INFO"
    )
    
    logger.info("OTEL logging initialized", extra={
        "protocol": otel_protocol,
        "endpoint": endpoint
    })
    
    return logger

def get_logger():
    """Get configured logger instance"""
    return logger