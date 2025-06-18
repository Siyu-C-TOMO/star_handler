"""
Logging utilities for particle analysis.

Provides centralized logging configuration and functionality for:
- File logging
- Console output
- Slack notifications
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Optional, Callable
import requests

class LogConfig:
    """Configuration for logging system.
    
    [ATTRIBUTES]
    LOG_DIR : Path
        Directory for log files
    LOG_FORMAT : str
        Format string for log messages
    DATE_FORMAT : str
        Format string for timestamps
    SLACK_WEBHOOK : str
        URL for Slack notifications
    """
    
    LOG_DIR = Path("/data/Users/Siyu/Scripts/star_handler/logs")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    SLACK_WEBHOOK = "https://hooks.slack.com/services/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"

def setup_logger(name: str,
                log_file: Optional[str] = None,
                level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger instance.
    
    [WORKFLOW]
    1. Create logger with name
    2. Set log level
    3. Add handlers (file and console)
    4. Configure formatters
    
    [PARAMETERS]
    name : str
        Logger name
    log_file : Optional[str]
        Path to log file
    level : int
        Logging level
        
    [OUTPUT]
    logging.Logger:
        Configured logger instance
        
    [EXAMPLE]
    >>> logger = setup_logger('analysis')
    >>> logger.info('Starting analysis')
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(level)
        
        formatter = logging.Formatter(
            fmt=LogConfig.LOG_FORMAT,
            datefmt=LogConfig.DATE_FORMAT
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        if log_file:
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
        logger.propagate = False
        
    return logger

def log_execution(func: Optional[Callable] = None,
                 *,
                 notify: bool = True) -> Callable:
    """Decorator for logging function execution and optional notification.
    
    [WORKFLOW]
    1. Log function start
    2. Execute function
    3. Log completion/error
    4. Send notification (optional)
    
    [PARAMETERS]
    func : Optional[Callable]
        Function to wrap
    notify : bool
        Whether to send Slack notification
        
    [OUTPUT]
    Callable:
        Wrapped function
        
    [EXAMPLE]
    >>> @log_execution(notify=True)
    >>> def process_data():
    >>>     pass
    """
    def decorator(func: Callable) -> Callable:
        # Use a module-level logger to avoid duplication
        logger_name = f"{func.__module__}.{func.__name__}"
        logger = logging.getLogger(logger_name)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log start
            logger.info("Started")
            start_time = datetime.now()
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log completion
                duration = datetime.now() - start_time
                logger.info(f"Completed in {duration.total_seconds():.2f}s")
                
                # Send notification
                if notify:
                    _send_notification(
                        f"✅ {logger_name} completed in {duration.total_seconds():.2f}s"
                    )
                    
                return result
                
            except Exception as e:
                # Log error
                logger.error(f"Failed: {str(e)}")
                
                # Send notification
                if notify:
                    _send_notification(
                        f"❌ {logger_name} failed: {str(e)}"
                    )
                    
                raise
                
        return wrapper
        
    return decorator(func) if func else decorator

def _send_notification(message: str) -> None:
    """Send notification to Slack.
    
    [WORKFLOW]
    1. Format message with context
    2. Send to webhook
    3. Handle response
    
    [PARAMETERS]
    message : str
        Message to send
    """
    try:
        # Add context
        user = os.getlogin()
        timestamp = datetime.now().strftime(LogConfig.DATE_FORMAT)
        address = os.getcwd()
        
        full_message = (
            f"{message}\n"
            f"User: {user}\n"
            f"Time: {timestamp}\n"
            f"Directory: {address}"
        )
        
        # Send to Slack
        response = requests.post(
            LogConfig.SLACK_WEBHOOK,
            json={"text": full_message}
        )
        
        if response.status_code != 200:
            logging.error(f"Slack notification failed: {response.text}")
            
    except Exception as e:
        logging.error(f"Failed to send notification: {str(e)}")

# Configure root logger
root_logger = setup_logger(
    'star_handler',
    log_file=str(LogConfig.LOG_DIR / 'star_handler.log')
)

# Example usage in other modules:
"""
from star_handler.utils.logger import log_execution, setup_logger

logger = setup_logger(__name__)

@log_execution(notify=True)
def analyze_data():
    logger.info("Processing data...")
    # Analysis code here
"""
