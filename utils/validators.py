"""
Input validation utilities for Fino application.
"""
from datetime import datetime
from flask import jsonify

def validate_numeric(value, field_name="value", min_val=0, max_val=None):
    """
    Validate and convert numeric input.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    
    Returns:
        float: The validated numeric value
    
    Raises:
        ValueError: If validation fails
    """
    try:
        num = float(value)
        if num < min_val:
            raise ValueError(f"{field_name} must be >= {min_val}")
        if max_val is not None and num > max_val:
            raise ValueError(f"{field_name} must be <= {max_val}")
        return num
    except (ValueError, TypeError) as e:
        if "could not convert" in str(e) or "invalid literal" in str(e):
            raise ValueError(f"Invalid {field_name}")
        raise

def validate_date(date_str):
    """
    Validate date format.
    
    Args:
        date_str: Date string in YYYY-MM-DD format, or None for today
    
    Returns:
        str: Validated date string in YYYY-MM-DD format
    
    Raises:
        ValueError: If date format is invalid
    """
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")

def validate_month_year(month, year):
    """
    Validate month and year parameters.
    
    Args:
        month: Month value (1-12) or None
        year: Year value (2000-2100) or None
    
    Returns:
        tuple: (validated_month, validated_year) as strings
    
    Raises:
        ValueError: If validation fails
    """
    validated_month = None
    validated_year = None
    
    if month:
        try:
            month_int = int(month)
            if not 1 <= month_int <= 12:
                raise ValueError("Month must be between 1 and 12")
            validated_month = f"{month_int:02d}"
        except (ValueError, TypeError):
            raise ValueError("Invalid month value")
    
    if year:
        try:
            year_int = int(year)
            if not 2000 <= year_int <= 2100:
                raise ValueError("Year must be between 2000 and 2100")
            validated_year = str(year_int)
        except (ValueError, TypeError):
            raise ValueError("Invalid year value")
    
    return validated_month, validated_year

def validate_string(value, field_name="field", min_length=1, max_length=200):
    """
    Validate string input.
    
    Args:
        value: The string to validate
        field_name: Name of the field for error messages
        min_length: Minimum allowed length
        max_length: Maximum allowed length
    
    Returns:
        str: The validated and stripped string
    
    Raises:
        ValueError: If validation fails
    """
    if not value:
        raise ValueError(f"{field_name} is required")
    
    value = str(value).strip()
    
    if len(value) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")
    if len(value) > max_length:
        raise ValueError(f"{field_name} must not exceed {max_length} characters")
    
    return value

def error_response(message, status_code=400):
    """
    Create standardized error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
    
    Returns:
        tuple: (jsonified response, status_code)
    """
    return jsonify({'error': str(message)}), status_code

def success_response(message, data=None, status_code=200):
    """
    Create standardized success response.
    
    Args:
        message: Success message
        data: Optional data to include
        status_code: HTTP status code
    
    Returns:
        tuple: (jsonified response, status_code)
    """
    response = {'message': message}
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code