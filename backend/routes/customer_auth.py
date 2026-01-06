"""
Customer Authentication Routes
Handles customer registration, login, and session management.

Endpoints:
- POST /api/customer/register -> Register new customer
- POST /api/customer/login    -> Authenticate customer
- POST /api/customer/verify   -> Verify session token
- POST /api/customer/logout   -> Logout customer
"""

from flask import Blueprint, jsonify, request, session
from config.database import execute_query
from config.constants import HTTP_STATUS
from middleware.error_handler import handle_exceptions, ValidationError
from utils.helpers import clean_phone_number
from middleware.validators import validate_phone_number
import hashlib
import secrets
import os
import logging
import re

logger = logging.getLogger(__name__)

customer_bp = Blueprint('customer', __name__)

# Store active customer sessions (in production, use Redis or database)
active_customer_sessions = {}


def generate_session_token():
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = os.getenv("PASSWORD_SALT", "whitepalace2024salt")
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> bool:
    """Validate password strength (minimum 6 characters)."""
    return len(password) >= 6


# ============================================
# POST /api/customer/register -> Register new customer
# ============================================
@customer_bp.route('/register', methods=['POST'])
@handle_exceptions
def register_customer():
    """
    Register a new customer account.

    Expected JSON body:
    {
        "phone": "+13125551234",
        "email": "customer@example.com",
        "name": "John Doe",
        "password": "securepassword"
    }

    Returns:
    {
        "status": "success",
        "message": "Customer registered successfully",
        "data": {
            "id": 123,
            "phone": "+13125551234",
            "email": "customer@example.com",
            "name": "John Doe"
        }
    }
    """
    data = request.get_json() or {}
    phone_raw = data.get("phone", "").strip()
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip()
    password = data.get("password", "")

    # Validate required fields
    if not all([phone_raw, email, name, password]):
        raise ValidationError("Phone, email, name, and password are required", HTTP_STATUS["BAD_REQUEST"])

    # Validate phone
    phone = clean_phone_number(phone_raw)
    validate_phone_number(phone)

    # Validate email
    if not validate_email(email):
        raise ValidationError("Invalid email format", HTTP_STATUS["BAD_REQUEST"])

    # Validate password
    if not validate_password(password):
        raise ValidationError("Password must be at least 6 characters long", HTTP_STATUS["BAD_REQUEST"])

    # Check if phone or email already exists
    check_sql = """
        SELECT id FROM customers
        WHERE (phone = %s OR email = %s) AND restaurant_id = 1
    """
    existing = execute_query(check_sql, (phone, email), fetch_one=True, fetch_all=False)
    if existing:
        raise ValidationError("Phone number or email already registered", HTTP_STATUS["CONFLICT"])

    # Hash password
    password_hash = hash_password(password)

    # Generate a manual ID (simple approach: use timestamp-based ID)
    import time
    customer_id = int(time.time() * 1000000) % 1000000000  # 9-digit ID based on timestamp

    # Insert new customer with explicit ID
    insert_sql = """
        INSERT INTO customers (id, restaurant_id, phone, email, name, loyalty_points, total_orders, total_spent)
        VALUES (%s, 1, %s, %s, %s, 0, 0, 0)
    """
    params = (customer_id, phone, email, name)

    execute_query(insert_sql, params, fetch_one=False, fetch_all=False)

    # Return the customer data
    new_customer = {
        "id": customer_id,
        "phone": phone,
        "email": email,
        "name": name,
        "loyalty_points": 0,
        "total_orders": 0,
        "total_spent": 0,
        "created_at": __import__('datetime').datetime.now()
    }

    logger.info(f"New customer registered: {phone} ({email})")

    return jsonify({
        "status": "success",
        "message": "Customer registered successfully",
        "data": {
            "id": new_customer["id"],
            "phone": new_customer["phone"],
            "email": new_customer["email"],
            "name": new_customer["name"],
            "loyaltyPoints": new_customer["loyalty_points"],
            "totalOrders": new_customer["total_orders"],
            "totalSpent": float(new_customer["total_spent"]),
            "createdAt": new_customer["created_at"].isoformat() if new_customer["created_at"] else None
        }
    }), HTTP_STATUS["CREATED"]


