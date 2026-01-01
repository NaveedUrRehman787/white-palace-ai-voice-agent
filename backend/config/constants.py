"""
Constants and enumerations for the application
"""

# HTTP Status Codes
HTTP_STATUS = {
    'OK': 200,
    'CREATED': 201,
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'CONFLICT': 409,
    'INTERNAL_SERVER_ERROR': 500,
    'SERVICE_UNAVAILABLE': 503
}

# Error Messages
ERROR_MESSAGES = {
    # General
    'INTERNAL_ERROR': 'Internal server error',
    'NOT_FOUND': 'Resource not found',
    'INVALID_REQUEST': 'Invalid request',
    'MISSING_FIELDS': 'Missing required fields',
    
    # Menu
    'MENU_ITEM_NOT_FOUND': 'Menu item not found',
    'MENU_ITEM_UNAVAILABLE': 'Menu item is currently unavailable',
    
    # Orders
    'ORDER_NOT_FOUND': 'Order not found',
    'ORDER_CREATE_FAILED': 'Failed to create order',
    'INVALID_ORDER_ITEMS': 'Invalid order items',
    'INSUFFICIENT_ITEMS': 'Order must contain at least one item',
    
    # Reservations
    'RESERVATION_NOT_FOUND': 'Reservation not found',
    'RESERVATION_CREATE_FAILED': 'Failed to create reservation',
    'INVALID_RESERVATION_DATE': 'Invalid reservation date or time',
    'RESTAURANT_CLOSED': 'Restaurant is closed at that time',
    'NO_AVAILABILITY': 'No tables available at that time',
    
    # Phone validation
    'INVALID_PHONE': 'Invalid phone number',
    'MISSING_PHONE': 'Phone number is required',
    
    # Voice/LiveKit
    'LIVEKIT_ERROR': 'LiveKit connection error',
    'INVALID_ROOM': 'Invalid room name',
    'MISSING_TOKEN': 'Missing access token'
}

# Success Messages
SUCCESS_MESSAGES = {
    'MENU_ITEMS_FETCHED': 'Menu items fetched successfully',
    'ORDER_CREATED': 'Order created successfully',
    'RESERVATION_CREATED': 'Reservation created successfully',
    'ROOM_CREATED': 'LiveKit room created successfully'
}

# Intent Types (for voice processing)
INTENT_TYPES = {
    'PLACE_ORDER': 'place_order',
    'MAKE_RESERVATION': 'make_reservation',
    'QUERY_MENU': 'query_menu',
    'QUERY_HOURS': 'query_hours',
    'QUERY_CONTACT': 'query_contact',
    'CHECK_ORDER_STATUS': 'check_order_status',
    'CANCEL_ORDER': 'cancel_order',
    'CANCEL_RESERVATION': 'cancel_reservation',
    'UNKNOWN': 'unknown'
}

# Order Status
ORDER_STATUS = {
    'PENDING': 'pending',
    'CONFIRMED': 'confirmed',
    'PREPARING': 'preparing',
    'READY': 'ready',
    'COMPLETED': 'completed',
    'CANCELLED': 'cancelled'
}

# Reservation Status
RESERVATION_STATUS = {
    'PENDING': 'pending',
    'CONFIRMED': 'confirmed',
    'CHECKED_IN': 'checked_in',
    'COMPLETED': 'completed',
    'CANCELLED': 'cancelled',
    'NO_SHOW': 'no_show'
}

# Default values
DEFAULTS = {
    'ITEMS_PER_PAGE': 50,
    'QUERY_TIMEOUT': 5000,  # milliseconds
    'MAX_RETRIES': 3,
    'CACHE_TTL': 300  # seconds
}

# Twilio Message Templates
TWILIO_MESSAGES = {
    'ORDER_CONFIRMATION': 'Your order #{order_id} has been confirmed. Estimated ready time: {ready_time}. Thank you!',
    'ORDER_READY': 'Your order #{order_id} is ready for {order_type}. Thank you for choosing White Palace Grill!',
    'RESERVATION_CONFIRMATION': 'Your reservation for {party_size} at {time} on {date} is confirmed. Reservation #{res_id}',
    'VOICE_CALL_GREETING': 'Welcome to White Palace Grill! How can we help you today?'
}

# LiveKit configuration
LIVEKIT_CONFIG = {
    'GRANT_CAN_PUBLISH': True,
    'GRANT_CAN_PUBLISH_DATA': True,
    'GRANT_CAN_SUBSCRIBE': True,
    'GRANT_CAN_PUBLISH_SOURCES': ['microphone', 'screen_share'],
    'GRANT_INGEST': False
}

