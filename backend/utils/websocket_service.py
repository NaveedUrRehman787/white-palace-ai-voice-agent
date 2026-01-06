"""
WebSocket service for real-time updates using Flask-SocketIO
"""

import os
import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from config.database import execute_query
from config.restaurant_config import RESTAURANT_CONFIG
import json

logger = logging.getLogger(__name__)

# Initialize SocketIO (will be set by app.py)
socketio = None

def init_socketio(app):
    """Initialize SocketIO with Flask app"""
    global socketio
    socketio = SocketIO(app, cors_allowed_origins=[
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:5173",
        "http://localhost:5174"
    ])
    return socketio

def emit_order_status_update(order_id, order_data):
    """Emit order status update to connected clients"""
    try:
        room = f"order_{order_id}"
        event_data = {
            "type": "order_status_update",
            "orderId": order_id,
            "order": order_data,
            "timestamp": json.dumps({"$date": None})  # Will be set by client
        }

        # Emit to order-specific room
        socketio.emit("order_update", event_data, room=room)

        # Also emit to general orders room for admin dashboard
        socketio.emit("order_update", event_data, room="orders_admin")

        logger.info(f"Emitted order status update for order {order_id}")

    except Exception as e:
        logger.error(f"Error emitting order status update: {e}")

def emit_reservation_status_update(reservation_id, reservation_data):
    """Emit reservation status update to connected clients"""
    try:
        room = f"reservation_{reservation_id}"
        event_data = {
            "type": "reservation_status_update",
            "reservationId": reservation_id,
            "reservation": reservation_data,
            "timestamp": json.dumps({"$date": None})
        }

        # Emit to reservation-specific room
        socketio.emit("reservation_update", event_data, room=room)

        # Emit to general reservations room for admin dashboard
        socketio.emit("reservation_update", event_data, room="reservations_admin")

        logger.info(f"Emitted reservation status update for reservation {reservation_id}")

    except Exception as e:
        logger.error(f"Error emitting reservation status update: {e}")

def emit_payment_status_update(order_id, payment_data):
    """Emit payment status update"""
    try:
        room = f"order_{order_id}"
        event_data = {
            "type": "payment_status_update",
            "orderId": order_id,
            "payment": payment_data,
            "timestamp": json.dumps({"$date": None})
        }

        socketio.emit("payment_update", event_data, room=room)
        socketio.emit("payment_update", event_data, room="payments_admin")

        logger.info(f"Emitted payment status update for order {order_id}")

    except Exception as e:
        logger.error(f"Error emitting payment status update: {e}")

def emit_inventory_alert(menu_item_id, current_stock, minimum_stock):
    """Emit low inventory alert"""
    try:
        event_data = {
            "type": "inventory_alert",
            "menuItemId": menu_item_id,
            "currentStock": current_stock,
            "minimumStock": minimum_stock,
            "timestamp": json.dumps({"$date": None})
        }

        socketio.emit("inventory_alert", event_data, room="inventory_admin")
        logger.info(f"Emitted inventory alert for menu item {menu_item_id}")

    except Exception as e:
        logger.error(f"Error emitting inventory alert: {e}")

