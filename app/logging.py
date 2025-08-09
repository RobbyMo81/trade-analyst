"""Logging configuration and setup"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


def setup_logging(config_file: Optional[str] = None, 
                 verbose: bool = False,
                 log_dir: str = "logs") -> None:
    """
    Setup logging configuration
    
    Args:
        config_file: Optional path to logging configuration file
        verbose: Enable verbose logging
        log_dir: Directory for log files
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Determine log level
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Main log file with rotation
    main_log_file = log_path / "trade-analyst.log"
    main_file_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    main_file_handler.setLevel(logging.INFO)
    main_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(main_file_handler)
    
    # Error log file
    error_log_file = log_path / "trade-analyst-error.log"
    error_file_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_file_handler)
    
    # Debug log file (if verbose)
    if verbose:
        debug_log_file = log_path / "trade-analyst-debug.log"
        debug_file_handler = logging.handlers.RotatingFileHandler(
            debug_log_file,
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=2
        )
        debug_file_handler.setLevel(logging.DEBUG)
        debug_file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(debug_file_handler)
    
    # Data collection log
    data_logger = logging.getLogger('data_collection')
    data_log_file = log_path / "data-collection.log"
    data_file_handler = logging.handlers.RotatingFileHandler(
        data_log_file,
        maxBytes=15 * 1024 * 1024,  # 15MB
        backupCount=3
    )
    data_file_handler.setLevel(logging.INFO)
    data_file_handler.setFormatter(detailed_formatter)
    data_logger.addHandler(data_file_handler)
    data_logger.setLevel(logging.INFO)
    data_logger.propagate = False  # Don't propagate to root logger
    
    # API access log
    api_logger = logging.getLogger('api_access')
    api_log_file = log_path / "api-access.log"
    api_file_handler = logging.handlers.RotatingFileHandler(
        api_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3
    )
    api_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    api_file_handler.setFormatter(api_formatter)
    api_logger.addHandler(api_file_handler)
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = False
    
    # Authentication log
    auth_logger = logging.getLogger('authentication')
    auth_log_file = log_path / "authentication.log"
    auth_file_handler = logging.handlers.RotatingFileHandler(
        auth_log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=2
    )
    auth_file_handler.setFormatter(detailed_formatter)
    auth_logger.addHandler(auth_file_handler)
    auth_logger.setLevel(logging.INFO)
    auth_logger.propagate = False
    
    # Set levels for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info(f"Log directory: {log_path.absolute()}")


class StructuredLogger:
    """Structured logging helper for consistent log formats"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_api_call(self, 
                    provider: str, 
                    endpoint: str, 
                    method: str = "GET",
                    status_code: Optional[int] = None,
                    duration_ms: Optional[float] = None,
                    error: Optional[str] = None):
        """Log API call details"""
        message = f"API Call - Provider: {provider}, Endpoint: {endpoint}, Method: {method}"
        
        if status_code:
            message += f", Status: {status_code}"
        
        if duration_ms:
            message += f", Duration: {duration_ms:.2f}ms"
        
        if error:
            message += f", Error: {error}"
            self.logger.error(message)
        elif status_code and status_code >= 400:
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def log_data_collection(self,
                           data_type: str,
                           symbol: str,
                           record_count: int,
                           duration_ms: Optional[float] = None,
                           error: Optional[str] = None):
        """Log data collection details"""
        message = f"Data Collection - Type: {data_type}, Symbol: {symbol}, Records: {record_count}"
        
        if duration_ms:
            message += f", Duration: {duration_ms:.2f}ms"
        
        if error:
            message += f", Error: {error}"
            self.logger.error(message)
        else:
            self.logger.info(message)
    
    def log_auth_event(self,
                      event_type: str,
                      provider: str,
                      success: bool,
                      details: Optional[str] = None):
        """Log authentication events"""
        message = f"Auth Event - Type: {event_type}, Provider: {provider}, Success: {success}"
        
        if details:
            message += f", Details: {details}"
        
        if success:
            self.logger.info(message)
        else:
            self.logger.warning(message)
    
    def log_export_event(self,
                        export_type: str,
                        file_path: str,
                        record_count: int,
                        file_size_bytes: int,
                        duration_ms: Optional[float] = None):
        """Log data export events"""
        message = (f"Data Export - Type: {export_type}, Path: {file_path}, "
                  f"Records: {record_count}, Size: {file_size_bytes} bytes")
        
        if duration_ms:
            message += f", Duration: {duration_ms:.2f}ms"
        
        self.logger.info(message)


class LogAnalyzer:
    """Analyze log files for patterns and statistics"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about log files"""
        stats = {
            'log_files': [],
            'total_size_bytes': 0,
            'oldest_log': None,
            'newest_log': None
        }
        
        if not self.log_dir.exists():
            return stats
        
        log_files = list(self.log_dir.glob("*.log"))
        
        for log_file in log_files:
            file_stat = log_file.stat()
            file_info = {
                'name': log_file.name,
                'size_bytes': file_stat.st_size,
                'size_mb': file_stat.st_size / (1024 * 1024),
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat()
            }
            
            stats['log_files'].append(file_info)
            stats['total_size_bytes'] += file_stat.st_size
            
            if not stats['oldest_log'] or file_stat.st_mtime < stats['oldest_log']:
                stats['oldest_log'] = file_stat.st_mtime
            
            if not stats['newest_log'] or file_stat.st_mtime > stats['newest_log']:
                stats['newest_log'] = file_stat.st_mtime
        
        # Convert timestamps to ISO format
        if stats['oldest_log']:
            stats['oldest_log'] = datetime.fromtimestamp(stats['oldest_log']).isoformat()
        
        if stats['newest_log']:
            stats['newest_log'] = datetime.fromtimestamp(stats['newest_log']).isoformat()
        
        stats['total_size_mb'] = stats['total_size_bytes'] / (1024 * 1024)
        
        return stats
    
    def analyze_error_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze error patterns in recent logs"""
        error_patterns = {
            'error_count': 0,
            'warning_count': 0,
            'critical_count': 0,
            'common_errors': {},
            'error_timeline': []
        }
        
        # This is a simplified implementation
        # In practice, you'd parse log files and extract error information
        
        return error_patterns
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Clean up log files older than specified days"""
        if not self.log_dir.exists():
            return 0
        
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        removed_count = 0
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    removed_count += 1
                except Exception as e:
                    logging.getLogger(__name__).error(f"Failed to remove old log file {log_file}: {e}")
        
        return removed_count


# Performance monitoring decorator
def log_performance(logger_name: str = None):
    """Decorator to log function performance"""
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.info(f"Performance - {func.__name__}: {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(f"Performance - {func.__name__}: {duration:.2f}ms (FAILED: {e})")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.info(f"Performance - {func.__name__}: {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(f"Performance - {func.__name__}: {duration:.2f}ms (FAILED: {e})")
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


if __name__ == "__main__":
    # Test logging setup
    setup_logging(verbose=True)
    
    # Test structured logging
    structured_logger = StructuredLogger("test")
    structured_logger.log_api_call("test_provider", "/quotes", "GET", 200, 150.5)
    structured_logger.log_data_collection("quotes", "AAPL", 100, 250.0)
    structured_logger.log_auth_event("login", "test_provider", True)
    
    # Test log analysis
    analyzer = LogAnalyzer()
    stats = analyzer.get_log_stats()
    print(f"Log stats: {stats}")
    
    print("Logging test completed")
