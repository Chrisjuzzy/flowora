
"""
Structured Logging Configuration for Flowora
Provides centralized logging with rotation, formatting, and error handling
"""
import logging
import logging.handlers
import sys
import gzip
import os
from pathlib import Path
from structlog.contextvars import get_contextvars
from config_production import settings


def setup_logging():
    """
    Configure structured logging for the application
    """
    # Create logs directory if it doesn't exist
    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt=settings.LOG_FORMAT,
        datefmt=settings.LOG_DATE_FORMAT
    )

    json_formatter = JsonFormatter()

    request_filter = RequestContextFilter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.setFormatter(json_formatter)
    console_handler.addFilter(request_filter)
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    if settings.LOG_FILE and settings.LOG_ROTATION:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        if settings.LOG_COMPRESS:
            file_handler.namer = _gzip_namer
            file_handler.rotator = _gzip_rotator
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(request_filter)
        root_logger.addHandler(file_handler)
    elif settings.LOG_FILE:
        file_handler = logging.FileHandler(
            filename=settings.LOG_FILE,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(request_filter)
        root_logger.addHandler(file_handler)

    # Error handler (separate file for errors)
    if settings.LOG_FILE:
        error_log_path = Path(settings.LOG_FILE).parent / 'error.log'
        error_handler = logging.handlers.RotatingFileHandler(
            filename=error_log_path,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        if settings.LOG_COMPRESS:
            error_handler.namer = _gzip_namer
            error_handler.rotator = _gzip_rotator
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        error_handler.addFilter(request_filter)
        root_logger.addHandler(error_handler)

    # Configure third-party loggers
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.INFO)
    logging.getLogger('redis').setLevel(logging.WARNING)


class JsonFormatter(logging.Formatter):
    """
    Custom formatter for JSON log output
    Useful for log aggregation systems like ELK
    """
    def format(self, record):
        import json
        ctx = get_contextvars()
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'request_id': getattr(record, 'request_id', None) or ctx.get('request_id')
        }

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        if hasattr(record, 'props'):
            log_data['props'] = record.props

        return json.dumps(log_data)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_contextvars()
        record.request_id = ctx.get("request_id")
        return True


def _gzip_namer(name: str) -> str:
    return f"{name}.gz"


def _gzip_rotator(source: str, dest: str) -> None:
    with open(source, "rb") as f_in:
        with gzip.open(dest, "wb") as f_out:
            f_out.writelines(f_in)
    os.remove(source)


class LoggerMixin:
    """
    Mixin class to add logging capabilities
    """
    @property
    def logger(self):
        return logging.getLogger(self.__class__.__name__)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_function_call(logger: logging.Logger):
    """
    Decorator to log function calls

    Args:
        logger: Logger instance to use

    Usage:
        @log_function_call(logger)
        def my_function(arg1, arg2):
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned successfully")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised exception: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


def log_execution_time(logger: logging.Logger):
    """
    Decorator to log function execution time

    Args:
        logger: Logger instance to use

    Usage:
        @log_execution_time(logger)
        def my_function():
            pass
    """
    import time

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.debug(f"Starting {func.__name__}")
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{func.__name__} completed in {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


# Initialize logging on module import
setup_logging()
