

"""
Input validation functions
"""

import re
from config.constants import ERROR_MESSAGES
from middleware.error_handler import ValidationError


def validate_phone_number(phone):
    """
    Validate phone number format

    Args:
        phone: Phone number string

    Returns:
        Cleaned phone number or raises ValidationError
    """
    if not phone:
        raise ValidationError(ERROR_MESSAGES['MISSING_PHONE'])

    # Remove non-numeric characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Check if valid length (10+ digits)
    if len(cleaned) < 10:
        raise ValidationError(ERROR_MESSAGES['INVALID_PHONE'])

    return cleaned


def validate_email(email):
    """Validate email format"""
    if not email:
        return True

    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(pattern, email):
        raise ValidationError('Invalid email format')

    return True


def validate_date(date_string):
    """Validate date format"""
    from datetime import datetime

    try:
        datetime.fromisoformat(date_string)
        return True
    except ValueError:
        raise ValidationError(ERROR_MESSAGES['INVALID_RESERVATION_DATE'])


def validate_order_items(items):
    """
    Validate order items

    For now (to allow AI agent placeholder items):
    - items must be a non-empty list
    - each item must be a dict
    - 'name' must be a non-empty string
    - 'quantity' must be a positive integer
    - menuItemId and price are NOT strictly validated

    Later you can tighten this once the agent maps items to real menu entries.
    """
    if not isinstance(items, list) or len(items) == 0:
        raise ValidationError(ERROR_MESSAGES['INSUFFICIENT_ITEMS'])

    for item in items:
        if not isinstance(item, dict):
            raise ValidationError(ERROR_MESSAGES['INVALID_ORDER_ITEMS'])

        # Name required
        name = item.get('name')
        if not name or not isinstance(name, str):
            raise ValidationError(ERROR_MESSAGES['INVALID_ORDER_ITEMS'])

        # Quantity must be positive integer
        quantity = item.get('quantity')
        if not isinstance(quantity, int) or quantity < 1:
            raise ValidationError(ERROR_MESSAGES['INVALID_ORDER_ITEMS'])

        # TEMPORARY RELAXATION:
        # - Allow menuItemId to be missing or zero
        # - Allow price to be missing or zero
        # This is to support early AI agent flows where items are not yet
        # mapped to real menu IDs and prices.
        # Uncomment/adjust below when ready to enforce strictly:
        #
        # menu_item_id = item.get('menuItemId')
        # if not isinstance(menu_item_id, int) or menu_item_id <= 0:
        #     raise ValidationError(ERROR_MESSAGES['INVALID_ORDER_ITEMS'])
        #
        # price = item.get('price')
        # if price is None or not isinstance(price, (int, float)) or price <= 0:
        #     raise ValidationError(ERROR_MESSAGES['INVALID_ORDER_ITEMS'])

    return True


def validate_reservation_data(data):
    """
    Validate reservation data

    Args:
        data: Reservation data dict

    Returns:
        True or raises ValidationError
    """
    required_fields = ['reservationDate', 'reservationTime', 'partySize', 'customerName', 'customerPhone']

    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(ERROR_MESSAGES['MISSING_FIELDS'])

    # Validate phone
    validate_phone_number(data['customerPhone'])

    # Validate date
    validate_date(data['reservationDate'])

    # Validate party size
    party_size = int(data.get('partySize', 0))
    if party_size < 1 or party_size > 20:
        raise ValidationError('Party size must be between 1 and 20')

    return True


def validate_order_data(data):
    """
    Validate order data

    Args:
        data: Order data dict

    Returns:
        True or raises ValidationError
    """
    required_fields = ['items', 'orderType', 'customerPhone']

    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(ERROR_MESSAGES['MISSING_FIELDS'])

    # Validate items
    validate_order_items(data['items'])

    # Validate phone
    validate_phone_number(data['customerPhone'])

    # Validate order type
    valid_types = ['dine-in', 'pickup', 'delivery']
    if data['orderType'] not in valid_types:
        raise ValidationError('Invalid order type')

    return True
