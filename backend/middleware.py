import uuid
import time
from quart import request, g
from logging_config import set_correlation_id, set_session_id, set_user_id, get_logger

logger = get_logger()

def setup_middleware(app):
    """Setup all middleware for the application"""
    
    @app.before_request
    async def before_request():
        # Get or generate correlation ID
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        session_id = request.headers.get('X-Session-ID')
        
        # Store in g for request context
        g.correlation_id = correlation_id
        g.session_id = session_id
        g.request_start_time = time.time()
        
        # Set context vars for logging
        set_correlation_id(correlation_id)
        if session_id:
            set_session_id(session_id)
        
        # Extract user ID from JWT if available
        if hasattr(g, 'user') and g.user:
            user_id = g.user.get('id')
            if user_id:
                set_user_id(str(user_id))
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', ''),
                "correlation_id": correlation_id,
                "session_id": session_id
            }
        )
    
    @app.after_request
    async def after_request(response):
        # Add correlation ID to response headers
        if hasattr(g, 'correlation_id'):
            response.headers['X-Correlation-ID'] = g.correlation_id
        
        # Log response
        if hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "correlation_id": getattr(g, 'correlation_id', None)
                }
            )
        
        return response
    
    @app.errorhandler(Exception)
    async def handle_exception(error):
        """Global error handler with logging"""
        correlation_id = getattr(g, 'correlation_id', str(uuid.uuid4()))
        
        logger.error(
            f"Unhandled exception: {str(error)}",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "correlation_id": correlation_id,
                "path": request.path,
                "method": request.method
            },
            exc_info=True
        )
        
        # Return generic error response
        return {
            "error": "Internal server error",
            "correlation_id": correlation_id
        }, 500
