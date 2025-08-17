# app/tools/datetime_tool.py
"""
Date and time operations tool with various datetime manipulations.

Features:
- Current date/time retrieval
- Date/time formatting and parsing
- Date arithmetic (add/subtract days, hours, etc.)
- Timezone conversions
- Date comparisons
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Union
from .base_tool import tool_wrapper, ToolResult, validate_input

logger = logging.getLogger(__name__)


def parse_datetime_string(date_string: str) -> datetime:
    """Parse datetime string with multiple format attempts."""
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M',
        '%m/%d/%Y',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S.%fZ'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse datetime string: {date_string}")


@tool_wrapper("datetime_tool")
def datetime_operation(operation: str, **kwargs) -> ToolResult:
    """
    Perform various date and time operations.
    
    Args:
        operation: Operation to perform
        **kwargs: Additional parameters for specific operations
        
    Available Operations:
    - 'now': Get current date/time
    - 'today': Get today's date
    - 'format': Format a datetime (datetime_str, format)
    - 'parse': Parse datetime string (datetime_str)
    - 'add': Add time to datetime (datetime_str, days, hours, minutes, seconds)
    - 'subtract': Subtract time from datetime (datetime_str, days, hours, minutes, seconds)
    - 'difference': Calculate difference between two datetimes (datetime1, datetime2)
    - 'compare': Compare two datetimes (datetime1, datetime2)
    - 'weekday': Get weekday name (datetime_str)
    - 'timestamp': Convert to Unix timestamp (datetime_str)
    - 'from_timestamp': Convert from Unix timestamp (timestamp)
    
    Returns:
        ToolResult with datetime operation result
        
    Examples:
        datetime_operation("now")
        datetime_operation("format", datetime_str="2023-01-01 12:00:00", format="%B %d, %Y")
        datetime_operation("add", datetime_str="2023-01-01", days=7)
    """
    try:
        # Validate operation
        operation = validate_input(operation, str, "operation")
        operation = operation.lower().strip()
        
        logger.info(f"Performing datetime operation: {operation}")
        
        if operation == 'now':
            result = datetime.utcnow().isoformat()
            
        elif operation == 'today':
            result = datetime.utcnow().date().isoformat()
            
        elif operation == 'format':
            datetime_str = kwargs.get('datetime_str')
            format_str = kwargs.get('format', '%Y-%m-%d %H:%M:%S')
            
            if not datetime_str:
                raise ValueError("datetime_str parameter required for format operation")
            
            dt = parse_datetime_string(datetime_str)
            result = dt.strftime(format_str)
            
        elif operation == 'parse':
            datetime_str = kwargs.get('datetime_str')
            
            if not datetime_str:
                raise ValueError("datetime_str parameter required for parse operation")
            
            dt = parse_datetime_string(datetime_str)
            result = {
                'parsed_datetime': dt.isoformat(),
                'year': dt.year,
                'month': dt.month,
                'day': dt.day,
                'hour': dt.hour,
                'minute': dt.minute,
                'second': dt.second,
                'weekday': dt.strftime('%A'),
                'month_name': dt.strftime('%B')
            }
            
        elif operation in ['add', 'subtract']:
            datetime_str = kwargs.get('datetime_str')
            
            if not datetime_str:
                raise ValueError(f"datetime_str parameter required for {operation} operation")
            
            dt = parse_datetime_string(datetime_str)
            
            # Get time components
            days = kwargs.get('days', 0)
            hours = kwargs.get('hours', 0)
            minutes = kwargs.get('minutes', 0)
            seconds = kwargs.get('seconds', 0)
            weeks = kwargs.get('weeks', 0)
            
            # Create timedelta
            delta = timedelta(
                days=days,
                hours=hours,
                minutes=minutes,
                seconds=seconds,
                weeks=weeks
            )
            
            # Apply operation
            if operation == 'add':
                new_dt = dt + delta
            else:  # subtract
                new_dt = dt - delta
            
            result = {
                'original_datetime': dt.isoformat(),
                'new_datetime': new_dt.isoformat(),
                'operation': operation,
                'delta': {
                    'days': days,
                    'hours': hours,
                    'minutes': minutes,
                    'seconds': seconds,
                    'weeks': weeks
                }
            }
            
        elif operation == 'difference':
            datetime1 = kwargs.get('datetime1')
            datetime2 = kwargs.get('datetime2')
            
            if not datetime1 or not datetime2:
                raise ValueError("Both datetime1 and datetime2 parameters required for difference operation")
            
            dt1 = parse_datetime_string(datetime1)
            dt2 = parse_datetime_string(datetime2)
            
            diff = dt2 - dt1
            
            result = {
                'datetime1': dt1.isoformat(),
                'datetime2': dt2.isoformat(),
                'difference_seconds': diff.total_seconds(),
                'difference_days': diff.days,
                'difference_hours': diff.total_seconds() / 3600,
                'difference_minutes': diff.total_seconds() / 60,
                'human_readable': str(diff)
            }
            
        elif operation == 'compare':
            datetime1 = kwargs.get('datetime1')
            datetime2 = kwargs.get('datetime2')
            
            if not datetime1 or not datetime2:
                raise ValueError("Both datetime1 and datetime2 parameters required for compare operation")
            
            dt1 = parse_datetime_string(datetime1)
            dt2 = parse_datetime_string(datetime2)
            
            if dt1 < dt2:
                comparison = "earlier"
            elif dt1 > dt2:
                comparison = "later"
            else:
                comparison = "equal"
            
            result = {
                'datetime1': dt1.isoformat(),
                'datetime2': dt2.isoformat(),
                'comparison': f"datetime1 is {comparison} than datetime2",
                'are_equal': dt1 == dt2,
                'datetime1_is_earlier': dt1 < dt2,
                'datetime1_is_later': dt1 > dt2
            }
            
        elif operation == 'weekday':
            datetime_str = kwargs.get('datetime_str')
            
            if not datetime_str:
                raise ValueError("datetime_str parameter required for weekday operation")
            
            dt = parse_datetime_string(datetime_str)
            
            result = {
                'datetime': dt.isoformat(),
                'weekday_name': dt.strftime('%A'),
                'weekday_short': dt.strftime('%a'),
                'weekday_number': dt.weekday(),  # 0=Monday, 6=Sunday
                'is_weekend': dt.weekday() >= 5
            }
            
        elif operation == 'timestamp':
            datetime_str = kwargs.get('datetime_str')
            
            if not datetime_str:
                raise ValueError("datetime_str parameter required for timestamp operation")
            
            dt = parse_datetime_string(datetime_str)
            timestamp = dt.timestamp()
            
            result = {
                'datetime': dt.isoformat(),
                'unix_timestamp': timestamp,
                'unix_timestamp_int': int(timestamp)
            }
            
        elif operation == 'from_timestamp':
            timestamp = kwargs.get('timestamp')
            
            if timestamp is None:
                raise ValueError("timestamp parameter required for from_timestamp operation")
            
            try:
                timestamp = float(timestamp)
            except (ValueError, TypeError):
                raise ValueError("timestamp must be a number")
            
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            result = {
                'unix_timestamp': timestamp,
                'datetime': dt.isoformat(),
                'formatted': dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'weekday': dt.strftime('%A')
            }
            
        else:
            available_ops = [
                'now', 'today', 'format', 'parse', 'add', 'subtract',
                'difference', 'compare', 'weekday', 'timestamp', 'from_timestamp'
            ]
            return ToolResult(
                success=False,
                result=None,
                error_message=f"Unknown operation '{operation}'. Available operations: {', '.join(available_ops)}"
            )
        
        return ToolResult(
            success=True,
            result=result,
            metadata={
                "operation": operation,
                "kwargs": kwargs
            }
        )
        
    except Exception as e:
        error_msg = f"Datetime operation '{operation}' failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return ToolResult(
            success=False,
            result=None,
            error_message=error_msg
        )


def get_datetime_help() -> str:
    """Get help text for the datetime tool."""
    return """
