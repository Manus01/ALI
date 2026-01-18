# app/services/structured_logger.py
"""
Structured Logging Framework for ALI Platform

Provides:
1. JSON-formatted log output for log aggregation systems
2. Automatic request context injection (request_id, user_id)
3. PII/Secret redaction to prevent sensitive data leakage
4. Convenience logger wrapper with context-aware methods

Usage:
    from app.services.structured_logger import ObservabilityLogger
    
    log = ObservabilityLogger("brand_monitoring")
    log.info("Fetching mentions", metadata={"count": 10})
    log.error("API failed", error=e)
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple, Pattern

# Import context accessors
try:
    from app.middleware.observability import get_request_id, get_user_id
except ImportError:
    # Fallback if middleware not loaded
    def get_request_id() -> str:
        return ""
    def get_user_id() -> str:
        return ""


# =============================================================================
# PII/SECRET REDACTION PATTERNS
# =============================================================================

# Compile patterns once for efficiency
REDACT_PATTERNS: List[Tuple[Pattern, str]] = [
    # JSON field patterns (case-insensitive)
    (re.compile(r'"password"\s*:\s*"[^"]*"', re.I), '"password": "[REDACTED]"'),
    (re.compile(r'"passwd"\s*:\s*"[^"]*"', re.I), '"passwd": "[REDACTED]"'),
    (re.compile(r'"secret"\s*:\s*"[^"]*"', re.I), '"secret": "[REDACTED]"'),
    (re.compile(r'"api_key"\s*:\s*"[^"]*"', re.I), '"api_key": "[REDACTED]"'),
    (re.compile(r'"apikey"\s*:\s*"[^"]*"', re.I), '"apikey": "[REDACTED]"'),
    (re.compile(r'"api-key"\s*:\s*"[^"]*"', re.I), '"api-key": "[REDACTED]"'),
    (re.compile(r'"token"\s*:\s*"[^"]*"', re.I), '"token": "[REDACTED]"'),
    (re.compile(r'"access_token"\s*:\s*"[^"]*"', re.I), '"access_token": "[REDACTED]"'),
    (re.compile(r'"refresh_token"\s*:\s*"[^"]*"', re.I), '"refresh_token": "[REDACTED]"'),
    (re.compile(r'"private_key"\s*:\s*"[^"]*"', re.I), '"private_key": "[REDACTED]"'),
    (re.compile(r'"credit_card"\s*:\s*"[^"]*"', re.I), '"credit_card": "[REDACTED]"'),
    (re.compile(r'"card_number"\s*:\s*"[^"]*"', re.I), '"card_number": "[REDACTED]"'),
    (re.compile(r'"cvv"\s*:\s*"[^"]*"', re.I), '"cvv": "[REDACTED]"'),
    (re.compile(r'"ssn"\s*:\s*"[^"]*"', re.I), '"ssn": "[REDACTED]"'),
    (re.compile(r'"social_security"\s*:\s*"[^"]*"', re.I), '"social_security": "[REDACTED]"'),
    
    # Bearer tokens in headers
    (re.compile(r'Bearer\s+[A-Za-z0-9\-_.~+/]+=*', re.I), 'Bearer [REDACTED]'),
    
    # Email addresses (optional - uncomment if emails should be redacted)
    # (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),
    
    # Credit card numbers (13-19 digits with optional separators)
    (re.compile(r'\b(?:\d{4}[-\s]?){3,4}\d{1,4}\b'), '[CC_REDACTED]'),
    
    # SSN pattern (XXX-XX-XXXX)
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN_REDACTED]'),
    
    # Firebase/GCP credential patterns
    (re.compile(r'"client_secret"\s*:\s*"[^"]*"', re.I), '"client_secret": "[REDACTED]"'),
    (re.compile(r'"client_id"\s*:\s*"[^"]*"', re.I), '"client_id": "[REDACTED]"'),
]


def redact_sensitive(text: str) -> str:
    """
    Apply all redaction patterns to the given text.
    
    This function is idempotent - applying it multiple times
    produces the same result.
    
    Args:
        text: The string to redact
        
    Returns:
        String with sensitive data replaced by [REDACTED] markers
    """
    if not isinstance(text, str):
        return str(text)
    
    result = text
    for pattern, replacement in REDACT_PATTERNS:
        result = pattern.sub(replacement, result)
    
    return result


def redact_dict(data: Dict[str, Any], sensitive_keys: set = None) -> Dict[str, Any]:
    """
    Recursively redact sensitive values in a dictionary.
    
    Args:
        data: Dictionary to redact
        sensitive_keys: Set of key names to redact (case-insensitive)
        
    Returns:
        New dictionary with sensitive values redacted
    """
    if sensitive_keys is None:
        sensitive_keys = {
            'password', 'passwd', 'secret', 'api_key', 'apikey', 'token',
            'access_token', 'refresh_token', 'private_key', 'credit_card',
            'card_number', 'cvv', 'ssn', 'social_security', 'client_secret'
        }
    
    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        if key_lower in sensitive_keys:
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = redact_dict(value, sensitive_keys)
        elif isinstance(value, list):
            result[key] = [
                redact_dict(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str):
            result[key] = redact_sensitive(value)
        else:
            result[key] = value
    
    return result


# =============================================================================
# STRUCTURED JSON FORMATTER
# =============================================================================

class StructuredFormatter(logging.Formatter):
    """
    JSON formatter that produces structured log entries compatible with
    log aggregation systems (CloudWatch, Stackdriver, ELK, etc.).
    
    Each log entry includes:
    - timestamp: ISO 8601 format with timezone
    - level: Log level name
    - service: Service name for filtering
    - request_id: Correlation ID from request context
    - user_id: Authenticated user ID if available
    - message: The log message (redacted)
    - logger: Logger name
    - Additional fields from record.extra
    """
    
    # Fields to copy from the log record if present
    EXTRA_FIELDS = [
        'request_id', 'user_id', 'route', 'method', 'latency_ms',
        'outcome', 'status_code', 'event', 'error_type', 'error_message',
        'metadata', 'component'
    ]
    
    def __init__(self, service_name: str = "ali-backend"):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        # Build base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": redact_sensitive(record.getMessage()),
        }
        
        # Add request context (from contextvars or record)
        log_entry["request_id"] = (
            getattr(record, 'request_id', None) or 
            get_request_id() or 
            None
        )
        log_entry["user_id"] = (
            getattr(record, 'user_id', None) or 
            get_user_id() or 
            None
        )
        
        # Add extra fields from record
        for field in self.EXTRA_FIELDS:
            if hasattr(record, field):
                value = getattr(record, field)
                if isinstance(value, str):
                    value = redact_sensitive(value)
                elif isinstance(value, dict):
                    value = redact_dict(value)
                log_entry[field] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Remove None values to reduce log size
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


# =============================================================================
# SETUP FUNCTION
# =============================================================================

def setup_structured_logging(
    service_name: str = "ali-backend",
    level: int = logging.INFO,
    json_output: bool = True
) -> None:
    """
    Configure the root logger with structured JSON output.
    
    Call this once at application startup (e.g., in main.py).
    
    Args:
        service_name: Name to include in all log entries
        level: Minimum log level
        json_output: If True, use JSON format; if False, use human-readable
    """
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_output:
        handler.setFormatter(StructuredFormatter(service_name))
    else:
        # Human-readable format for local development
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)
    
    # Reduce noise from third-party libraries
    noisy_loggers = [
        "httpx", "httpcore", "urllib3", "asyncio", 
        "google.auth", "google.api_core", "grpc"
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# =============================================================================
# CONVENIENCE LOGGER WRAPPER
# =============================================================================

class ObservabilityLogger:
    """
    Convenience wrapper for structured logging with automatic context injection.
    
    Provides a cleaner API than the standard logging module with built-in
    support for request context, error objects, and metadata.
    
    Usage:
        log = ObservabilityLogger("brand_monitoring")
        
        # Simple info log
        log.info("Processing mentions")
        
        # With metadata
        log.info("Found mentions", metadata={"count": 42, "source": "news"})
        
        # Error with exception
        try:
            risky_operation()
        except Exception as e:
            log.error("Operation failed", error=e)
    """
    
    def __init__(self, name: str, component: str = None):
        """
        Create a new observability logger.
        
        Args:
            name: Logger name (typically module or feature name)
            component: Optional component identifier for filtering
        """
        self.logger = logging.getLogger(name)
        self.component = component
    
    def _build_extra(self, **kwargs) -> dict:
        """Build extra dict with context and provided values."""
        extra = {
            "request_id": get_request_id(),
            "user_id": get_user_id(),
        }
        
        if self.component:
            extra["component"] = self.component
        
        # Handle error objects
        if "error" in kwargs:
            error = kwargs.pop("error")
            extra["error_type"] = type(error).__name__
            extra["error_message"] = str(error)
        
        # Handle metadata
        if "metadata" in kwargs:
            extra["metadata"] = kwargs.pop("metadata")
        
        # Add any remaining kwargs
        extra.update(kwargs)
        
        return extra
    
    def debug(self, message: str, **kwargs) -> None:
        """Log at DEBUG level."""
        self.logger.debug(message, extra=self._build_extra(**kwargs))
    
    def info(self, message: str, **kwargs) -> None:
        """Log at INFO level."""
        self.logger.info(message, extra=self._build_extra(**kwargs))
    
    def warning(self, message: str, **kwargs) -> None:
        """Log at WARNING level."""
        self.logger.warning(message, extra=self._build_extra(**kwargs))
    
    def error(self, message: str, **kwargs) -> None:
        """Log at ERROR level."""
        self.logger.error(message, extra=self._build_extra(**kwargs))
    
    def exception(self, message: str, **kwargs) -> None:
        """Log at ERROR level with exception traceback."""
        self.logger.exception(message, extra=self._build_extra(**kwargs))
    
    def critical(self, message: str, **kwargs) -> None:
        """Log at CRITICAL level."""
        self.logger.critical(message, extra=self._build_extra(**kwargs))


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

def get_logger(name: str, component: str = None) -> ObservabilityLogger:
    """
    Get an ObservabilityLogger instance.
    
    Convenience function that mirrors logging.getLogger().
    
    Args:
        name: Logger name
        component: Optional component identifier
        
    Returns:
        ObservabilityLogger instance
    """
    return ObservabilityLogger(name, component)
