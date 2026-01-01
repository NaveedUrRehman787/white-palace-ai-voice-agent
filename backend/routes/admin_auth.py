"""
Admin Authentication Routes
Handles admin login with secure password verification.

Endpoints:
- POST /api/admin/login  -> Authenticate admin user
"""

from flask import Blueprint, jsonify, request, session
from config.constants import HTTP_STATUS
from middleware.error_handler import handle_exceptions, ValidationError
import hashlib
import secrets
import os
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

# In production, store this in a database with proper hashing
# For now, we use environment variable or a default (change this!)
ADMIN_PASSWORD_HASH = os.getenv(
    "ADMIN_PASSWORD_HASH",
    # Default password: "whitepalace2024" - SHA256 hashed
    # Generate new one with: python -c "import hashlib; print(hashlib.sha256('YOUR_PASSWORD'.encode()).hexdigest())"
    "a8f5f167f44f4964e6c998dee827110c039a00e0ad4a2f9b0d7b17d08ce7b839"  # whitepalace2024
)

# Store active sessions (in production, use Redis or database)
active_sessions = {}


def generate_session_token():
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str) -> bool:
    """Verify password against stored hash."""
    return hash_password(password) == ADMIN_PASSWORD_HASH


# ============================================
# POST /api/admin/login -> Admin Login
# ============================================
@admin_bp.route('/login', methods=['POST'])
@handle_exceptions
def admin_login():
    """
    Authenticate admin user.
    
    Expected JSON body:
    {
        "password": "admin_password"
    }
    
    Returns:
    {
        "status": "success",
        "token": "session_token",
        "expiresIn": 3600
    }
    """
    data = request.get_json() or {}
    password = data.get("password", "")
    
    if not password:
        raise ValidationError("Password is required", HTTP_STATUS["BAD_REQUEST"])
    
    if not verify_password(password):
        logger.warning("Failed admin login attempt")
        raise ValidationError("Invalid password", HTTP_STATUS["UNAUTHORIZED"])
    
    # Generate session token
    token = generate_session_token()
    
    # Store session (expires in 8 hours)
    active_sessions[token] = {
        "created_at": __import__('datetime').datetime.now().isoformat(),
        "expires_in": 8 * 60 * 60  # 8 hours in seconds
    }
    
    logger.info("Admin login successful")
    
    return jsonify({
        "status": "success",
        "token": token,
        "expiresIn": 8 * 60 * 60
    }), HTTP_STATUS["OK"]


# ============================================
# POST /api/admin/verify -> Verify Session Token
# ============================================
@admin_bp.route('/verify', methods=['POST'])
@handle_exceptions
def verify_session():
    """
    Verify if a session token is valid.
    
    Expected JSON body:
    {
        "token": "session_token"
    }
    """
    data = request.get_json() or {}
    token = data.get("token", "")
    
    if not token or token not in active_sessions:
        return jsonify({
            "status": "error",
            "valid": False
        }), HTTP_STATUS["UNAUTHORIZED"]
    
    return jsonify({
        "status": "success",
        "valid": True
    }), HTTP_STATUS["OK"]


# ============================================
# POST /api/admin/logout -> Logout
# ============================================
@admin_bp.route('/logout', methods=['POST'])
@handle_exceptions
def admin_logout():
    """
    Invalidate admin session.
    """
    data = request.get_json() or {}
    token = data.get("token", "")
    
    if token in active_sessions:
        del active_sessions[token]
    
    return jsonify({
        "status": "success",
        "message": "Logged out successfully"
    }), HTTP_STATUS["OK"]
