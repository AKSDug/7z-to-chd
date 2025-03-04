#!/usr/bin/env python3
"""
7z-to-CHD Converter - Utilities Module
Common utility functions

Author: AKSDug
Repository: https://github.com/AKSDug/7z-to-chd
"""

import os
import sys
import logging
import time
from pathlib import Path
from datetime import datetime

# Constants
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_LEVEL = logging.INFO

def setup_logging(log_dir=None, log_level=DEFAULT_LOG_LEVEL, console=True):
    """
    Set up logging configuration.
    
    Args:
        log_dir (str, optional): Directory to store log files. Defaults to 'logs'.
        log_level (int, optional): Logging level. Defaults to logging.INFO.
        console (bool, optional): Whether to log to console. Defaults to True.
        
    Returns:
        logging.Logger: Configured root logger.
    """
    # Create timestamp for log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Set up log directory
    if log_dir is None:
        script_dir = Path(__file__).parent.parent
        log_dir = script_dir / 'logs'
    else:
        log_dir = Path(log_dir)
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create a file handler
    log_file = log_dir / f'7z-to-chd_{timestamp}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    root_logger.addHandler(file_handler)
    
    # Create a console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        root_logger.addHandler(console_handler)
    
    # Log basic information
    logger = logging.getLogger('utils')
    logger.info(f"Log file: {log_file}")
    
    return root_logger

def format_time(seconds):
    """
    Format time in seconds to a human-readable string.
    
    Args:
        seconds (float): Time in seconds.
        
    Returns:
        str: Formatted time string.
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

class Timer:
    """Simple timer class for measuring elapsed time."""
    
    def __init__(self):
        """Initialize the timer."""
        self.start_time = None
        self.stop_time = None
    
    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        self.stop_time = None
        return self
    
    def stop(self):
        """Stop the timer."""
        self.stop_time = time.time()
        return self
    
    def elapsed(self):
        """
        Get the elapsed time.
        
        Returns:
            float: Elapsed time in seconds.
        """
        if self.start_time is None:
            return 0
        
        if self.stop_time is None:
            return time.time() - self.start_time
        
        return self.stop_time - self.start_time
    
    def elapsed_str(self):
        """
        Get the elapsed time as a formatted string.
        
        Returns:
            str: Formatted elapsed time.
        """
        return format_time(self.elapsed())

def confirm_path(path, create=False, is_file=False):
    """
    Confirm that a path exists or can be created.
    
    Args:
        path (str): Path to confirm.
        create (bool, optional): Whether to create the path if it doesn't exist. Defaults to False.
        is_file (bool, optional): Whether the path is a file path. Defaults to False.
        
    Returns:
        Path: Confirmed path.
        
    Raises:
        FileNotFoundError: If the path does not exist and create is False.
        NotADirectoryError: If the path exists but is not a directory (when is_file is False).
        NotADirectoryError: If the parent directory of a file path does not exist and create is True.
    """
    path = Path(path)
    
    if is_file:
        # For file paths, check if the parent directory exists
        parent_dir = path.parent
        
        if not parent_dir.exists():
            if create:
                os.makedirs(parent_dir, exist_ok=True)
            else:
                raise FileNotFoundError(f"Parent directory does not exist: {parent_dir}")
        
        elif not parent_dir.is_dir():
            raise NotADirectoryError(f"Parent path is not a directory: {parent_dir}")
        
        return path
    
    else:
        # For directory paths
        if path.exists():
            if not path.is_dir():
                raise NotADirectoryError(f"Path exists but is not a directory: {path}")
        elif create:
            os.makedirs(path, exist_ok=True)
        else:
            raise FileNotFoundError(f"Directory does not exist: {path}")
        
        return path