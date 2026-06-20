"""
Structured Logging Configuration

Sets up JSON-formatted logging for production and human-readable logs for development.
"""

import logging
import sys
from typing import Any
from datetime import datetime
import json

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON-structured logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request_id if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "context"):
            log_data["context"] = record.context
        
        return json.dumps(log_data)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development"""
    
    def format(self, record: logging.LogRecord) -> str:
        colors = {
            "DEBUG": "\033[36m",
            "INFO": "\033[32m",
            "WARNING": "\033[33m",
            "ERROR": "\033[31m",
            "CRITICAL": "\033[35m",
        }
        reset = "\033[0m"
        color = colors.get(record.levelname, "")
        
        formatted = (
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"{color}{record.levelname:8}{reset} | "
            f"{record.name:30} | "
        )
        
        # Add request_id if present
        if hasattr(record, "request_id"):
            formatted += f"[{record.request_id[:8]}] "
        
        formatted += record.getMessage()
        
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_logging() -> None:
    """Configure application-wide logging"""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    
    if settings.ENVIRONMENT == "production":
        formatter = JSONFormatter()
    else:
        formatter = DevelopmentFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    root_logger.info(
        f"Logging configured: level={settings.LOG_LEVEL}, env={settings.ENVIRONMENT}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module"""
    return logging.getLogger(name)