# SocketIO event handlers
def register_socketio_events(socketio):
    """Register SocketIO event handlers"""

    @socketio.on('connect')
    def handle_connect():
        logger.info("Client connected to WebSocket")

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info("Client disconnected from WebSocket")

    @socketio.on('join_order_room')
    def handle_join_order_room(data):
        """Join order-specific room for real-time updates"""
        order_id = data.get('orderId')
        if order_id:
            room = f"order_{order_id}"
            join_room(room)
            logger.info(f"Client joined order room: {room}")

    @socketio.on('leave_order_room')
    def handle_leave_order_room(data):
        """Leave order-specific room"""
        order_id = data.get('orderId')
        if order_id:
            room = f"order_{order_id}"
            leave_room(room)
            logger.info(f"Client left order room: {room}")

    @socketio.on('join_reservation_room')
    def handle_join_reservation_room(data):
        """Join reservation-specific room for real-time updates"""
        reservation_id = data.get('reservationId')
        if reservation_id:
            room = f"reservation_{reservation_id}"
            join_room(room)
            logger.info(f"Client joined reservation room: {room}")

    @socketio.on('leave_reservation_room')
    def handle_leave_reservation_room(data):
        """Leave reservation-specific room"""
        reservation_id = data.get('reservationId')
        if reservation_id:
            room = f"reservation_{reservation_id}"
            leave_room(room)
            logger.info(f"Client left reservation room: {room}")

    @socketio.on('join_admin_rooms')
    def handle_join_admin_rooms():
        """Join admin rooms for real-time dashboard updates"""
        join_room("orders_admin")
        join_room("reservations_admin")
        join_room("payments_admin")
        join_room("inventory_admin")
        logger.info("Client joined admin rooms")

    @socketio.on('leave_admin_rooms')
    def handle_leave_admin_rooms():
        """Leave admin rooms"""
        leave_room("orders_admin")
        leave_room("reservations_admin")
        leave_room("payments_admin")
        leave_room("inventory_admin")
        logger.info("Client left admin rooms")

# Helper functions for emitting updates from various parts of the app
def notify_order_update(order_id):
    """Fetch order data and emit update"""
    try:
        from routes.orders import format_order
        sql = """
            SELECT id, restaurant_id, order_number, customer_phone, customer_name,
                   order_items, subtotal, tax, total_price, status, order_type,
                   special_requests, delivery_address, estimated_ready_time,
                   completed_at, created_at, updated_at
            FROM orders WHERE id = %s AND restaurant_id = %s
        """
        order = execute_query(sql, (order_id, RESTAURANT_CONFIG["id"]), fetch_one=True)
        if order:
            order_data = format_order(order)
            emit_order_status_update(order_id, order_data)
    except Exception as e:
        logger.error(f"Error notifying order update: {e}")

def notify_reservation_update(reservation_id):
    """Fetch reservation data and emit update"""
    try:
        from routes.reservations import format_reservation
        sql = """
            SELECT id, restaurant_id, reservation_number, customer_phone, customer_name,
                   customer_email, party_size, reservation_date, reservation_time,
                   status, special_requests, notes, created_at, updated_at
            FROM reservations WHERE id = %s AND restaurant_id = %s
        """
        reservation = execute_query(sql, (reservation_id, RESTAURANT_CONFIG["id"]), fetch_one=True)
        if reservation:
            reservation_data = format_reservation(reservation)
            emit_reservation_status_update(reservation_id, reservation_data)
    except Exception as e:
        logger.error(f"Error notifying reservation update: {e}")

def notify_payment_update(order_id):
    """Fetch payment data and emit update"""
    try:
        from routes.payments import format_payment
        sql = """
            SELECT id, order_id, stripe_payment_intent_id, amount, currency,
                   status, payment_method, customer_email, metadata,
                   created_at, updated_at
            FROM payments WHERE order_id = %s AND restaurant_id = %s
            ORDER BY created_at DESC LIMIT 1
        """
        payment = execute_query(sql, (order_id, RESTAURANT_CONFIG["id"]), fetch_one=True)
        if payment:
            payment_data = format_payment(payment)
            emit_payment_status_update(order_id, payment_data)
    except Exception as e:
        logger.error(f"Error notifying payment update: {e}")

def check_inventory_alerts():
    """Check for low inventory and emit alerts"""
    try:
        sql = """
            SELECT id, name, current_stock, minimum_stock
            FROM inventory i
            JOIN menu_items m ON i.menu_item_id = m.id
            WHERE i.restaurant_id = %s AND i.current_stock <= i.minimum_stock
        """
        low_stock_items = execute_query(sql, (RESTAURANT_CONFIG["id"],), fetch_all=True)

        for item in low_stock_items:
            if isinstance(item, dict):
                menu_item_id = item.get("id")
                current_stock = item.get("current_stock", 0)
                minimum_stock = item.get("minimum_stock", 0)
            else:
                menu_item_id = item[0]
                current_stock = item[2]
                minimum_stock = item[3]

            emit_inventory_alert(menu_item_id, current_stock, minimum_stock)

    except Exception as e:
        logger.error(f"Error checking inventory alerts: {e}")
