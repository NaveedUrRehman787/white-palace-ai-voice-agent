"""
Payment Processing Routes
Stripe integration for order payments.

Endpoints:
- POST /api/payments/create-intent    -> Create payment intent
- POST /api/payments/webhook          -> Stripe webhook handler
- GET /api/payments/{order_id}        -> Get payment status
- POST /api/payments/{order_id}/refund -> Refund payment
"""

from flask import Blueprint, jsonify, request
from config.database import execute_query, get_db_cursor
from config.constants import HTTP_STATUS, ERROR_MESSAGES, SUCCESS_MESSAGES
from config.restaurant_config import RESTAURANT_CONFIG
from middleware.error_handler import handle_exceptions, ValidationError
from middleware.validators import validate_order_data
from utils.helpers import clean_phone_number
import stripe
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__)

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# ============================================
# HELPER: FORMAT PAYMENT ROW
# ============================================
def format_payment(payment_row):
    """Format payment row for API response."""
    if isinstance(payment_row, dict):
        p = payment_row
        return {
            "id": p.get("id"),
            "orderId": p.get("order_id"),
            "stripePaymentIntentId": p.get("stripe_payment_intent_id"),
            "amount": float(p.get("amount", 0)),
            "currency": p.get("currency", "USD"),
            "status": p.get("status"),
            "paymentMethod": p.get("payment_method"),
            "customerEmail": p.get("customer_email"),
            "metadata": p.get("metadata"),
            "createdAt": p.get("created_at").isoformat() if p.get("created_at") else None,
            "updatedAt": p.get("updated_at").isoformat() if p.get("updated_at") else None,
        }
    else:
        # Tuple fallback
        return {
            "id": payment_row[0],
            "orderId": payment_row[1],
            "stripePaymentIntentId": payment_row[2],
            "amount": float(payment_row[3]),
            "currency": payment_row[4] or "USD",
            "status": payment_row[5],
            "paymentMethod": payment_row[6],
            "customerEmail": payment_row[7],
            "metadata": payment_row[8],
            "createdAt": payment_row[9].isoformat() if payment_row[9] else None,
            "updatedAt": payment_row[10].isoformat() if payment_row[10] else None,
        }

# ============================================
# POST /api/payments/create-intent
# ============================================

@payments_bp.route("/create-intent", methods=["POST"])
@handle_exceptions
def create_payment_intent():
    pass
    # data = request.get_json() or {}
    # amount = data.get("amount")

    # if not amount:
    #     raise ValidationError("Amount is required", HTTP_STATUS["BAD_REQUEST"])

    # # TEMP: bypass Stripe
    # fake_client_secret = "test_client_secret_no_payment"

    # return jsonify(
    #     status="success",
    #     data={"clientSecret": fake_client_secret}
    # ), HTTP_STATUS["OK"]


# @payments_bp.route('/create-intent', methods=['POST'])
# @handle_exceptions
# def create_payment_intent():
#     """
#     Create a Stripe payment intent for an order.

#     Expected JSON body:
#     {
#       "orderId": 123,
#       "amount": 25.95,
#       "currency": "USD",
#       "customerEmail": "customer@example.com",
#       "metadata": {"order_number": "ABC123"}
#     }

#     Returns:
#     {
#       "clientSecret": "...",
#       "paymentIntentId": "...",
#       "publishableKey": "..."
#     }
#     """
#     data = request.get_json() or {}
#     order_id = data.get("orderId")
#     amount = data.get("amount")
#     currency = data.get("currency", "USD").upper()
#     customer_email = data.get("customerEmail")
#     metadata = data.get("metadata", {})

#     if not order_id or not amount:
#         raise ValidationError("orderId and amount are required", HTTP_STATUS["BAD_REQUEST"])

#     if amount <= 0:
#         raise ValidationError("Amount must be greater than 0", HTTP_STATUS["BAD_REQUEST"])

#     # Verify order exists and is in correct status
#     order_sql = """
#         SELECT id, order_number, status, total_price, customer_name
#         FROM orders
#         WHERE id = %s AND restaurant_id = %s
#     """
#     order = execute_query(order_sql, (order_id, RESTAURANT_CONFIG["id"]), fetch_one=True)

