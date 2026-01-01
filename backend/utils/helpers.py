"""
Helper functions for the application
"""

import uuid
from datetime import datetime, timedelta
import re

def generate_order_id():
    """Generate unique order ID"""
    return f"ORD-{int(datetime.now().timestamp())}-{str(uuid.uuid4())[:8]}".upper()

def generate_reservation_id():
    """Generate unique reservation ID"""
    return f"RES-{int(datetime.now().timestamp())}-{str(uuid.uuid4())[:8]}".upper()

def format_phone_number(phone):
    """
    Format phone number to (XXX) XXX-XXXX format
    
    Args:
        phone: Phone number string
    
    Returns:
        Formatted phone number
    """
    cleaned = re.sub(r'[^\d]', '', phone)
    
    if len(cleaned) == 10:
        return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
    
    return phone

def calculate_order_total(items, tax_rate=0.0825):
    """
    Calculate order total with tax
    
    Args:
        items: List of order items with price and quantity
        tax_rate: Tax rate (default 8.25%)
    
    Returns:
        Dict with subtotal, tax, and total
    """
    subtotal = sum(item.get('price', 0) * item.get('quantity', 0) for item in items)
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)
    
    return {
        'subtotal': round(subtotal, 2),
        'tax': tax,
        'total': total
    }

def calculate_estimated_ready_time(prep_time, buffer=10):
    """
    Calculate estimated ready time
    
    Args:
        prep_time: Preparation time in minutes
        buffer: Additional buffer time in minutes
    
    Returns:
        Datetime object with estimated ready time
    """
    now = datetime.now()
    ready_time = now + timedelta(minutes=prep_time + buffer)
    return ready_time

def is_time_slot_available(requested_time, booked_times, duration=90):
    """
    Check if time slot is available
    
    Args:
        requested_time: Requested time
        booked_times: List of booked time slots
        duration: Duration of booking in minutes
    
    Returns:
        Boolean indicating availability
    """
    requested_start = datetime.fromisoformat(requested_time)
    requested_end = requested_start + timedelta(minutes=duration)
    
    for booking in booked_times:
        booking_start = datetime.fromisoformat(booking['reservationTime'])
        booking_end = booking_start + timedelta(minutes=duration)
        
        # Check for overlap
        if (requested_start >= booking_start and requested_start < booking_end) or \
           (requested_end > booking_start and requested_end <= booking_end) or \
           (requested_start <= booking_start and requested_end >= booking_end):
            return False
    
    return True

def get_day_of_week(date_string):
    """
    Get day of week name
    
    Args:
        date_string: Date string in ISO format
    
    Returns:
        Day name (lowercase)
    """
    date = datetime.fromisoformat(date_string)
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return days[date.weekday()]

def format_datetime(date_obj):
    """Format datetime object to readable string"""
    return date_obj.strftime('%Y-%m-%d %H:%M:%S')

def clean_phone_number(phone):
    """Remove all non-numeric characters from phone number"""
    return re.sub(r'[^\d]', '', phone)

