"""
Helper utilities for the application
"""

import os
import platform
import socket
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_system_info() -> Dict[str, str]:
    """Get current system information"""
    return {
        'hostname': socket.gethostname(),
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version()
    }


def format_time(seconds: float) -> str:
    """Format seconds into human-readable time"""
    if seconds < 1:
        return f"{seconds*1000:.2f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def format_number(num: int) -> str:
    """Format large numbers with thousand separators"""
    if num is None or (isinstance(num, float) and (num != num)):  # Check for NaN
        return "N/A"
    try:
        return f"{int(num):,}"
    except (ValueError, TypeError):
        return "N/A"


def format_memory(kb: int) -> str:
    """Format KB into human-readable memory"""
    if kb is None or kb == 0:
        return "0 KB"
    try:
        kb = int(kb)
        if kb < 1024:
            return f"{kb} KB"
        elif kb < 1024 * 1024:
            return f"{kb/1024:.2f} MB"
        else:
            return f"{kb/(1024*1024):.2f} GB"
    except (ValueError, TypeError):
        return "N/A"


def validate_cnf_file(filepath: str) -> bool:
    """Validate if file is a CNF file"""
    if not os.path.exists(filepath):
        return False
    
    if not filepath.endswith('.cnf'):
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first few lines to check for CNF format
            for _ in range(100):
                line = f.readline()
                if not line:
                    break
                if line.strip().startswith('p cnf'):
                    return True
        return False
    except Exception as e:
        logger.error(f"Error validating CNF file {filepath}: {e}")
        return False


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division that handles zero denominator"""
    if denominator == 0:
        return default
    return numerator / denominator


def timestamp_to_str(timestamp: datetime = None) -> str:
    """Convert timestamp to string"""
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def str_to_timestamp(date_str: str) -> datetime:
    """Convert string to timestamp"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None


def ensure_dir(path: str):
    """Ensure directory exists"""
    os.makedirs(path, exist_ok=True)


def get_available_cores() -> int:
    """Get number of available CPU cores"""
    return os.cpu_count() or 1


def truncate_string(s: str, max_length: int = 100) -> str:
    """Truncate string with ellipsis"""
    if len(s) <= max_length:
        return s
    return s[:max_length-3] + "..."


class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""
    
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Format
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    if platform.system() != "Windows":
        console_handler.setFormatter(ColoredFormatter(fmt))
    else:
        console_handler.setFormatter(logging.Formatter(fmt))
    
    logger.addHandler(console_handler)
    
    return logger
