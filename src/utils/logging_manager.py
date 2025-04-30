"""
Logging utilities for the Discord bot.

This module provides classes for managing and configuring loggers.
"""

import os
import time
import logging
import functools
from datetime import datetime
from typing import Optional, Dict, Any


class LogContext:
    """
    Context manager for adding additional context to log messages.

    This allows for temporarily adding context to log entries within a specific scope.

    Example:
        with LogContext(logger, {"user_id": "12345"}):
            logger.info("User action")  # Will include the user_id in the log
    """

    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        """
        Initialize the LogContext.

        Args:
            logger: The logger to add context to
            context: Dictionary of context variables to add
        """
        self.logger = logger
        self.context = context
        self.old_factory = None

    def __enter__(self):
        """Set up the context when entering the with block."""
        # Store old factory
        self.old_factory = logging.getLogRecordFactory()

        # Create a new factory that adds our context
        old_factory = self.old_factory
        context = self.context

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in context.items():
                setattr(record, key, value)
            return record

        # Set our factory as the new factory
        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting the with block."""
        # Restore old factory
        logging.setLogRecordFactory(self.old_factory)


class TimingLogger:
    """
    Utility for logging execution time of code blocks.

    Example:
        with TimingLogger(logger, "operation_name"):
            # Code to time
            pass
    """

    def __init__(
        self, logger: logging.Logger, operation_name: str, level: int = logging.DEBUG
    ):
        """
        Initialize the timer.

        Args:
            logger: The logger to use for logging
            operation_name: Name of the operation being timed
            level: Logging level to use
        """
        self.logger = logger
        self.operation_name = operation_name
        self.level = level
        self.start_time = None

    def __enter__(self):
        """Start timing when entering the with block."""
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log the elapsed time when exiting the with block."""
        elapsed = time.time() - self.start_time
        if exc_type:
            self.logger.log(
                self.level,
                f"{self.operation_name} failed after {elapsed:.3f}s with {exc_type.__name__}: {exc_val}",
            )
        else:
            self.logger.log(
                self.level, f"{self.operation_name} completed in {elapsed:.3f}s"
            )


def log_execution_time(
    logger: logging.Logger,
    operation_name: Optional[str] = None,
    level: int = logging.DEBUG,
):
    """
    Decorator to log the execution time of a function.

    Args:
        logger: The logger to use
        operation_name: Name of the operation (defaults to function name if None)
        level: Logging level to use

    Returns:
        Decorated function

    Example:
        @log_execution_time(logger, "database_query")
        def query_database():
            # ... function code ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start_time = time.time()
            logger.log(level, f"Starting {name}")
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(level, f"{name} completed in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.log(
                    level,
                    f"{name} failed after {elapsed:.3f}s with {type(e).__name__}: {str(e)}",
                )
                raise

        return wrapper

    return decorator


class LoggingManager:
    """Utility class for setting up logging configurations."""

    @staticmethod
    def setup_logger(
        name: str,
        console_output: bool = True,
        file_output: bool = False,
        filename: Optional[str] = None,
        file_mode: str = "a",
        level: int = logging.INFO,
        format_string: Optional[str] = None,
    ) -> logging.Logger:
        """
        Set up and configure a logger with specified outputs.

        Args:
            name: Name of the logger
            console_output: Whether to output logs to console
            file_output: Whether to output logs to a file
            filename: Path to the log file (required if file_output is True)
            file_mode: File open mode ('a' for append, 'w' for write)
            level: Logging level
            format_string: Custom format string for log messages

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Default format for log messages
        if format_string is None:
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(message)s"
            )

        formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

        # Add console handler
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Add file handler
        if file_output:
            if filename:
                # Create directory if it doesn't exist
                if "/" in filename or "\\" in filename:
                    directory = os.path.dirname(filename)
                    if directory:
                        os.makedirs(directory, exist_ok=True)

                # Create a rotating file handler
                file_handler = logging.FileHandler(filename, mode=file_mode)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            else:
                raise ValueError("Filename must be provided when file_output is True")

        return logger

    @staticmethod
    def get_daily_log_filename(base_filename: str) -> str:
        """
        Generate a log filename with the current date.

        Args:
            base_filename: Base filename to use

        Returns:
            Filename with date appended
        """
        today = datetime.now().strftime("%Y-%m-%d")
        filename, extension = os.path.splitext(base_filename)
        return f"{filename}_{today}{extension}"
