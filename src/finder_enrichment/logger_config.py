import logging
import os
from typing import Optional

# Global logger instance
_logger: Optional[logging.Logger] = None

def setup_logger(name: str = 'orchestrator') -> logging.Logger:
    """Sets up the logger if not already set up, otherwise returns the existing logger.
    
    Args:
        name: The name for the logger. Defaults to 'orchestrator'.
    
    Returns:
        The configured logger instance.
    """
    global _logger
    if _logger is None:
        # Get log level from environment variable, default to INFO (20)
        log_level = int(os.getenv("LOG_LEVEL", "10"))
        
        # Create logger
        _logger = logging.getLogger(name)
        _logger.setLevel(log_level)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        _logger.addHandler(console_handler)
        
        # Prevent propagation to root logger to avoid duplicate messages
        _logger.propagate = False
        
    return _logger

def get_logger(name: str = 'finder_enrichment_db') -> logging.Logger:
    """Returns the logger instance, setting it up if necessary.
    
    Args:
        name: The name for the logger. Defaults to 'finder_enrichment_db'.
    
    Returns:
        The configured logger instance.
    """
    if _logger is None:
        return setup_logger(name)
    return _logger

def configure_logging_for_vercel():
    """Configure logging to work properly in Vercel environment.
    This ensures all loggers have proper handlers and output to stdout/stderr.
    """
    # Get log level from environment variable, default to INFO (20)
    log_level = int(os.getenv("LOG_LEVEL", "20"))
    
    # Configure root logger to output to console
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(levelname)s - %(asctime)s - %(name)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Create console handler for root logger
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Ensure our main logger is also configured
    setup_logger('finder_enrichment_db')
    
    # Log the configured level
    level_name = logging.getLevelName(log_level)
    root_logger.info(f"✅ Logging configured for Vercel environment - Level: {level_name} ({log_level})")
    
    # Test that logging is working at the configured level
    test_logger = logging.getLogger('test')
    if log_level <= logging.DEBUG:
        test_logger.debug("DEBUG test message")
    if log_level <= logging.INFO:
        test_logger.info("INFO test message")
    if log_level <= logging.WARNING:
        test_logger.warning("WARNING test message")
    if log_level <= logging.ERROR:
        test_logger.error("ERROR test message") 