"""Logging configuration for the application."""

import logging
import sys
from typing import Optional

# Import RichHandler separately
from rich.logging import RichHandler


def setup_logging(level: int = logging.INFO, fmt: str = "text") -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (e.g., logging.INFO, logging.DEBUG)
        fmt: Output format - "text" for rich text, "json" for JSON logs
    """
    # Remove any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set the log level
    root_logger.setLevel(level)
    
    if fmt == "json":
        try:
            from pythonjsonlogger import jsonlogger
            
            # Create JSON formatter
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            )
            
            # Use standard StreamHandler for JSON output
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)
            
        except ImportError:
            print("python-json-logger not installed, falling back to text format")
            fmt = "text"
    
    if fmt == "text":
        # Use RichHandler for beautiful console output
        rich_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=True,
        )
        rich_handler.setFormatter(
            logging.Formatter("%(message)s")
        )
        root_logger.addHandler(rich_handler)
    
    # Suppress verbose logs from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)