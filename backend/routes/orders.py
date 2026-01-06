
"""
Orders API Routes
Handles creating, retrieving, updating, and cancelling orders.

Endpoints:
- POST   /api/orders                 -> Create new order
- GET    /api/orders/<id>            -> Get order by ID
- GET    /api/orders/customer/<phone>-> List orders for a customer
- PUT    /api/orders/<id>/status     -> Update order status
- DELETE /api/orders/<id>            -> Cancel order
"""

from flask import Blueprint, jsonify, request
from config.database import execute_query, get_db_cursor
from config.constants import HTTP_STATUS, ERROR_MESSAGES, SUCCESS_MESSAGES, ORDER_STATUS
from config.restaurant_config import RESTAURANT_CONFIG
from middleware.error_handler import handle_exceptions, ValidationError
from middleware.validators import validate_order_data, validate_phone_number
from utils.helpers import generate_order_id, calculate_order_total, calculate_estimated_ready_time, clean_phone_number
from utils.websocket_service import notify_order_update
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

orders_bp = Blueprint('orders', __name__)

# ============================================
# HELPER: FORMAT ORDER ROW
# ============================================
def format_order(order_row):
    """
    Format order row (dict or tuple) into API response shape.
    """
    if isinstance(order_row, dict):
        o = order_row
        return {
            "id": o.get("id"),
            "restaurantId": o.get("restaurant_id"),
            "orderNumber": o.get("order_number"),
            "customerPhone": o.get("customer_phone"),
            "customerName": o.get("customer_name"),
            "orderItems": o.get("order_items"),
            "subtotal": float(o.get("subtotal", 0)),
            "tax": float(o.get("tax", 0)),
            "totalPrice": float(o.get("total_price", 0)),
            "status": o.get("status"),
            "orderType": o.get("order_type"),
            "specialRequests": o.get("special_requests"),
            "deliveryAddress": o.get("delivery_address"),
            "estimatedReadyTime": o.get("estimated_ready_time").isoformat() if o.get("estimated_ready_time") else None,
            "completedAt": o.get("completed_at").isoformat() if o.get("completed_at") else None,
            "createdAt": o.get("created_at").isoformat() if o.get("created_at") else None,
            "updatedAt": o.get("updated_at").isoformat() if o.get("updated_at") else None,
        }
    else:
        # Tuple fallback (in case RealDictCursor is not used)
        return {
            "id": order_row[0],
            "restaurantId": order_row[1],
            "orderNumber": order_row[2],
            "customerPhone": order_row[3],
            "customerName": order_row[4],
            "orderItems": order_row[5],
            "subtotal": float(order_row[6]),
            "tax": float(order_row[7]),
            "totalPrice": float(order_row[8]),
            "status": order_row[9],
            "orderType": order_row[10],
            "specialRequests": order_row[11],
            "deliveryAddress": order_row[12],
            "estimatedReadyTime": order_row[13].isoformat() if order_row[13] else None,
            "completedAt": order_row[14].isoformat() if order_row[14] else None,
            "createdAt": order_row[15].isoformat() if order_row[15] else None,
            "updatedAt": order_row[16].isoformat() if order_row[16] else None,
        }