#     if not order:
#         raise ValidationError("Order not found", HTTP_STATUS["NOT_FOUND"])

#     if isinstance(order, dict):
#         order_status = order.get("status")
#         order_total = float(order.get("total_price", 0))
#         order_number = order.get("order_number")
#     else:
#         order_status = order[2]
#         order_total = float(order[4])
#         order_number = order[1]

#     if order_status not in ["pending", "confirmed"]:
#         raise ValidationError("Order is not in a payable state", HTTP_STATUS["BAD_REQUEST"])

#     # Convert amount to cents for Stripe
#     amount_cents = int(amount * 100)

#     # Create payment intent metadata
#     intent_metadata = {
#         "order_id": str(order_id),
#         "order_number": order_number,
#         "restaurant_id": str(RESTAURANT_CONFIG["id"]),
#         **metadata
#     }

#     try:
#         # Create Stripe payment intent
#         intent = stripe.PaymentIntent.create(
#             amount=amount_cents,
#             currency=currency.lower(),
#             metadata=intent_metadata,
#             receipt_email=customer_email,
#             description=f"Order #{order_number} - White Palace Grill",
#             automatic_payment_methods={"enabled": True}
#         )

#         # Store payment record in database
#         payment_sql = """
#             INSERT INTO payments (
#               restaurant_id, order_id, stripe_payment_intent_id,
#               amount, currency, status, customer_email, metadata
#             ) VALUES (
#               %s, %s, %s, %s, %s, %s, %s, %s
#             )
#             RETURNING id
#         """
#         payment_params = (
#             RESTAURANT_CONFIG["id"],
#             order_id,
#             intent.id,
#             amount,
#             currency,
#             intent.status,
#             customer_email,
#             json.dumps(intent_metadata)
#         )

#         with get_db_cursor() as cursor:
#             cursor.execute(payment_sql, payment_params)
#             payment_id = cursor.fetchone()[0]

#         logger.info(f"Payment intent created: {intent.id} for order {order_number}")

#         return jsonify({
#             "status": "success",
#             "data": {
#                 "paymentIntentId": intent.id,
#                 "clientSecret": intent.client_secret,
#                 "amount": amount,
#                 "currency": currency,
#                 "status": intent.status,
#                 "publishableKey": os.getenv('STRIPE_PUBLISHABLE_KEY')
#             }
#         }), HTTP_STATUS["CREATED"]

#     except stripe.error.StripeError as e:
#         logger.error(f"Stripe error creating payment intent: {e}")
#         raise ValidationError(f"Payment processing error: {str(e)}", HTTP_STATUS["INTERNAL_SERVER_ERROR"])
#     except Exception as e:
#         logger.error(f"Error creating payment intent: {e}")
#         raise ValidationError("Failed to create payment intent", HTTP_STATUS["INTERNAL_SERVER_ERROR"])

