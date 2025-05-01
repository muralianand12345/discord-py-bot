import os
import logging
from typing import Optional


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

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Clear existing handlers
        logger.handlers = []

        # Format for log messages
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Add console handler
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Add file handler
        if file_output:
            if filename:
                # Create directory if it doesn't exist
                (
                    os.makedirs(os.path.dirname(filename), exist_ok=True)
                    if "/" in filename or "\\" in filename
                    else None
                )
                # Use utf-8 encoding for file output
                file_handler = logging.FileHandler(
                    filename, mode=file_mode, encoding="utf-8", errors="replace"
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            else:
                raise ValueError("Filename must be provided when file_output is True")

        return logger