# ============================================
# POST /api/orders  -> Create order
# ============================================
@orders_bp.route('', methods=['POST'])
@handle_exceptions
def create_order():
    """
    Create a new order.

    Expected JSON body:
    {
      "items": [
        {"menuItemId": 1, "name": "Classic Burger", "price": 5.95, "quantity": 2},
        ...
      ],
      "orderType": "pickup" | "dine-in" | "delivery",
      "customerPhone": "+13125551234",
      "customerName": "John Doe",
      "deliveryAddress": "optional string for delivery",
      "specialRequests": "optional notes"
    }
    """
    data = request.get_json() or {}

    # Validate base order fields
    validate_order_data(data)

    items = data["items"]
    order_type = data["orderType"]
    customer_phone_raw = data["customerPhone"]
    customer_name = data.get("customerName")
    delivery_address = data.get("deliveryAddress")
    special_requests = data.get("specialRequests")

    # Normalize phone
    customer_phone = clean_phone_number(customer_phone_raw)
    validate_phone_number(customer_phone)

    # Calculate totals
    tax_rate = RESTAURANT_CONFIG["defaults"]["tax_rate"]
    totals = calculate_order_total(items, tax_rate=tax_rate)

    # if totals["total"] <= 0:
    #     totals["total"] = 1.00  # temporary minimum total for AI placeholder orders

    # Generate order number
    order_number = generate_order_id()

    # Estimate ready time
    # Use max preparation_time from items if provided, else fallback
    max_prep_time = max((item.get("preparationTime", 10) for item in items), default=10)
    estimated_ready_dt = calculate_estimated_ready_time(
        prep_time=max_prep_time,
        buffer=RESTAURANT_CONFIG["defaults"]["estimated_pickup_time"]
        if order_type != "delivery"
        else RESTAURANT_CONFIG["defaults"]["estimated_delivery_time"],
    )

    # Insert into DB
    sql = """
        INSERT INTO orders (
          restaurant_id,
          order_number,
          customer_phone,
          customer_name,
          order_items,
          subtotal,
          tax,
          total_price,
          status,
          order_type,
          special_requests,
          delivery_address,
          estimated_ready_time
        ) VALUES (
          %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
    """

    params = (
        RESTAURANT_CONFIG["id"],
        order_number,
        customer_phone,
        customer_name,
        json.dumps(items),
        totals["subtotal"],
        totals["tax"],
        totals["total"],
        ORDER_STATUS["PENDING"],
        order_type,
        special_requests,
        delivery_address,
        estimated_ready_dt,
    )

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        new_order = cursor.fetchone()

    logger.info(f"Order created: {new_order['order_number']} for {customer_phone}")

    return (
        jsonify(
            {
                "status": "success",
                "message": SUCCESS_MESSAGES["ORDER_CREATED"],
                "data": format_order(new_order),
            }
        ),
        HTTP_STATUS["CREATED"],
    )


