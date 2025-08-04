"""Logging configuration for GitLab Tools CLI."""

import logging
import sys
from pathlib import Path
from typing import Optional

from colorama import init, Fore, Style


# Initialize colorama for cross-platform colored output
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record):
        # Color the level name
        level_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{level_color}{record.levelname}{Style.RESET_ALL}"
        
        # Format the message
        formatted = super().format(record)
        
        return formatted


def setup_cli_logging(debug: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration for the CLI.
    
    Args:
        debug: Enable debug level logging
        log_file: Optional log file path
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('glt')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Console formatter
    console_format = '%(levelname)s: %(message)s'
    if debug:
        console_format = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
    
    console_formatter = ColoredFormatter(console_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Suppress some noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return logger


def get_default_log_file() -> Path:
    """Get the default log file path."""
    home_dir = Path.home()
    log_dir = home_dir / '.glt'
    log_dir.mkdir(exist_ok=True)
    return log_dir / 'glt.log'


class CLILogger:
    """
    CLI-specific logger with convenience methods.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def info(self, message: str, emoji: str = "ℹ️"):
        """Log an info message with emoji."""
        self.logger.info(f"{emoji} {message}")
    
    def success(self, message: str, emoji: str = "✅"):
        """Log a success message."""
        self.logger.info(f"{Fore.GREEN}{emoji} {message}{Style.RESET_ALL}")
    
    def warning(self, message: str, emoji: str = "⚠️"):
        """Log a warning message."""
        self.logger.warning(f"{emoji} {message}")
    
    def error(self, message: str, emoji: str = "❌"):
        """Log an error message."""
        self.logger.error(f"{emoji} {message}")
    
    def debug(self, message: str):
        """Log a debug message."""
        self.logger.debug(message)
    
    def progress(self, message: str, emoji: str = "🔄"):
        """Log a progress message."""
        self.logger.info(f"{Fore.CYAN}{emoji} {message}{Style.RESET_ALL}")
    
    def command(self, command: str):
        """Log a command execution."""
        self.logger.debug(f"Executing command: {command}")
    
    def result(self, message: str, emoji: str = "📊"):
        """Log a result message."""
        self.logger.info(f"{Fore.BLUE}{emoji} {message}{Style.RESET_ALL}")


def create_cli_logger(debug: bool = False, log_file: Optional[str] = None) -> CLILogger:
    """
    Create a CLI logger instance.
    
    Args:
        debug: Enable debug logging
        log_file: Optional log file path
        
    Returns:
        CLILogger instance
    """
    if log_file is None and debug:
        log_file = str(get_default_log_file())
    
    logger = setup_cli_logging(debug=debug, log_file=log_file)
    return CLILogger(logger)