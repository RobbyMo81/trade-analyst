"""Error handlers and exception management"""

import logging
import traceback
import functools
from typing import Any, Callable, Dict, Optional, Type, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Error information container"""
    error_id: str
    timestamp: datetime
    error_type: str
    message: str
    severity: ErrorSeverity
    context: Dict[str, Any]
    traceback: Optional[str] = None
    resolved: bool = False


class ErrorRegistry:
    """Registry for tracking and managing errors"""
    
    def __init__(self):
        self.errors = {}
        self.error_counts = {}
        self.max_errors = 1000
    
    def register_error(self, error_info: ErrorInfo):
        """Register a new error"""
        self.errors[error_info.error_id] = error_info
        
        # Update error counts
        error_type = error_info.error_type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Limit error storage
        if len(self.errors) > self.max_errors:
            # Remove oldest errors
            oldest_errors = sorted(self.errors.items(), key=lambda x: x[1].timestamp)
            for error_id, _ in oldest_errors[:100]:  # Remove 100 oldest
                del self.errors[error_id]
    
    def get_error(self, error_id: str) -> Optional[ErrorInfo]:
        """Get error by ID"""
        return self.errors.get(error_id)
    
    def get_recent_errors(self, limit: int = 50) -> List[ErrorInfo]:
        """Get recent errors"""
        sorted_errors = sorted(self.errors.values(), key=lambda x: x.timestamp, reverse=True)
        return sorted_errors[:limit]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = len(self.errors)
        
        if total_errors == 0:
            return {
                'total_errors': 0,
                'by_type': {},
                'by_severity': {},
                'resolved_count': 0
            }
        
        # Count by severity
        severity_counts = {}
        resolved_count = 0
        
        for error in self.errors.values():
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            if error.resolved:
                resolved_count += 1
        
        return {
            'total_errors': total_errors,
            'by_type': self.error_counts.copy(),
            'by_severity': severity_counts,
            'resolved_count': resolved_count,
            'resolution_rate': (resolved_count / total_errors) * 100
        }


# Global error registry
error_registry = ErrorRegistry()


class ErrorHandler:
    """Main error handling class"""
    
    def __init__(self):
        self.error_callbacks = {}
        self.default_severity = ErrorSeverity.MEDIUM
    
    def register_callback(self, error_type: str, callback: Callable[[ErrorInfo], None]):
        """Register a callback for specific error types"""
        if error_type not in self.error_callbacks:
            self.error_callbacks[error_type] = []
        self.error_callbacks[error_type].append(callback)
    
    def handle_error(self, 
                    error: Exception, 
                    context: Dict[str, Any] = None,
                    severity: ErrorSeverity = None,
                    error_id: str = None) -> str:
        """
        Handle an error and return error ID
        
        Args:
            error: The exception that occurred
            context: Additional context information
            severity: Error severity level
            error_id: Optional custom error ID
            
        Returns:
            str: Error ID for tracking
        """
        if error_id is None:
            error_id = self._generate_error_id()
        
        if context is None:
            context = {}
        
        if severity is None:
            severity = self._determine_severity(error)
        
        # Create error info
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            context=context,
            traceback=traceback.format_exc()
        )
        
        # Register the error
        error_registry.register_error(error_info)
        
        # Log the error
        self._log_error(error_info)
        
        # Execute callbacks
        self._execute_callbacks(error_info)
        
        return error_id
    
    def _generate_error_id(self) -> str:
        """Generate a unique error ID"""
        import uuid
        return f"ERR_{uuid.uuid4().hex[:8]}"
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on exception type"""
        critical_errors = (SystemExit, KeyboardInterrupt, MemoryError)
        high_errors = (ConnectionError, TimeoutError, PermissionError)
        medium_errors = (ValueError, TypeError, AttributeError)
        
        if isinstance(error, critical_errors):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, high_errors):
            return ErrorSeverity.HIGH
        elif isinstance(error, medium_errors):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _log_error(self, error_info: ErrorInfo):
        """Log the error with appropriate level"""
        severity_to_level = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO
        }
        
        level = severity_to_level.get(error_info.severity, logging.ERROR)
        
        logger.log(level, 
                  f"Error {error_info.error_id}: {error_info.message} "
                  f"(Type: {error_info.error_type}, Severity: {error_info.severity.value})")
        
        if error_info.traceback and error_info.severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            logger.log(level, f"Traceback for {error_info.error_id}:\n{error_info.traceback}")
    
    def _execute_callbacks(self, error_info: ErrorInfo):
        """Execute registered callbacks for the error type"""
        callbacks = self.error_callbacks.get(error_info.error_type, [])
        
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")