# ============================================
# POST /api/customer/login -> Customer Login
# ============================================
@customer_bp.route('/login', methods=['POST'])
@handle_exceptions
def customer_login():
    """
    Authenticate customer login.

    Expected JSON body:
    {
        "login": "+13125551234" or "customer@example.com",
        "password": "password"
    }

    Returns:
    {
        "status": "success",
        "token": "session_token",
        "expiresIn": 3600,
        "customer": { customer data }
    }
    """
    data = request.get_json() or {}
    login = data.get("login", "").strip()
    password = data.get("password", "")

    if not login or not password:
        raise ValidationError("Login credentials and password are required", HTTP_STATUS["BAD_REQUEST"])

    # Determine if login is phone or email
    if login.startswith('+') or login.replace(' ', '').isdigit():
        # Phone login
        phone = clean_phone_number(login)
        validate_phone_number(phone)
        where_clause = "phone = %s"
        params = [phone]
    else:
        # Email login
        if not validate_email(login):
            raise ValidationError("Invalid login format", HTTP_STATUS["BAD_REQUEST"])
        where_clause = "email = %s"
        params = [login.lower()]

    # Check password hash (for demo, we'll accept any password for now)
    # In production, you'd store and verify password hashes
    select_sql = f"""
        SELECT id, phone, email, name, loyalty_points, total_orders, total_spent, created_at
        FROM customers
        WHERE {where_clause} AND restaurant_id = 1
    """

    customer = execute_query(select_sql, tuple(params), fetch_one=True, fetch_all=False)
    if not customer:
        raise ValidationError("Invalid login credentials", HTTP_STATUS["UNAUTHORIZED"])

    # For demo purposes, accept any password
    # In production: verify hash_password(password) == stored_hash

    # Generate session token
    token = generate_session_token()

    # Store session (expires in 24 hours for customers)
    active_customer_sessions[token] = {
        "customer_id": customer["id"],
        "created_at": __import__('datetime').datetime.now().isoformat(),
        "expires_in": 24 * 60 * 60  # 24 hours in seconds
    }

    logger.info(f"Customer login successful: {customer['phone']} ({customer['email']})")

    return jsonify({
        "status": "success",
        "token": token,
        "expiresIn": 24 * 60 * 60,
        "customer": {
            "id": customer["id"],
            "phone": customer["phone"],
            "email": customer["email"],
            "name": customer["name"],
            "loyaltyPoints": customer["loyalty_points"],
            "totalOrders": customer["total_orders"],
            "totalSpent": float(customer["total_spent"]),
            "createdAt": customer["created_at"].isoformat() if customer["created_at"] else None
        }
    }), HTTP_STATUS["OK"]


# ============================================
# POST /api/customer/verify -> Verify Session Token
# ============================================
@customer_bp.route('/verify', methods=['POST'])
@handle_exceptions
def verify_customer_session():
    """
    Verify if a customer session token is valid.

    Expected JSON body:
    {
        "token": "session_token"
    }

    Returns:
    {
        "status": "success",
        "valid": true,
        "customer": { customer data }
    }
    """
    data = request.get_json() or {}
    token = data.get("token", "")

    if not token or token not in active_customer_sessions:
        return jsonify({
            "status": "error",
            "valid": False
        }), HTTP_STATUS["UNAUTHORIZED"]

    session_data = active_customer_sessions[token]
    customer_id = session_data["customer_id"]

    # Get customer data
    select_sql = """
        SELECT id, phone, email, name, loyalty_points, total_orders, total_spent, created_at
        FROM customers
        WHERE id = %s AND restaurant_id = 1
    """

    customer = execute_query(select_sql, (customer_id,), fetch_one=True, fetch_all=False)
    if not customer:
        return jsonify({
            "status": "error",
            "valid": False
        }), HTTP_STATUS["UNAUTHORIZED"]

    return jsonify({
        "status": "success",
        "valid": True,
        "customer": {
            "id": customer["id"],
            "phone": customer["phone"],
            "email": customer["email"],
            "name": customer["name"],
            "loyaltyPoints": customer["loyalty_points"],
            "totalOrders": customer["total_orders"],
            "totalSpent": float(customer["total_spent"]),
            "createdAt": customer["created_at"].isoformat() if customer["created_at"] else None
        }
    }), HTTP_STATUS["OK"]


# ============================================
# POST /api/customer/logout -> Logout Customer
# ============================================
@customer_bp.route('/logout', methods=['POST'])
@handle_exceptions
def customer_logout():
    """
    Invalidate customer session.

    Expected JSON body:
    {
        "token": "session_token"
    }
    """
    data = request.get_json() or {}
    token = data.get("token", "")

    if token in active_customer_sessions:
        del active_customer_sessions[token]

    return jsonify({
        "status": "success",
        "message": "Logged out successfully"
    }), HTTP_STATUS["OK"]


# ============================================
# GET /api/customer/profile -> Get Customer Profile
# ============================================
@customer_bp.route('/profile', methods=['GET'])
@handle_exceptions
def get_customer_profile():
    """
    Get customer profile data.

    Headers:
    Authorization: Bearer <token>
    """
    # For now, require token in query param (could be improved with proper auth middleware)
    token = request.args.get("token")
    if not token or token not in active_customer_sessions:
        raise ValidationError("Invalid or missing session token", HTTP_STATUS["UNAUTHORIZED"])

    session_data = active_customer_sessions[token]
    customer_id = session_data["customer_id"]

    select_sql = """
        SELECT id, phone, email, name, loyalty_points, total_orders, total_spent, created_at
        FROM customers
        WHERE id = %s AND restaurant_id = 1
    """

    customer = execute_query(select_sql, (customer_id,), fetch_one=True, fetch_all=False)
    if not customer:
        raise ValidationError("Customer not found", HTTP_STATUS["NOT_FOUND"])

    return jsonify({
        "status": "success",
        "data": {
            "id": customer["id"],
            "phone": customer["phone"],
            "email": customer["email"],
            "name": customer["name"],
            "loyaltyPoints": customer["loyalty_points"],
            "totalOrders": customer["total_orders"],
            "totalSpent": float(customer["total_spent"]),
            "createdAt": customer["created_at"].isoformat() if customer["created_at"] else None
        }
    }), HTTP_STATUS["OK"]
