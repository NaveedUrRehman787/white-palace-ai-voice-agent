"""
Error handling middleware for Flask application
"""

from flask import jsonify
from functools import wraps
import logging
from datetime import datetime
from config.constants import HTTP_STATUS, ERROR_MESSAGES

logger = logging.getLogger(__name__)

def error_handler(error):
    """
    Global error handler for Flask application
    
    Args:
        error: Exception object
    
    Returns:
        JSON response with error details
    """
    logger.error(f'❌ Error: {str(error)}', exc_info=True)
    
    # Database errors
    if hasattr(error, 'pgcode'):
        if error.pgcode == '23505':  # Unique violation
            return jsonify({
                'error': 'Conflict',
                'message': 'Duplicate entry',
                'timestamp': datetime.utcnow().isoformat()
            }), HTTP_STATUS['CONFLICT']
        elif error.pgcode == '23502':  # Not null violation
            return jsonify({
                'error': 'Bad Request',
                'message': 'Missing required fields',
                'timestamp': datetime.utcnow().isoformat()
            }), HTTP_STATUS['BAD_REQUEST']
    
    # Validation errors
    if hasattr(error, 'name') and error.name == 'ValidationError':
        return jsonify({
            'error': 'Validation Error',
            'message': str(error),
            'timestamp': datetime.utcnow().isoformat()
        }), HTTP_STATUS['BAD_REQUEST']
    
    # Default error response
    status_code = getattr(error, 'code', HTTP_STATUS['INTERNAL_SERVER_ERROR'])
    return jsonify({
        'error': type(error).__name__,
        'message': str(error) or ERROR_MESSAGES['INTERNAL_ERROR'],
        'timestamp': datetime.utcnow().isoformat()
    }), status_code

def handle_exceptions(f):
    """
    Decorator to handle exceptions in route handlers
    
    Usage:
        @app.route('/api/endpoint')
        @handle_exceptions
        def endpoint():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return error_handler(e)
    
    return decorated_function

class ValidationError(Exception):
    """Custom validation error"""
    name = 'ValidationError'
    
    def __init__(self, message, status_code=HTTP_STATUS['BAD_REQUEST']):
        self.message = message
        self.code = status_code
        super().__init__(self.message)

