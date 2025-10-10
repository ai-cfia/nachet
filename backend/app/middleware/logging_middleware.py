"""
Logging middleware for FastAPI to log all API requests and responses.
"""

import time
from uuid6 import uuid7
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from app.service.logs import LogService


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests and outgoing responses.

    Features:
    - Generates or extracts correlation_id from X-Correlation-ID header (UUIDv7 for time-ordered tracing)
    - Extracts session_id from X-Session-ID header
    - Sets context variables for structured logging
    - Logs request start with method, path, and metadata
    - Logs response completion with status code and duration
    - Adds correlation_id to response headers
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._logger = None

    @property
    def logger(self):
        """Lazy load logger to ensure Settings are loaded first"""
        if self._logger is None:
            self._logger = LogService.get_logger()
        return self._logger

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get or generate correlation ID (using UUIDv7 for time-ordered IDs)
        correlation_id = request.headers.get('X-Correlation-ID') or request.headers.get('x-correlation-id') or str(uuid7())
        session_id = request.headers.get('X-Session-ID') or request.headers.get('x-session-id')

        # Store in request state for access in endpoints
        request.state.correlation_id = correlation_id
        request.state.session_id = session_id
        request.state.request_start_time = time.time()

        # Set context vars for logging
        LogService.set_correlation_id(correlation_id)
        if session_id:
            LogService.set_session_id(session_id)

        # Extract user ID from request state (set by auth middleware/dependency)
        if hasattr(request.state, 'user') and request.state.user:
            user_id = getattr(request.state.user, 'oid', None) or getattr(request.state.user, 'id', None)
            if user_id:
                LogService.set_user_id(str(user_id))

        # Log request start
        self.logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            remote_addr=request.client.host if request.client else None,
            user_agent=request.headers.get('User-Agent', ''),
            correlation_id=correlation_id,
            session_id=session_id
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - request.state.request_start_time

            # Log response
            self.logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                remote_addr=request.client.host if request.client else None,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                correlation_id=correlation_id,
                session_id=session_id
            )

            # Add correlation ID to response headers
            response.headers['X-Correlation-ID'] = correlation_id

            return response

        except Exception as error:
            # Log error
            duration = time.time() - request.state.request_start_time

            self.logger.error(
                f"Request failed: {str(error)}",
                error_type=type(error).__name__,
                error_message=str(error),
                correlation_id=correlation_id,
                path=request.url.path,
                method=request.method,
                remote_addr=request.client.host if request.client else None,
                session_id=session_id,
                duration_ms=round(duration * 1000, 2)
            )

            # Re-raise to let FastAPI's exception handlers deal with it
            raise
