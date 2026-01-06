"""
Reservations API Routes
Handles creating, retrieving, listing, updating, and cancelling reservations.

Endpoints:
- POST   /api/reservations                      -> Create new reservation
- GET    /api/reservations/<id>                 -> Get reservation by ID
- GET    /api/reservations/date/<yyyy-mm-dd>    -> List reservations for a date
- GET    /api/reservations/customer/<phone>     -> List reservations for a customer
- PUT    /api/reservations/<id>/status          -> Update reservation status
- DELETE /api/reservations/<id>                 -> Cancel reservation
"""

from flask import Blueprint, jsonify, request
from config.database import execute_query, get_db_cursor
from config.constants import HTTP_STATUS, ERROR_MESSAGES, RESERVATION_STATUS
from config.restaurant_config import RESTAURANT_CONFIG, is_restaurant_open
from middleware.error_handler import handle_exceptions, ValidationError
from middleware.validators import validate_reservation_data, validate_phone_number
from utils.helpers import (
    generate_reservation_id,
    is_time_slot_available,
    get_day_of_week,
    format_datetime,
    clean_phone_number,
)
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

reservations_bp = Blueprint('reservations', __name__)

# ============================================
# HELPER: FORMAT RESERVATION ROW
# ============================================
def format_reservation(row):
    """
    Format reservation row (dict or tuple) into API response shape.
    """
    if isinstance(row, dict):
        r = row
        return {
            "id": r.get("id"),
            "restaurantId": r.get("restaurant_id"),
            "reservationNumber": r.get("reservation_number"),
            "customerPhone": r.get("customer_phone"),
            "customerName": r.get("customer_name"),
            "customerEmail": r.get("customer_email"),
            "partySize": r.get("party_size"),
            "reservationDate": r.get("reservation_date").isoformat() if r.get("reservation_date") else None,
            "reservationTime": r.get("reservation_time").strftime("%H:%M:%S") if r.get("reservation_time") else None,
            "status": r.get("status"),
            "specialRequests": r.get("special_requests"),
            "notes": r.get("notes"),
            "createdAt": r.get("created_at").isoformat() if r.get("created_at") else None,
            "updatedAt": r.get("updated_at").isoformat() if r.get("updated_at") else None,
        }
    else:
        # Tuple fallback
        return {
            "id": row[0],
            "restaurantId": row[1],
            "reservationNumber": row[2],
            "customerPhone": row[3],
            "customerName": row[4],
            "customerEmail": row[5],
            "partySize": row[6],
            "reservationDate": row[7].isoformat() if row[7] else None,
            "reservationTime": row[8].strftime("%H:%M:%S") if row[8] else None,
            "status": row[9],
            "specialRequests": row[10],
            "notes": row[11],
            "createdAt": row[12].isoformat() if row[12] else None,
            "updatedAt": row[13].isoformat() if row[13] else None,
        }


