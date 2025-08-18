# app/core/logging_config.py
"""
Structured Logging Configuration for GremlinsAI.

This module provides production-ready structured logging with:
- JSON formatted output for log aggregation
- Correlation IDs for request tracing
- Environment-specific log levels
- Performance monitoring
- Security audit logging
"""

import json
import logging
import logging.config
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger

# Context variable for correlation ID tracking
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record):
        """Add correlation ID to the log record."""
        record.correlation_id = correlation_id.get() or "no-correlation-id"
        return True


class StructuredFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging.
    
    Adds standard fields for observability and monitoring.
    """
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add service information
        log_record['service'] = 'gremlinsai-backend'
        log_record['version'] = '9.0.0'
        
        # Add correlation ID for request tracing
        log_record['correlation_id'] = getattr(record, 'correlation_id', 'no-correlation-id')
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add module and function information
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add process and thread information
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread
        
        # Add any extra fields from the log call
        if hasattr(record, 'extra_fields'):
            log_record.update(record.extra_fields)


class PerformanceFilter(logging.Filter):
    """Filter for performance-related logs."""
    
    def filter(self, record):
        """Only allow performance logs through."""
        return hasattr(record, 'performance') and record.performance


class SecurityFilter(logging.Filter):
    """Filter for security-related logs."""
    
    def filter(self, record):
        """Only allow security logs through."""
        return hasattr(record, 'security') and record.security


class RequestLoggingMiddleware:
    """
    Middleware for request logging with correlation IDs.
    
    This should be integrated into FastAPI middleware stack.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """Process request with correlation ID."""
        if scope["type"] == "http":
            # Generate correlation ID for this request
            request_correlation_id = str(uuid.uuid4())
            correlation_id.set(request_correlation_id)
            
            # Log request start
            logger = logging.getLogger("gremlinsai.requests")
            start_time = time.time()
            
            logger.info(
                "Request started",
                extra={
                    'extra_fields': {
                        'request_method': scope.get('method'),
                        'request_path': scope.get('path'),
                        'request_query': scope.get('query_string', b'').decode(),
                        'client_ip': scope.get('client', ['unknown'])[0] if scope.get('client') else 'unknown',
                        'user_agent': dict(scope.get('headers', [])).get(b'user-agent', b'').decode(),
                        'event_type': 'request_start'
                    }
                }
            )
            
            # Process request
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    # Log response
                    duration = time.time() - start_time
                    status_code = message.get("status", 0)
                    
                    log_level = logging.INFO
                    if status_code >= 400:
                        log_level = logging.WARNING
                    if status_code >= 500:
                        log_level = logging.ERROR
                    
                    logger.log(
                        log_level,
                        "Request completed",
                        extra={
                            'extra_fields': {
                                'request_method': scope.get('method'),
                                'request_path': scope.get('path'),
                                'response_status': status_code,
                                'response_time_ms': round(duration * 1000, 2),
                                'event_type': 'request_end'
                            }
                        }
                    )
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


