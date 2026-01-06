"""
White Palace Grill - AI Voice Agent Backend
Flask application with LiveKit + Twilio integration
"""

import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify
from flask import g
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import os
import logging
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Import configurations and utilities
from config.database import init_db
from config.restaurant_config import RESTAURANT_CONFIG
from config.constants import HTTP_STATUS, ERROR_MESSAGES
from middleware.error_handler import error_handler
from routes.menu import menu_bp
from routes.orders import orders_bp
from routes.reservations import reservations_bp
from routes.payments import payments_bp
from routes.voice import voice_bp
from routes.twilio_webhooks import twilio_bp
from routes.agent import agent_bp
from routes.admin_auth import admin_bp
from routes.customer_auth import customer_bp
from utils.websocket_service import init_socketio, register_socketio_events

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize Database
try:
    init_db()
    logger.info('✅ Database initialized at startup')
except Exception as e:
    logger.error(f'❌ Failed to initialize database at startup: {e}')

# Initialize SocketIO
socketio = init_socketio(app)
register_socketio_events(socketio)

# Enable CORS for both Flask and SocketIO
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5000", "http://localhost:5173", "http://localhost:5174"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Register blueprints (routes)
app.register_blueprint(menu_bp, url_prefix='/api/menu')
app.register_blueprint(orders_bp, url_prefix='/api/orders')
app.register_blueprint(reservations_bp, url_prefix='/api/reservations')
app.register_blueprint(payments_bp, url_prefix='/api/payments')
app.register_blueprint(voice_bp, url_prefix='/api/voice')
app.register_blueprint(twilio_bp, url_prefix='/api/twilio')
app.register_blueprint(agent_bp, url_prefix="/api/agent")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(customer_bp, url_prefix="/api/customer")



# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        from config.database import get_db_cursor
        with get_db_cursor() as cursor:
            cursor.execute('SELECT NOW()')
        
        return jsonify({
            'status': 'OK',
            'restaurant': RESTAURANT_CONFIG['name'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0',
            'database': 'connected'
        }), HTTP_STATUS['OK']
    except Exception as e:
        logger.error(f'Health check failed: {str(e)}')
        return jsonify({
            'status': 'ERROR',
            'message': 'Database connection failed',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), HTTP_STATUS['SERVICE_UNAVAILABLE']

# Restaurant info endpoint
@app.route('/api/restaurant', methods=['GET'])
def get_restaurant():
    """Get restaurant information"""
    return jsonify({
        'id': RESTAURANT_CONFIG['id'],
        'name': RESTAURANT_CONFIG['name'],
        'phone': RESTAURANT_CONFIG['phone'],
        'address': RESTAURANT_CONFIG['address'],
        'city': RESTAURANT_CONFIG['city'],
        'state': RESTAURANT_CONFIG['state'],
        'zipCode': RESTAURANT_CONFIG['zip_code'],
        'email': RESTAURANT_CONFIG['email'],
        'website': RESTAURANT_CONFIG['website'],
        'established': RESTAURANT_CONFIG['established_year'],
        'hours': RESTAURANT_CONFIG['hours'],
        'services': RESTAURANT_CONFIG['services'],
        'timezone': RESTAURANT_CONFIG['timezone']
    }), HTTP_STATUS['OK']

# 404 handler
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource does not exist',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), HTTP_STATUS['NOT_FOUND']

# 500 handler
@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f'Internal server error: {str(error)}')
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), HTTP_STATUS['INTERNAL_SERVER_ERROR']

# Register error handler middleware
app.register_error_handler(Exception, error_handler)

# Initialize database on startup
@app.before_request
def before_request():
    """Initialize database connection before each request"""
    pass

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection after each request"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    # Initialize database
    init_db()
    logger.info('✅ Database initialized')
    
    # Start Flask server
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f'''
╔════════════════════════════════════════════╗
║  🍔 White Palace Grill - AI Voice Agent   ║
║  Server running on port {port}           ║
║  Restaurant: {RESTAURANT_CONFIG['name']}    ║
║  Stack: Python + Flask + LiveKit + Twilio ║
╚════════════════════════════════════════════╝
    ''')
    
    logger.info(f'Health check: http://localhost:{port}/api/health')
    logger.info(f'Restaurant info: http://localhost:{port}/api/restaurant')
    # close_connection()
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug
    )