# ============================================
# INTERNAL: CHECK AVAILABILITY & BUSINESS RULES
# ============================================
def _check_reservation_rules(res_date_str, res_time_str, party_size):
    """
    Enforce restaurant rules:
    - restaurant open on that day/time
    - min/max advance notice
    - capacity (tables_available) using is_time_slot_available
    """
    settings = RESTAURANT_CONFIG["reservation_settings"]
    min_notice_minutes = settings["min_advance_notice"]
    max_advance_minutes = settings["max_advance_booking"]
    default_duration = settings["default_duration"]
    tables_available = settings["tables_available"]

    # Parse date & time
    try:
        # reservationDate is ISO date, reservationTime is "HH:MM"
        combined_str = f"{res_date_str}T{res_time_str}"
        requested_dt = datetime.fromisoformat(combined_str)
    except Exception:
        raise ValidationError(ERROR_MESSAGES["INVALID_RESERVATION_DATE"], HTTP_STATUS["BAD_REQUEST"])

    now = datetime.now()
    diff = requested_dt - now
    diff_minutes = diff.total_seconds() / 60

    # Check advance notice
    if diff_minutes < min_notice_minutes:
        raise ValidationError("Reservation must be made at least "
                              f"{min_notice_minutes} minutes in advance",
                              HTTP_STATUS["BAD_REQUEST"])
    if diff_minutes > max_advance_minutes:
        raise ValidationError("Reservation cannot be made that far in advance",
                              HTTP_STATUS["BAD_REQUEST"])

    # Check restaurant open (by day)
    day_name = get_day_of_week(res_date_str)  # returns monday..sunday
    # if not is_restaurant_open(day_name=day_name):
    #     raise ValidationError(ERROR_MESSAGES["RESTAURANT_CLOSED"], HTTP_STATUS["BAD_REQUEST"])

    # Check capacity for that time slot
    # 1) Fetch existing reservations on that date
    sql = """
        SELECT
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
        FROM reservations
        WHERE restaurant_id = %s
          AND reservation_date = %s
          AND status IN (%s, %s, %s)
    """
    params = (
        RESTAURANT_CONFIG["id"],
        res_date_str,
        RESERVATION_STATUS["PENDING"],
        RESERVATION_STATUS["CONFIRMED"],
        RESERVATION_STATUS["COMPLETED"],
    )

    existing = execute_query(sql, params, fetch_all=True)

    # Build a list of booked time slots for is_time_slot_available
    booked_times = []
    for r in existing:
        formatted = format_reservation(r)
        booked_times.append(
            {
                "reservationTime": f"{formatted['reservationDate']}T{formatted['reservationTime']}"
            }
        )

    requested_iso_time = f"{res_date_str}T{res_time_str}"
    # Use helper to check slot overlap
    if not is_time_slot_available(requested_iso_time, booked_times, duration=default_duration):
        # Already full at this time
        raise ValidationError(ERROR_MESSAGES["NO_AVAILABILITY"], HTTP_STATUS["BAD_REQUEST"])

    # Optionally, enforce party size relative to tables_available (basic: if too many existing parties)
    total_parties = len(existing) + 1
    if total_parties > tables_available:
        raise ValidationError(ERROR_MESSAGES["NO_AVAILABILITY"], HTTP_STATUS["BAD_REQUEST"])


# ============================================
# POST /api/reservations -> Create reservation
# ============================================
@reservations_bp.route('', methods=['POST'])
@handle_exceptions
def create_reservation():
    """
    Create a new reservation.

    Expected JSON body:
    {
      "reservationDate": "2025-12-31",
      "reservationTime": "19:30",
      "partySize": 4,
      "customerName": "John Doe",
      "customerPhone": "+1 (312) 555-1234",
      "customerEmail": "optional@email",
      "specialRequests": "optional string"
    }
    """
    data = request.get_json() or {}

    # Validate structure and base fields
    validate_reservation_data(data)

    reservation_date = data["reservationDate"]
    reservation_time = data["reservationTime"]
    party_size = int(data["partySize"])
    customer_name = data["customerName"]
    customer_phone_raw = data["customerPhone"]
    customer_email = data.get("customerEmail")
    special_requests = data.get("specialRequests")
    notes = data.get("notes")

    # Normalize and validate phone
    customer_phone = clean_phone_number(customer_phone_raw)
    validate_phone_number(customer_phone)

    # Check restaurant rules & availability
    _check_reservation_rules(reservation_date, reservation_time, party_size)

    # Generate reservation number
    reservation_number = generate_reservation_id()

    # Insert into DB
    sql = """
        INSERT INTO reservations (
          restaurant_id,
          reservation_number,
          customer_phone,
          customer_name,
          customer_email,
          party_size,
          reservation_date,
          reservation_time,
          status,
          special_requests,
          notes
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
    """

    params = (
        RESTAURANT_CONFIG["id"],
        reservation_number,
        customer_phone,
        customer_name,
        customer_email,
        party_size,
        reservation_date,
        reservation_time,
        RESERVATION_STATUS["PENDING"],
        special_requests,
        notes,
    )

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        new_res = cursor.fetchone()

    logger.info(f"Reservation created: {new_res['reservation_number']} for {customer_phone}")

    return (
        jsonify(
            {
                "status": "success",
                "data": format_reservation(new_res),
            }
        ),
        HTTP_STATUS["CREATED"],
    )


