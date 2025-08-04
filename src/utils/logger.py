"""Logging configuration for GitLab tools."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


# ANSI color codes for terminal output
class Colors:
    """Terminal color codes."""
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages."""
    
    COLORS = {
        'DEBUG': Colors.CYAN,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.RED + Colors.BOLD,
    }
    
    def __init__(self, *args, use_colors: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        if self.use_colors:
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{Colors.RESET}"
                record.name = f"{Colors.BLUE}{record.name}{Colors.RESET}"
        
        return super().format(record)


def setup_logging(
    config: Optional[Dict[str, Any]] = None,
    log_file: Optional[str] = None,
    console_level: Optional[str] = None,
    file_level: Optional[str] = None,
    use_colors: bool = True
) -> None:
    """Setup logging configuration.
    
    Args:
        config: Logging configuration dict
        log_file: Override log file path
        console_level: Override console log level
        file_level: Override file log level
        use_colors: Whether to use colored output
    """
    config = config or {}
    
    # Get configuration values
    level = config.get('level', 'INFO')
    log_file = log_file or config.get('file', 'logs/gitlab-tools.log')
    max_size = config.get('max_size', 10) * 1024 * 1024  # Convert MB to bytes
    backup_count = config.get('backup_count', 5)
    format_str = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Override levels if specified
    console_level = console_level or level
    file_level = file_level or level
    
    # Create logs directory if needed
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))
    
    # Use colored formatter for console
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        use_colors=use_colors
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count
    )
    file_handler.setLevel(getattr(logging, file_level.upper()))
    
    # Plain formatter for file
    file_formatter = logging.Formatter(format_str)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Log startup message
    logging.info(f"Logging initialized - Console: {console_level}, File: {file_level} -> {log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class OperationLogger:
    """Context manager for logging operations with timing."""
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        """Initialize operation logger.
        
        Args:
            logger: Logger instance
            operation: Operation description
            **kwargs: Additional context to log
        """
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None
        self.success = True
        self.error = None
    
    def __enter__(self):
        """Start operation logging."""
        self.start_time = datetime.now()
        context_str = ', '.join(f"{k}={v}" for k, v in self.context.items())
        msg = f"Starting {self.operation}"
        if context_str:
            msg += f" ({context_str})"
        self.logger.info(msg)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End operation logging."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation} in {duration:.2f}s"
            )
        else:
            self.success = False
            self.error = exc_val
            self.logger.error(
                f"Failed {self.operation} after {duration:.2f}s: {exc_val}"
            )
        
        return False  # Don't suppress exceptions


def log_api_call(func):
    """Decorator to log API calls."""
    def wrapper(self, *args, **kwargs):
        logger = logging.getLogger(self.__class__.__name__)
        
        # Log the call
        func_name = func.__name__
        args_str = ', '.join(repr(arg) for arg in args)
        kwargs_str = ', '.join(f"{k}={v!r}" for k, v in kwargs.items())
        all_args = ', '.join(filter(None, [args_str, kwargs_str]))
        
        logger.debug(f"API call: {func_name}({all_args})")
        
        try:
            result = func(self, *args, **kwargs)
            logger.debug(f"API call successful: {func_name}")
            return result
        except Exception as e:
            logger.error(f"API call failed: {func_name} - {e}")
            raise
    
    return wrapper