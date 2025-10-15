"""
Input validation utilities for Iknow application.
"""

from datetime import datetime
from flask import jsonify


def validate_numeric(value, field_name="value", min_val=0, max_val=None):
    """
    Validate and convert numeric input.
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {field_name}")

    if num < min_val:
        raise ValueError(f"{field_name} must be >= {min_val}")
    if max_val is not None and num > max_val:
        raise ValueError(f"{field_name} must be <= {max_val}")

    return num


def validate_date(date_str):
    """
    Validate date format (YYYY-MM-DD). Returns today's date if None/empty.
    """
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")
    return date_str


def validate_month_year(month=None, year=None):
    """
    Validate month (1-12) and year (2000-2100).
    Returns tuple of strings: (month, year)
    """
    def _validate_int(value, field, min_v, max_v):
        try:
            num = int(value)
            if not min_v <= num <= max_v:
                raise ValueError(f"{field.capitalize()} must be between {min_v} and {max_v}")
            return num
        except (ValueError, TypeError):
            raise ValueError(f"Invalid {field} value")

    validated_month = f"{_validate_int(month, 'month', 1, 12):02d}" if month else None
    validated_year = str(_validate_int(year, 'year', 2000, 2100)) if year else None

    return validated_month, validated_year


def validate_string(value, field_name="field", min_length=1, max_length=200):
    """
    Validate non-empty string input with length constraints.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")

    value = value.strip()
    length = len(value)

    if length < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")
    if length > max_length:
        raise ValueError(f"{field_name} must not exceed {max_length} characters")

    return value


def error_response(message, status_code=400):
    """
    Create standardized JSON error response.
    """
    return jsonify({'error': str(message)}), status_code


def success_response(message, data=None, status_code=200):
    """
    Create standardized JSON success response.
    """
    response = {'message': message}
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code