DateTime Tool Help:

Usage:
- datetime_operation("operation", param=value)

Available Operations:

Current Time:
- 'now': Get current UTC datetime
- 'today': Get today's date

Formatting & Parsing:
- 'format': Format datetime (datetime_str, format)
- 'parse': Parse datetime string (datetime_str)

Arithmetic:
- 'add': Add time (datetime_str, days=0, hours=0, minutes=0, seconds=0, weeks=0)
- 'subtract': Subtract time (datetime_str, days=0, hours=0, minutes=0, seconds=0, weeks=0)

Comparison:
- 'difference': Calculate difference (datetime1, datetime2)
- 'compare': Compare two datetimes (datetime1, datetime2)

Utilities:
- 'weekday': Get weekday info (datetime_str)
- 'timestamp': Convert to Unix timestamp (datetime_str)
- 'from_timestamp': Convert from Unix timestamp (timestamp)

Examples:
- datetime_operation("now")
- datetime_operation("format", datetime_str="2023-01-01 12:00:00", format="%B %d, %Y")
- datetime_operation("add", datetime_str="2023-01-01", days=7, hours=2)
- datetime_operation("difference", datetime1="2023-01-01", datetime2="2023-01-08")

Supported Input Formats:
- ISO format: 2023-01-01T12:00:00
- Standard: 2023-01-01 12:00:00
- Date only: 2023-01-01
- US format: 01/01/2023
- And more...

Note: All operations use UTC timezone unless specified otherwise.
"""