# ============================================
# POST /api/payments/webhook
# ============================================
@payments_bp.route('/webhook', methods=['POST'])
@handle_exceptions
def stripe_webhook():
    """
    Handle Stripe webhook events for payment status updates.
    """
    payload = request.get_data()
    sig_header = request.headers.get('stripe-signature')

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )

    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        return jsonify({"error": "Invalid payload"}), HTTP_STATUS["BAD_REQUEST"]
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return jsonify({"error": "Invalid signature"}), HTTP_STATUS["BAD_REQUEST"]

    # Handle the event
    event_type = event['type']
    payment_intent = event['data']['object']

    logger.info(f"Stripe webhook: {event_type} for payment {payment_intent['id']}")

    try:
        # Update payment status in database
        update_sql = """
            UPDATE payments
            SET status = %s, updated_at = CURRENT_TIMESTAMP, metadata = metadata || %s
            WHERE stripe_payment_intent_id = %s AND restaurant_id = %s
        """

        # Extract metadata
        metadata = payment_intent.get('metadata', {})
        order_id = metadata.get('order_id')

        # Prepare additional metadata
        webhook_data = {
            "webhook_event": event_type,
            "webhook_received_at": datetime.now().isoformat(),
            "stripe_status": payment_intent.get('status'),
            "amount_received": payment_intent.get('amount_received')
        }

        update_params = (
            payment_intent.get('status'),
            json.dumps(webhook_data),
            payment_intent['id'],
            RESTAURANT_CONFIG["id"]
        )

        execute_query(update_sql, update_params)

        # If payment succeeded, update order status
        if event_type == 'payment_intent.succeeded' and order_id:
            order_update_sql = """
                UPDATE orders
                SET status = 'confirmed', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND restaurant_id = %s AND status = 'pending'
            """
            execute_query(order_update_sql, (order_id, RESTAURANT_CONFIG["id"]))
            logger.info(f"Order {order_id} confirmed after successful payment")

        elif event_type == 'payment_intent.payment_failed' and order_id:
            # Could notify customer or take other actions
            logger.warning(f"Payment failed for order {order_id}")

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Return 500 to make Stripe retry
        return jsonify({"error": "Webhook processing failed"}), HTTP_STATUS["INTERNAL_SERVER_ERROR"]

    return jsonify({"status": "success"}), HTTP_STATUS["OK"]

# ============================================
# GET /api/payments/{order_id}
# ============================================
@payments_bp.route('/<int:order_id>', methods=['GET'])
@handle_exceptions
def get_payment_status(order_id):
    """
    Get payment status for an order.
    """
    sql = """
        SELECT id, order_id, stripe_payment_intent_id, amount, currency,
               status, payment_method, customer_email, metadata,
               created_at, updated_at
        FROM payments
        WHERE order_id = %s AND restaurant_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """
    params = (order_id, RESTAURANT_CONFIG["id"])

    payment = execute_query(sql, params, fetch_one=True, fetch_all=False)
    if not payment:
        raise ValidationError("No payment found for this order", HTTP_STATUS["NOT_FOUND"])

    return jsonify({
        "status": "success",
        "data": format_payment(payment)
    }), HTTP_STATUS["OK"]

# ============================================
# POST /api/payments/{order_id}/refund
# ============================================
@payments_bp.route('/<int:order_id>/refund', methods=['POST'])
@handle_exceptions
def refund_payment(order_id):
    """
    Process a refund for an order.

    Expected JSON body:
    {
      "amount": 10.00,  // Optional: partial refund amount
      "reason": "requested_by_customer"
    }
    """
    data = request.get_json() or {}
    refund_amount = data.get("amount")
    reason = data.get("reason", "requested_by_customer")

    # Get payment details
    payment_sql = """
        SELECT stripe_payment_intent_id, amount, status
        FROM payments
        WHERE order_id = %s AND restaurant_id = %s AND status = 'succeeded'
        ORDER BY created_at DESC
        LIMIT 1
    """
    payment = execute_query(payment_sql, (order_id, RESTAURANT_CONFIG["id"]), fetch_one=True)

    if not payment:
        raise ValidationError("No successful payment found for this order", HTTP_STATUS["NOT_FOUND"])

    if isinstance(payment, dict):
        payment_intent_id = payment.get("stripe_payment_intent_id")
        full_amount = float(payment.get("amount", 0))
    else:
        payment_intent_id = payment[0]
        full_amount = float(payment[1])

    # Determine refund amount
    if refund_amount is None:
        refund_amount = full_amount
    elif refund_amount > full_amount:
        raise ValidationError("Refund amount cannot exceed payment amount", HTTP_STATUS["BAD_REQUEST"])

    try:
        # Create Stripe refund
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            amount=int(refund_amount * 100),  # Convert to cents
            reason=reason
        )

        # Update payment status
        update_sql = """
            UPDATE payments
            SET status = 'refunded', updated_at = CURRENT_TIMESTAMP,
                metadata = metadata || %s
            WHERE stripe_payment_intent_id = %s AND restaurant_id = %s
        """
        refund_data = json.dumps({
            "refund_id": refund.id,
            "refund_amount": refund_amount,
            "refund_reason": reason,
            "refund_created": datetime.now().isoformat()
        })

        execute_query(update_sql, (refund_data, payment_intent_id, RESTAURANT_CONFIG["id"]))

        # Update order status if full refund
        if refund_amount >= full_amount:
            order_update_sql = """
                UPDATE orders
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND restaurant_id = %s
            """
            execute_query(order_update_sql, (order_id, RESTAURANT_CONFIG["id"]))

        logger.info(f"Refund processed: ${refund_amount} for order {order_id}")

        return jsonify({
            "status": "success",
            "data": {
                "refundId": refund.id,
                "amount": refund_amount,
                "currency": refund.currency.upper(),
                "status": refund.status,
                "orderId": order_id
            }
        }), HTTP_STATUS["OK"]

    except stripe.error.StripeError as e:
        logger.error(f"Stripe refund error: {e}")
        raise ValidationError(f"Refund processing error: {str(e)}", HTTP_STATUS["INTERNAL_SERVER_ERROR"])