# ============================================
# GET /api/orders  -> Get all orders (Admin)
# ============================================
@orders_bp.route('', methods=['GET'])
@handle_exceptions
def get_all_orders():
    """
    Get all orders (Admin view).
    Optional query params:
      - status: filter by status (comma separated)
      - limit, offset: pagination
    """
    status_filter = request.args.get("status", "").strip().lower()
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    base_sql = "FROM orders WHERE restaurant_id = %s"
    params = [RESTAURANT_CONFIG["id"]]

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',')]
        # valid_statuses check skipped for flexibility or can be added
        placeholders = ', '.join(['%s'] * len(statuses))
        base_sql += f" AND status IN ({placeholders})"
        params.extend(statuses)

    # Data query
    data_sql = """
        SELECT
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
    """ + base_sql + """
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    data_params = params + [limit, offset]

    orders = execute_query(data_sql, tuple(data_params), fetch_all=True)

    # Count query
    count_sql = "SELECT COUNT(*) " + base_sql
    count_result = execute_query(count_sql, tuple(params), fetch_one=True, fetch_all=False)
    if isinstance(count_result, dict):
        total = list(count_result.values())[0]
    else:
        total = count_result[0] if count_result else 0

    return (
        jsonify(
            {
                "status": "success",
                "data": {
                    "orders": [format_order(o) for o in orders],
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "total": total,
                        "returned": len(orders),
                    },
                },
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# GET /api/orders/<id>  -> Get order by ID
# ============================================
@orders_bp.route('/<int:order_id>', methods=['GET'])
@handle_exceptions
def get_order(order_id):
    """
    Get a single order by database ID.
    """
    sql = """
        SELECT
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
        FROM orders
        WHERE id = %s AND restaurant_id = %s
    """
    params = (order_id, RESTAURANT_CONFIG["id"])

    order = execute_query(sql, params, fetch_one=True, fetch_all=False)
    if not order:
        raise ValidationError(ERROR_MESSAGES["ORDER_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    return jsonify({"status": "success", "data": format_order(order)}), HTTP_STATUS["OK"]


# ============================================
# GET /api/orders/customer/<phone> -> Orders for a customer
# ============================================
@orders_bp.route('/customer/<phone>', methods=['GET'])
@handle_exceptions
def get_orders_by_customer(phone):
    """
    Get all orders for a given customer phone (normalized).
    Optional query params:
      - status: filter by status
      - limit, offset: pagination
    """
    status_filter = request.args.get("status", "").strip().lower()
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    normalized_phone = clean_phone_number(phone)
    validate_phone_number(normalized_phone)

    base_sql = """
        FROM orders
        WHERE restaurant_id = %s
          AND customer_phone = %s
    """
    params = [RESTAURANT_CONFIG["id"], normalized_phone]

    if status_filter:
        if status_filter not in [v for v in ORDER_STATUS.values()]:
            raise ValidationError("Invalid order status filter", HTTP_STATUS["BAD_REQUEST"])
        base_sql += " AND status = %s"
        params.append(status_filter)

    # Data query
    data_sql = """
        SELECT
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
    """ + base_sql + """
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    data_params = params + [limit, offset]

    orders = execute_query(data_sql, tuple(data_params), fetch_all=True)

    # Count query
    count_sql = "SELECT COUNT(*) " + base_sql
    count_result = execute_query(count_sql, tuple(params), fetch_one=True, fetch_all=False)
    if isinstance(count_result, dict):
        total = list(count_result.values())[0]
    else:
        total = count_result[0] if count_result else 0

    return (
        jsonify(
            {
                "status": "success",
                "data": {
                    "orders": [format_order(o) for o in orders],
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "total": total,
                        "returned": len(orders),
                    },
                },
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# PUT /api/orders/<id>/status  -> Update order status
# ============================================
@orders_bp.route('/<int:order_id>/status', methods=['PUT'])
@handle_exceptions
def update_order_status(order_id):
    """
    Update an order's status.

    JSON body:
    {
      "status": "confirmed" | "preparing" | "ready" | "completed" | "cancelled"
    }
    """
    data = request.get_json() or {}
    new_status = data.get("status", "").strip().lower()

    valid_status_values = [v for v in ORDER_STATUS.values()]
    if new_status not in valid_status_values:
        raise ValidationError(
            f"Invalid status. Valid options: {', '.join(valid_status_values)}",
            HTTP_STATUS["BAD_REQUEST"],
        )

    # If moving to completed/cancelled, set completed_at
    set_completed = new_status in [ORDER_STATUS["COMPLETED"], ORDER_STATUS["CANCELLED"]]

    sql = """
        UPDATE orders
        SET status = %s,
            completed_at = CASE
                WHEN %s THEN CURRENT_TIMESTAMP
                ELSE completed_at
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND restaurant_id = %s
        RETURNING
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
    """
    params = (new_status, set_completed, order_id, RESTAURANT_CONFIG["id"])

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        updated = cursor.fetchone()

    if not updated:
        raise ValidationError(ERROR_MESSAGES["ORDER_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    logger.info(f"Order {updated['order_number']} status updated to {new_status}")

    # Emit real-time update via WebSocket
    try:
        notify_order_update(order_id)
    except Exception as e:
        logger.error(f"Failed to emit order update: {e}")

    return (
        jsonify(
            {
                "status": "success",
                "data": format_order(updated),
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# DELETE /api/orders/<id> -> Cancel order
# ============================================
@orders_bp.route('/<int:order_id>', methods=['DELETE'])
@handle_exceptions
def cancel_order(order_id):
    """
    Cancel an order (soft cancel by updating status to 'cancelled').
    """
    sql = """
        UPDATE orders
        SET status = %s,
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND restaurant_id = %s
        AND status NOT IN (%s, %s)
        RETURNING
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
    """
    params = (
        ORDER_STATUS["CANCELLED"],
        order_id,
        RESTAURANT_CONFIG["id"],
        ORDER_STATUS["COMPLETED"],
        ORDER_STATUS["CANCELLED"],
    )

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        cancelled = cursor.fetchone()

    if not cancelled:
        # Either not found or already completed/cancelled
        raise ValidationError(ERROR_MESSAGES["ORDER_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    logger.info(f"Order {cancelled['order_number']} cancelled")

    return (
        jsonify(
            {
                "status": "success",
                "message": "Order cancelled",
                "data": format_order(cancelled),
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# GET /api/orders/number/<order_number> -> Get order by order number
# ============================================
@orders_bp.route('/number/<order_number>', methods=['GET'])
@handle_exceptions
def get_order_by_number(order_number):
    """
    Get a single order by order number.
    """
    sql = """
        SELECT
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
        FROM orders
        WHERE order_number = %s AND restaurant_id = %s
    """
    params = (order_number, RESTAURANT_CONFIG["id"])

    order = execute_query(sql, params, fetch_one=True, fetch_all=False)
    if not order:
        raise ValidationError(ERROR_MESSAGES["ORDER_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    return jsonify({"status": "success", "data": format_order(order)}), HTTP_STATUS["OK"]


# ============================================
# PUT /api/orders/number/<order_number>/status -> Update order status by number
# ============================================
@orders_bp.route('/number/<order_number>/status', methods=['PUT'])
@handle_exceptions
def update_order_status_by_number(order_number):
    """
    Update an order's status by order number.

    JSON body:
    {
      "status": "confirmed" | "preparing" | "ready" | "completed" | "cancelled"
    }
    """
    data = request.get_json() or {}
    new_status = data.get("status", "").strip().lower()

    valid_status_values = [v for v in ORDER_STATUS.values()]
    if new_status not in valid_status_values:
        raise ValidationError(
            f"Invalid status. Valid options: {', '.join(valid_status_values)}",
            HTTP_STATUS["BAD_REQUEST"],
        )

    # If moving to completed/cancelled, set completed_at
    set_completed = new_status in [ORDER_STATUS["COMPLETED"], ORDER_STATUS["CANCELLED"]]

    sql = """
        UPDATE orders
        SET status = %s,
            completed_at = CASE
                WHEN %s THEN CURRENT_TIMESTAMP
                ELSE completed_at
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE order_number = %s AND restaurant_id = %s
        RETURNING
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
    """
    params = (new_status, set_completed, order_number, RESTAURANT_CONFIG["id"])

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        updated = cursor.fetchone()

    if not updated:
        raise ValidationError(ERROR_MESSAGES["ORDER_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    logger.info(f"Order {updated['order_number']} status updated to {new_status}")

    return (
        jsonify(
            {
                "status": "success",
                "data": format_order(updated),
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# DELETE /api/orders/number/<order_number> -> Cancel order by number
# ============================================
@orders_bp.route('/number/<order_number>', methods=['DELETE'])
@handle_exceptions
def cancel_order_by_number(order_number):
    """
    Cancel an order by order number (soft cancel by updating status to 'cancelled').
    """
    sql = """
        UPDATE orders
        SET status = %s,
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE order_number = %s AND restaurant_id = %s
        AND status NOT IN (%s, %s)
        RETURNING
          id, restaurant_id, order_number, customer_phone, customer_name,
          order_items, subtotal, tax, total_price, status, order_type,
          special_requests, delivery_address, estimated_ready_time,
          completed_at, created_at, updated_at
    """
    params = (
        ORDER_STATUS["CANCELLED"],
        order_number,
        RESTAURANT_CONFIG["id"],
        ORDER_STATUS["COMPLETED"],
        ORDER_STATUS["CANCELLED"],
    )

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        cancelled = cursor.fetchone()

    if not cancelled:
        # Either not found or already completed/cancelled
        raise ValidationError(ERROR_MESSAGES["ORDER_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    logger.info(f"Order {cancelled['order_number']} cancelled")

    return (
        jsonify(
            {
                "status": "success",
                "message": "Order cancelled",
                "data": format_order(cancelled),
            }
        ),
        HTTP_STATUS["OK"],
    )