def setup_logging(
    environment: str = "development",
    log_level: str = "INFO",
    enable_json_logging: bool = True,
    log_file: Optional[str] = None
) -> None:
    """
    Set up structured logging configuration.
    
    Args:
        environment: Deployment environment (development, staging, production)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json_logging: Whether to use JSON formatting
        log_file: Optional log file path
    """
    
    # Base logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
                "format": "%(timestamp)s %(level)s %(logger)s %(message)s"
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "filters": {
            "correlation_id": {
                "()": CorrelationIdFilter
            },
            "performance": {
                "()": PerformanceFilter
            },
            "security": {
                "()": SecurityFilter
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured" if enable_json_logging else "simple",
                "filters": ["correlation_id"],
                "stream": sys.stdout
            }
        },
        "loggers": {
            "gremlinsai": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "gremlinsai.requests": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "gremlinsai.performance": {
                "level": "INFO",
                "handlers": ["console"],
                "filters": ["performance"],
                "propagate": False
            },
            "gremlinsai.security": {
                "level": "WARNING",
                "handlers": ["console"],
                "filters": ["security"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "WARNING",  # Reduce noise, we have our own request logging
                "handlers": ["console"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"]
        }
    }
    
    # Add file handler if log file is specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "structured" if enable_json_logging else "simple",
            "filters": ["correlation_id"],
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
        
        # Add file handler to all loggers
        for logger_config in config["loggers"].values():
            logger_config["handlers"].append("file")
        config["root"]["handlers"].append("file")
    
    # Environment-specific adjustments
    if environment == "production":
        # In production, reduce log levels for external libraries
        config["loggers"]["uvicorn"]["level"] = "WARNING"
        config["loggers"]["sqlalchemy"] = {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False
        }
        
        # Add performance and security logging in production
        if log_file:
            config["handlers"]["performance"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "structured",
                "filters": ["correlation_id", "performance"],
                "filename": log_file.replace(".log", "_performance.log"),
                "maxBytes": 10485760,
                "backupCount": 10
            }
            
            config["handlers"]["security"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "WARNING",
                "formatter": "structured",
                "filters": ["correlation_id", "security"],
                "filename": log_file.replace(".log", "_security.log"),
                "maxBytes": 10485760,
                "backupCount": 10
            }
            
            config["loggers"]["gremlinsai.performance"]["handlers"] = ["performance"]
            config["loggers"]["gremlinsai.security"]["handlers"] = ["security"]
    
    elif environment == "development":
        # In development, enable more verbose logging
        config["loggers"]["sqlalchemy"] = {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        }
        
        # Use simple formatting in development for readability
        if not enable_json_logging:
            for handler in config["handlers"].values():
                if "formatter" in handler:
                    handler["formatter"] = "simple"
    
    # Apply the configuration
    logging.config.dictConfig(config)
    
    # Log configuration success
    logger = logging.getLogger("gremlinsai.config")
    logger.info(
        "Logging configuration initialized",
        extra={
            'extra_fields': {
                'environment': environment,
                'log_level': log_level,
                'json_logging': enable_json_logging,
                'log_file': log_file,
                'event_type': 'logging_init'
            }
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"gremlinsai.{name}")


def set_correlation_id(correlation_id_value: str) -> None:
    """
    Set correlation ID for the current context.
    
    Args:
        correlation_id_value: Correlation ID to set
    """
    correlation_id.set(correlation_id_value)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.
    
    Returns:
        Current correlation ID or None
    """
    return correlation_id.get()


def log_performance(
    operation: str,
    duration_ms: float,
    success: bool = True,
    **kwargs
) -> None:
    """
    Log performance metrics.
    
    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds
        success: Whether operation was successful
        **kwargs: Additional fields to log
    """
    logger = logging.getLogger("gremlinsai.performance")
    
    extra_fields = {
        'operation': operation,
        'duration_ms': duration_ms,
        'success': success,
        'event_type': 'performance',
        **kwargs
    }
    
    logger.info(
        f"Performance: {operation}",
        extra={
            'performance': True,
            'extra_fields': extra_fields
        }
    )


def log_security_event(
    event_type: str,
    severity: str = "medium",
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **kwargs
) -> None:
    """
    Enhanced security event logging with monitoring and alerting.

    Args:
        event_type: Type of security event (authentication_failed, authorization_denied, etc.)
        severity: Event severity (low, medium, high, critical)
        user_id: User ID if applicable
        ip_address: IP address if applicable
        **kwargs: Additional fields to log (session_id, endpoint, method, etc.)
    """
    logger = logging.getLogger("gremlinsai.security")

    # Generate correlation ID for tracking related events
    correlation_id = str(uuid.uuid4())

    extra_fields = {
        'event_type': 'security',
        'security_event_type': event_type,
        'severity': severity,
        'user_id': user_id,
        'ip_address': ip_address,
        'correlation_id': correlation_id,
        'timestamp': datetime.utcnow().isoformat(),
        'user_agent': kwargs.get('user_agent'),
        'session_id': kwargs.get('session_id'),
        'endpoint': kwargs.get('endpoint'),
        'method': kwargs.get('method'),
        'status_code': kwargs.get('status_code'),
        **kwargs
    }

    # Map severity to log level
    level_map = {
        'low': logging.INFO,
        'medium': logging.WARNING,
        'high': logging.ERROR,
        'critical': logging.CRITICAL
    }

    log_level = level_map.get(severity, logging.WARNING)

    logger.log(
        log_level,
        f"Security event: {event_type}",
        extra={
            'security': True,
            'extra_fields': extra_fields
        }
    )

    # Send to security monitoring system for critical events
    if severity in ['high', 'critical']:
        _send_to_security_monitoring(extra_fields)


def _send_to_security_monitoring(event_data: Dict[str, Any]):
    """Send security events to external monitoring system."""
    try:
        # Log to dedicated security events logger
        security_events_logger = logging.getLogger("gremlinsai.security_events")
        security_events_logger.critical(f"SECURITY_ALERT: {json.dumps(event_data)}")

        # Check for critical events that need immediate alerting
        critical_events = [
            "authentication_brute_force",
            "authorization_privilege_escalation",
            "data_exfiltration_attempt",
            "sql_injection_attempt",
            "xss_attempt",
            "suspicious_file_upload",
            "admin_access_anomaly",
            "rate_limit_exceeded",
            "invalid_token_repeated"
        ]

        if (event_data.get("security_event_type") in critical_events or
            event_data.get("severity") == "critical"):
            _trigger_security_alert(event_data)

    except Exception as e:
        # Don't let security logging failures break the application
        fallback_logger = logging.getLogger("gremlinsai.security_fallback")
        fallback_logger.error(f"Failed to send security event to monitoring: {e}")


def _trigger_security_alert(event_data: Dict[str, Any]):
    """Trigger immediate security alert for critical events."""
    try:
        alert_logger = logging.getLogger("gremlinsai.security_alerts")
        alert_data = {
            "alert_type": "SECURITY_INCIDENT",
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_data,
            "requires_immediate_attention": True,
            "alert_id": str(uuid.uuid4())
        }

        alert_logger.critical(f"SECURITY_ALERT: {json.dumps(alert_data)}")

        # TODO: Integrate with alerting system (PagerDuty, Slack, email, etc.)

    except Exception as e:
        # Fallback logging
        fallback_logger = logging.getLogger("gremlinsai.security_fallback")
        fallback_logger.critical(f"CRITICAL: Security alert system failed. Original event: {event_data}. Error: {e}")


def log_input_validation_failure(
    field_name: str,
    field_value: str,
    validation_error: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    endpoint: Optional[str] = None
):
    """Log input validation failures for security monitoring."""
    potential_attack = _detect_potential_attack(field_value, validation_error)
    severity = "high" if potential_attack else "medium"

    log_security_event(
        event_type="input_validation_failure",
        severity=severity,
        user_id=user_id,
        ip_address=ip_address,
        field_name=field_name,
        field_value=field_value[:100] if field_value else None,  # Truncate for security
        validation_error=validation_error,
        endpoint=endpoint,
        potential_attack=potential_attack
    )


def _detect_potential_attack(field_value: str, validation_error: str) -> Optional[str]:
    """Detect potential attack patterns in input validation failures."""
    if not field_value:
        return None

    field_value_lower = field_value.lower()

    # SQL Injection patterns
    sql_patterns = ["'", "union", "select", "drop", "insert", "update", "delete", "--", "/*"]
    if any(pattern in field_value_lower for pattern in sql_patterns):
        return "sql_injection_attempt"

    # XSS patterns
    xss_patterns = ["<script", "javascript:", "onerror", "onload", "alert(", "document.cookie"]
    if any(pattern in field_value_lower for pattern in xss_patterns):
        return "xss_attempt"

    # Command injection patterns
    cmd_patterns = [";", "&&", "||", "|", "`", "$(", "${"]
    if any(pattern in field_value for pattern in cmd_patterns):
        return "command_injection_attempt"

    # Path traversal patterns
    if "../" in field_value or "..\\" in field_value:
        return "path_traversal_attempt"

    return None


def log_suspicious_activity(
    activity_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **kwargs
):
    """Log suspicious activity that may indicate security threats."""
    log_security_event(
        event_type="suspicious_activity",
        severity="high",
        user_id=user_id,
        ip_address=ip_address,
        activity_type=activity_type,
        **kwargs
    )
