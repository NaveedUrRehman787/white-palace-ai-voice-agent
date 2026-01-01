"""
White Palace Grill configuration
All restaurant-specific settings
"""

import os
RESTAURANT_CONFIG = {
    # Basic Information
    'id': 1,
    'name': 'White Palace Grill',
    'phone': '(312) 939-7167',
    'address': '1159 S Canal St',
    'city': 'Chicago',
    'state': 'IL',
    'zip_code': '60607',
    'website': 'https://www.whitepalacechicago.com',
    'email': 'info@whitepalacechicago.com',
    'established_year': 1939,
    'timezone': 'America/Chicago',
    
    # Operating Hours (24-hour format)
    'hours': {
        'monday': {'open': '06:00', 'close': '23:00'},
        'tuesday': {'open': '06:00', 'close': '23:00'},
        'wednesday': {'open': '06:00', 'close': '23:00'},
        'thursday': {'open': '06:00', 'close': '23:00'},
        'friday': {'open': '06:00', 'close': '23:00'},
        'saturday': {'open': '07:00', 'close': '23:00'},
        'sunday': {'open': '07:00', 'close': '22:00'}
    },
    
    # Services Available
    'services': {
        'dine_in': True,
        'pickup': True,
        'delivery': True,
        'reservations': True,
        'voice_ordering': True
    },
    
    # Default values for orders
    'defaults': {
        'max_prep_time': 30,  # minutes
        'estimated_delivery_time': 45,  # minutes
        'estimated_pickup_time': 15,  # minutes
        'default_party_size': 2,
        'max_party_size': 20,
        'tax_rate': 0.0825
    },
    
    # Categories
    'categories': [
        'breakfast',
        'burgers',
        'sandwiches',
        'entrees',
        'sides',
        'soups',
        'salads',
        'desserts',
        'beverages'
    ],
    
    # Order types
    'order_types': ['dine-in', 'pickup', 'delivery'],
    
    # Reservation settings
    'reservation_settings': {
        'min_advance_notice': 15,  # minutes
        'max_advance_booking': 60 * 24 * 30,  # 30 days in minutes
        'default_duration': 90,  # minutes per reservation
        'tables_available': 25
    },
    
    # Twilio configuration
    'twilio': {
        'phone_number': os.getenv('TWILIO_PHONE_NUMBER'),  # Your Twilio number
        'account_sid': os.getenv('TWILIO_ACCOUNT_SID'),
        'auth_token': os.getenv('TWILIO_AUTH_TOKEN'),
    },
    
    # LiveKit configuration
    'livekit': {
        'url': os.getenv('LIVEKIT_URL', 'ws://localhost:7880'),
        'api_key': os.getenv('LIVEKIT_API_KEY'),
        'api_secret': os.getenv('LIVEKIT_API_SECRET'),
        'room_prefix': 'white_palace_'
    }
}

def is_restaurant_open(day_name=None):
    """
    Check if restaurant is currently open
    
    Args:
        day_name: Day name (optional, uses current day if not provided)
    
    Returns:
        Boolean indicating if restaurant is open
    """
    from datetime import datetime
    
    if not day_name:
        day_name = datetime.now().strftime('%A').lower()
    
    day_hours = RESTAURANT_CONFIG['hours'].get(day_name)
    
    if not day_hours:
        return False
    
    now = datetime.now().time()
    open_time = datetime.strptime(day_hours['open'], '%H:%M').time()
    close_time = datetime.strptime(day_hours['close'], '%H:%M').time()
    
    return open_time <= now < close_time

def get_estimated_ready_time(prep_time=10, order_type='pickup'):
    """
    Get estimated ready time for order
    
    Args:
        prep_time: Preparation time in minutes
        order_type: Type of order (pickup, delivery, dine-in)
    
    Returns:
        datetime object with estimated ready time
    """
    from datetime import datetime, timedelta
    
    now = datetime.now()
    buffer = RESTAURANT_CONFIG['defaults']['estimated_delivery_time'] \
        if order_type == 'delivery' \
        else RESTAURANT_CONFIG['defaults']['estimated_pickup_time']
    
    ready_time = now + timedelta(minutes=prep_time + buffer)
    return ready_time