# ============================================
# GET /api/payments/stats
# ============================================
@payments_bp.route('/stats', methods=['GET'])
@handle_exceptions
def get_payment_stats():
    """
    Get payment statistics (admin only).
    Optional query params: period (day|week|month|year)
    """
    period = request.args.get('period', 'month')

    # Build date filter
    if period == 'day':
        date_filter = "CURRENT_DATE"
    elif period == 'week':
        date_filter = "CURRENT_DATE - INTERVAL '7 days'"
    elif period == 'month':
        date_filter = "CURRENT_DATE - INTERVAL '30 days'"
    elif period == 'year':
        date_filter = "CURRENT_DATE - INTERVAL '365 days'"
    else:
        date_filter = "CURRENT_DATE - INTERVAL '30 days'"

    sql = f"""
        SELECT
          COUNT(*) as total_payments,
          COALESCE(SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END), 0) as successful_payments,
          COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) as failed_payments,
          COALESCE(SUM(CASE WHEN status = 'succeeded' THEN amount ELSE 0 END), 0.0) as total_revenue,
          CASE
            WHEN COUNT(CASE WHEN status = 'succeeded' THEN 1 END) > 0
            THEN COALESCE(AVG(CASE WHEN status = 'succeeded' THEN amount END), 0.0)
            ELSE 0.0
          END as avg_payment_amount
        FROM payments
        WHERE restaurant_id = %s AND created_at >= {date_filter}
    """

    stats = execute_query(sql, (RESTAURANT_CONFIG["id"],), fetch_one=True)

    # Handle case where no payments exist (stats is None)
    if stats is None:
        result = {
            "totalPayments": 0,
            "successfulPayments": 0,
            "failedPayments": 0,
            "totalRevenue": 0.0,
            "averagePaymentAmount": 0.0,
            "period": period
        }
    elif isinstance(stats, dict):
        result = {
            "totalPayments": stats.get("total_payments", 0),
            "successfulPayments": stats.get("successful_payments", 0),
            "failedPayments": stats.get("failed_payments", 0),
            "totalRevenue": float(stats.get("total_revenue", 0) or 0),
            "averagePaymentAmount": float(stats.get("avg_payment_amount", 0) or 0),
            "period": period
        }
    else:
        # Tuple fallback with safe None checking
        total_payments = stats[0] if stats and len(stats) > 0 and stats[0] is not None else 0
        successful_payments = stats[1] if stats and len(stats) > 1 and stats[1] is not None else 0
        failed_payments = stats[2] if stats and len(stats) > 2 and stats[2] is not None else 0
        total_revenue = float(stats[3]) if stats and len(stats) > 3 and stats[3] is not None else 0.0
        avg_payment_amount = float(stats[4]) if stats and len(stats) > 4 and stats[4] is not None else 0.0

        result = {
            "totalPayments": total_payments,
            "successfulPayments": successful_payments,
            "failedPayments": failed_payments,
            "totalRevenue": total_revenue,
            "averagePaymentAmount": avg_payment_amount,
            "period": period
        }

    return jsonify({
        "status": "success",
        "data": result
    }), HTTP_STATUS["OK"]
