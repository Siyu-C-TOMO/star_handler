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
from slack_bolt import App
import getpass

class SlackNotifier:
    """Handles Slack notifications using Bolt framework."""
    
    def __init__(self):
        self.app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
        self.default_channel = "@U03DENW0RPV"
        
    def send(self, message: str, channel: Optional[str] = None) -> bool:
        """Send message to Slack channel or DM."""
        try:
            response = self.app.client.chat_postMessage(
                channel=channel or self.default_channel,
                text=message
            )
            return response["ok"]
        except Exception as e:
            print(f"Failed to send Slack message: {e}")
            return False

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
    _slack_notifier = None
    
    @classmethod
    def get_slack_notifier(cls) -> SlackNotifier:
        """Get or create Slack notifier instance."""
        if cls._slack_notifier is None:
            cls._slack_notifier = SlackNotifier()
        return cls._slack_notifier

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
                 notify: bool = True,
                 channel: Optional[str] = None) -> Callable:
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
    channel : Optional[str]
        Specific Slack channel for notifications
        
    [OUTPUT]
    Callable:
        Wrapped function
        
    [EXAMPLE]
    >>> @log_execution(notify=True, channel="#analysis")
    >>> def process_data():
    >>>     pass
    """
    def decorator(func: Callable) -> Callable:
        logger_name = f"{func.__module__}.{func.__name__}"
        logger = logging.getLogger(logger_name)
        user = getpass.getuser()
        directory = os.getcwd()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info("Started")
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                
                duration = datetime.now() - start_time
                logger.info(f"Completed in {duration.total_seconds():.2f}s")
                
                if notify:
                    LogConfig.get_slack_notifier().send(
                        f"✅ {logger_name} completed in {duration.total_seconds():.2f}s\nUser: {user}\nDirectory: {directory}",
                        channel=channel
                    )
                    
                return result
                
            except Exception as e:
                logger.error(f"Failed: {str(e)}")
                if notify:
                    LogConfig.get_slack_notifier().send(
                        f"❌ {logger_name} failed: {str(e)}\nUser: {user}\nDirectory: {directory}",
                        channel=channel
                    )
                    
                raise
                
        return wrapper
        
    return decorator(func) if func else decorator

root_logger = setup_logger(
    'star_handler',
    log_file=str(LogConfig.LOG_DIR / 'star_handler.log')
)

"""
from star_handler.utils.logger import log_execution, setup_logger

logger = setup_logger(__name__)

@log_execution(notify=True)
def analyze_data():
    logger.info("Processing data...")
    # Analysis code here
"""