# Global error handler
error_handler = ErrorHandler()


def handle_exceptions(severity: ErrorSeverity = None, 
                     context: Dict[str, Any] = None,
                     reraise: bool = False):
    """
    Decorator to handle exceptions in functions
    
    Args:
        severity: Error severity override
        context: Additional context to include
        reraise: Whether to reraise the exception after handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_context = context.copy() if context else {}
                error_context.update({
                    'function': func.__name__,
                    'args': str(args)[:200],  # Limit args length
                    'kwargs': str(kwargs)[:200]
                })
                
                error_id = error_handler.handle_error(e, error_context, severity)
                
                if reraise:
                    raise
                
                logger.error(f"Exception handled in {func.__name__}: {error_id}")
                return None
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = context.copy() if context else {}
                error_context.update({
                    'function': func.__name__,
                    'args': str(args)[:200],
                    'kwargs': str(kwargs)[:200]
                })
                
                error_id = error_handler.handle_error(e, error_context, severity)
                
                if reraise:
                    raise
                
                logger.error(f"Exception handled in {func.__name__}: {error_id}")
                return None
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def handle_api_errors(func: Callable) -> Callable:
    """Decorator specifically for API error handling"""
    return handle_exceptions(
        severity=ErrorSeverity.HIGH,
        context={'component': 'api'},
        reraise=False
    )(func)


def handle_data_errors(func: Callable) -> Callable:
    """Decorator specifically for data processing error handling"""
    return handle_exceptions(
        severity=ErrorSeverity.MEDIUM,
        context={'component': 'data'},
        reraise=False
    )(func)


def handle_auth_errors(func: Callable) -> Callable:
    """Decorator specifically for authentication error handling"""
    return handle_exceptions(
        severity=ErrorSeverity.HIGH,
        context={'component': 'auth'},
        reraise=True
    )(func)


class APIError(Exception):
    """Custom exception for API-related errors"""
    def __init__(self, message: str, status_code: int = None, provider: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    def __init__(self, message: str, provider: str = None):
        super().__init__(message)
        self.provider = provider


class DataValidationError(Exception):
    """Custom exception for data validation errors"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class RateLimitError(Exception):
    """Custom exception for rate limit errors"""
    def __init__(self, message: str, retry_after: int = None, provider: str = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.provider = provider


# Error callback examples
def critical_error_callback(error_info: ErrorInfo):
    """Handle critical errors"""
    logger.critical(f"CRITICAL ERROR: {error_info.error_id} - {error_info.message}")
    # In a real application, you might send alerts, notifications, etc.


def api_error_callback(error_info: ErrorInfo):
    """Handle API errors"""
    logger.error(f"API ERROR: {error_info.error_id}")
    # Could implement retry logic, circuit breaker patterns, etc.


# Register default callbacks
error_handler.register_callback('APIError', api_error_callback)


# Example usage functions
@handle_exceptions(severity=ErrorSeverity.HIGH)
async def example_function():
    """Example function with error handling"""
    raise ValueError("This is a test error")


@handle_api_errors
async def example_api_call():
    """Example API call with error handling"""
    raise APIError("API connection failed", 500, "example_provider")


if __name__ == "__main__":
    import asyncio
    
    async def test_error_handling():
        # Test the error handling system
        await example_function()
        await example_api_call()
        
        # Get error statistics
        stats = error_registry.get_error_stats()
        print(f"Error stats: {stats}")
        
        # Get recent errors
        recent = error_registry.get_recent_errors(5)
        for error in recent:
            print(f"Error: {error.error_id} - {error.message}")
    
    asyncio.run(test_error_handling())