# ============================================
# GET /api/reservations -> Get all reservations (Admin)
# ============================================
@reservations_bp.route('', methods=['GET'])
@handle_exceptions
def get_all_reservations():
    """
    Get all upcoming reservations (Admin view).
    Optional query:
      - status: comma separated
      - date: YYYY-MM-DD (filter by specific date)
      - limit, offset
    """
    status_filter = request.args.get("status", "").strip().lower()
    date_filter = request.args.get("date", "").strip()
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    base_sql = "FROM reservations WHERE restaurant_id = %s"
    params = [RESTAURANT_CONFIG["id"]]

    if date_filter:
        base_sql += " AND reservation_date = %s"
        params.append(date_filter)
    
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',')]
        placeholders = ', '.join(['%s'] * len(statuses))
        base_sql += f" AND status IN ({placeholders})"
        params.extend(statuses)

    
    # Data query
    data_sql = """
        SELECT
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
    """ + base_sql + """
        ORDER BY reservation_date DESC, reservation_time DESC
        LIMIT %s OFFSET %s
    """
    data_params = params + [limit, offset]

    reservations = execute_query(data_sql, tuple(data_params), fetch_all=True)

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
                    "reservations": [format_reservation(r) for r in reservations],
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "total": total,
                        "returned": len(reservations),
                    },
                },
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# GET /api/reservations/<id> -> Get reservation
# ============================================
@reservations_bp.route('/<int:reservation_id>', methods=['GET'])
@handle_exceptions
def get_reservation(reservation_id):
    """
    Get a single reservation by database ID.
    """
    sql = """
        SELECT
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
        FROM reservations
        WHERE id = %s AND restaurant_id = %s
    """
    params = (reservation_id, RESTAURANT_CONFIG["id"])

    res = execute_query(sql, params, fetch_one=True, fetch_all=False)
    if not res:
        raise ValidationError(ERROR_MESSAGES["RESERVATION_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    return jsonify({"status": "success", "data": format_reservation(res)}), HTTP_STATUS["OK"]


# ============================================
# GET /api/reservations/date/<date> -> By date
# ============================================
@reservations_bp.route('/date/<date_str>', methods=['GET'])
@handle_exceptions
def get_reservations_by_date(date_str):
    """
    Get all reservations for a given date (YYYY-MM-DD).

    Optional query params:
      - status: filter by status
    """
    status_filter = request.args.get("status", "").strip().lower()

    # Basic validation for date string
    try:
        datetime.fromisoformat(date_str)
    except Exception:
        raise ValidationError(ERROR_MESSAGES["INVALID_RESERVATION_DATE"], HTTP_STATUS["BAD_REQUEST"])

    base_sql = """
        FROM reservations
        WHERE restaurant_id = %s
          AND reservation_date = %s
    """
    params = [RESTAURANT_CONFIG["id"], date_str]

    if status_filter:
        if status_filter not in [v for v in RESERVATION_STATUS.values()]:
            raise ValidationError("Invalid reservation status filter", HTTP_STATUS["BAD_REQUEST"])
        base_sql += " AND status = %s"
        params.append(status_filter)

    sql = """
        SELECT
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
    """ + base_sql + """
        ORDER BY reservation_time ASC
    """

    reservations = execute_query(sql, tuple(params), fetch_all=True)

    return (
        jsonify(
            {
                "status": "success",
                "date": date_str,
                "count": len(reservations),
                "data": [format_reservation(r) for r in reservations],
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# GET /api/reservations/customer/<phone> -> By customer
# ============================================
@reservations_bp.route('/customer/<phone>', methods=['GET'])
@handle_exceptions
def get_reservations_by_customer(phone):
    """
    Get all reservations for a given customer phone.
    Optional query:
      - status
    """
    status_filter = request.args.get("status", "").strip().lower()
    normalized_phone = clean_phone_number(phone)
    validate_phone_number(normalized_phone)

    base_sql = """
        FROM reservations
        WHERE restaurant_id = %s
          AND customer_phone = %s
    """
    params = [RESTAURANT_CONFIG["id"], normalized_phone]

    if status_filter:
        if status_filter not in [v for v in RESERVATION_STATUS.values()]:
            raise ValidationError("Invalid reservation status filter", HTTP_STATUS["BAD_REQUEST"])
        base_sql += " AND status = %s"
        params.append(status_filter)

    sql = """
        SELECT
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
    """ + base_sql + """
        ORDER BY reservation_date DESC, reservation_time DESC
    """

    reservations = execute_query(sql, tuple(params), fetch_all=True)

    return (
        jsonify(
            {
                "status": "success",
                "phone": normalized_phone,
                "count": len(reservations),
                "data": [format_reservation(r) for r in reservations],
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# PUT /api/reservations/<id>/status -> Update status
# ============================================
@reservations_bp.route('/<int:reservation_id>/status', methods=['PUT'])
@handle_exceptions
def update_reservation_status(reservation_id):
    """
    Update reservation status.

    JSON body:
    {
      "status": "confirmed" | "completed" | "cancelled" | "no_show"
    }
    """
    data = request.get_json() or {}
    new_status = data.get("status", "").strip().lower()

    valid_status_values = [v for v in RESERVATION_STATUS.values()]
    if new_status not in valid_status_values:
        raise ValidationError(
            f"Invalid status. Valid options: {', '.join(valid_status_values)}",
            HTTP_STATUS["BAD_REQUEST"],
        )

    sql = """
        UPDATE reservations
        SET status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND restaurant_id = %s
        RETURNING
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
    """
    params = (new_status, reservation_id, RESTAURANT_CONFIG["id"])

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        updated = cursor.fetchone()

    if not updated:
        raise ValidationError(ERROR_MESSAGES["RESERVATION_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    logger.info(f"Reservation {updated['reservation_number']} status updated to {new_status}")

    return jsonify({"status": "success", "data": format_reservation(updated)}), HTTP_STATUS["OK"]


# ============================================
# DELETE /api/reservations/<id> -> Cancel
# ============================================
@reservations_bp.route('/<int:reservation_id>', methods=['DELETE'])
@handle_exceptions
def cancel_reservation(reservation_id):
    """
    Cancel a reservation (set status to 'cancelled').
    """
    sql = """
        UPDATE reservations
        SET status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND restaurant_id = %s
          AND status NOT IN (%s, %s)
        RETURNING
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
    """
    params = (
        RESERVATION_STATUS["CANCELLED"],
        reservation_id,
        RESTAURANT_CONFIG["id"],
        RESERVATION_STATUS["COMPLETED"],
        RESERVATION_STATUS["CANCELLED"],
    )

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        cancelled = cursor.fetchone()

    if not cancelled:
        raise ValidationError(ERROR_MESSAGES["RESERVATION_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    logger.info(f"Reservation {cancelled['reservation_number']} cancelled")

    return (
        jsonify(
            {
                "status": "success",
                "message": "Reservation cancelled",
                "data": format_reservation(cancelled),
            }
        ),
        HTTP_STATUS["OK"],
    )


# ============================================
# POST /api/reservations/availability -> Check availability
# ============================================
@reservations_bp.route('/availability', methods=['POST'])
@handle_exceptions
def check_availability():
    """
    Check if a reservation slot is available.

    Expected JSON body:
    {
      "reservationDate": "2025-12-31",
      "reservationTime": "19:30",
      "partySize": 4
    }
    """
    data = request.get_json() or {}

    reservation_date = data.get("reservationDate")
    reservation_time = data.get("reservationTime")
    party_size = data.get("partySize")

    if not all([reservation_date, reservation_time, party_size]):
        raise ValidationError("reservationDate, reservationTime, and partySize are required", HTTP_STATUS["BAD_REQUEST"])

    try:
        party_size = int(party_size)

        # Check rules - if this passes, it's available
        # _check_reservation_rules raises ValidationError if not available
        _check_reservation_rules(reservation_date, reservation_time, party_size)

        return jsonify({
            "status": "success",
            "available": True,
            "message": f"Great! We have availability for {party_size} guests on {reservation_date} at {reservation_time}."
        }), HTTP_STATUS["OK"]

    except ValidationError as e:
        # If it's a validation error, it means likely not available or invalid params
        # We return success: true (API call worked) but available: false
        return jsonify({
            "status": "success",
            "available": False,
            "message": str(e)
        }), HTTP_STATUS["OK"]
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        return jsonify({
            "status": "error",
            "available": False,
            "message": "Could not check availability"
        }), HTTP_STATUS["INTERNAL_SERVER_ERROR"]


# ============================================
# GET /api/reservations/number/<reservation_number> -> Get reservation by number
# ============================================
@reservations_bp.route('/number/<reservation_number>', methods=['GET'])
@handle_exceptions
def get_reservation_by_number(reservation_number):
    """
    Get a single reservation by reservation number.
    """
    sql = """
        SELECT
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
        FROM reservations
        WHERE reservation_number = %s AND restaurant_id = %s
    """
    params = (reservation_number, RESTAURANT_CONFIG["id"])

    res = execute_query(sql, params, fetch_one=True, fetch_all=False)
    if not res:
        raise ValidationError(ERROR_MESSAGES["RESERVATION_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    return jsonify({"status": "success", "data": format_reservation(res)}), HTTP_STATUS["OK"]


# ============================================
# PUT /api/reservations/number/<reservation_number>/status -> Update status by number
# ============================================
@reservations_bp.route('/number/<reservation_number>/status', methods=['PUT'])
@handle_exceptions
def update_reservation_status_by_number(reservation_number):
    """
    Update reservation status by reservation number.

    JSON body:
    {
      "status": "confirmed" | "completed" | "cancelled" | "no_show"
    }
    """
    data = request.get_json() or {}
    new_status = data.get("status", "").strip().lower()

    valid_status_values = [v for v in RESERVATION_STATUS.values()]
    if new_status not in valid_status_values:
        raise ValidationError(
            f"Invalid status. Valid options: {', '.join(valid_status_values)}",
            HTTP_STATUS["BAD_REQUEST"],
        )

    sql = """
        UPDATE reservations
        SET status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE reservation_number = %s AND restaurant_id = %s
        RETURNING
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
    """
    params = (new_status, reservation_number, RESTAURANT_CONFIG["id"])

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        updated = cursor.fetchone()

    if not updated:
        raise ValidationError(ERROR_MESSAGES["RESERVATION_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    logger.info(f"Reservation {updated['reservation_number']} status updated to {new_status}")

    return jsonify({"status": "success", "data": format_reservation(updated)}), HTTP_STATUS["OK"]


# ============================================
# DELETE /api/reservations/number/<reservation_number> -> Cancel by number
# ============================================
@reservations_bp.route('/number/<reservation_number>', methods=['DELETE'])
@handle_exceptions
def cancel_reservation_by_number(reservation_number):
    """
    Cancel a reservation by reservation number (set status to 'cancelled').
    """
    sql = """
        UPDATE reservations
        SET status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE reservation_number = %s AND restaurant_id = %s
          AND status NOT IN (%s, %s)
        RETURNING
          id, restaurant_id, reservation_number, customer_phone, customer_name,
          customer_email, party_size, reservation_date, reservation_time,
          status, special_requests, notes, created_at, updated_at
    """
    params = (
        RESERVATION_STATUS["CANCELLED"],
        reservation_number,
        RESTAURANT_CONFIG["id"],
        RESERVATION_STATUS["COMPLETED"],
        RESERVATION_STATUS["CANCELLED"],
    )

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        cancelled = cursor.fetchone()

    if not cancelled:
        raise ValidationError(ERROR_MESSAGES["RESERVATION_NOT_FOUND"], HTTP_STATUS["NOT_FOUND"])

    logger.info(f"Reservation {cancelled['reservation_number']} cancelled")

    return (
        jsonify(
            {
                "status": "success",
                "message": "Reservation cancelled",
                "data": format_reservation(cancelled),
            }
        ),
        HTTP_STATUS["OK"],
    )
