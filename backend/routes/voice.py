"""
Voice / LiveKit API Routes

Endpoints:
- POST /api/voice/create-room   -> Create a LiveKit room + tokens for customer & agent
- POST /api/voice/start-session -> Start AI voice agent session in room
- POST /api/voice/stop-session  -> Stop AI voice agent session
"""

from flask import Blueprint, jsonify, request
import asyncio
from config.constants import HTTP_STATUS
from middleware.error_handler import handle_exceptions, ValidationError
from middleware.validators import validate_phone_number
from utils.helpers import clean_phone_number
from utils.livekit_service import livekit_service
from routes.voice_pipeline import start_voice_session, stop_voice_session, get_agent_session
import logging

logger = logging.getLogger(__name__)

voice_bp = Blueprint('voice', __name__)


# ============================================
# POST /api/voice/create-room
# ============================================
@voice_bp.route('/create-room', methods=['POST'])
@handle_exceptions
def create_room():
    """
    Create a LiveKit room for a voice call between customer and AI agent.

    Expected JSON body:
    {
      "customerPhone": "+1 (312) 555-1234"   # required
    }

    Returns:
    {
      "status": "success",
      "data": {
        "roomName": "...",
        "livekitUrl": "ws://...",
        "customerToken": "...",
        "agentToken": "...",  # Changed from staffToken
        "createdAt": "..."
      }
    }
    """
    body = request.get_json() or {}

    customer_phone_raw = body.get("customerPhone")
    if not customer_phone_raw:
        raise ValidationError("customerPhone is required", HTTP_STATUS["BAD_REQUEST"])

    # Normalize and validate phone
    customer_phone = clean_phone_number(customer_phone_raw)
    validate_phone_number(customer_phone)

    # Create LiveKit voice room via service
    room_info = livekit_service.create_voice_room(customer_phone=customer_phone)
    if not room_info:
        raise ValidationError("Failed to create LiveKit room", HTTP_STATUS["INTERNAL_SERVER_ERROR"])

    logger.info(
        f"LiveKit voice room created: {room_info['room_name']} "
        f"for customer {customer_phone}"
    )

    return (
        jsonify(
            {
                "status": "success",
                "data": {
                    "roomName": room_info["room_name"],
                    "livekitUrl": room_info["livekit_url"],
                    "customerToken": room_info["customer_token"],
                    "agentToken": room_info["staff_token"],  # Reuse staff token as agent token
                    "createdAt": room_info["created_at"],
                },
            }
        ),
        HTTP_STATUS["CREATED"],
    )


# ============================================
# POST /api/voice/start-session
# ============================================
@voice_bp.route('/start-session', methods=['POST'])
@handle_exceptions
def start_session():
    """
    Start AI voice agent session in a LiveKit room.

    Expected JSON body:
    {
      "roomName": "room_name",           # required
      "customerPhone": "+1 (312) 555-1234"  # required
    }

    Returns:
    {
      "status": "success",
      "data": {
        "sessionId": "...",
        "startedAt": "..."
      }
    }
    """
    body = request.get_json() or {}

    room_name = body.get("roomName")
    customer_phone_raw = body.get("customerPhone")

    if not room_name:
        raise ValidationError("roomName is required", HTTP_STATUS["BAD_REQUEST"])
    if not customer_phone_raw:
        raise ValidationError("customerPhone is required", HTTP_STATUS["BAD_REQUEST"])

    # Normalize phone
    customer_phone = clean_phone_number(customer_phone_raw)

    try:
        # Start voice session asynchronously
        session = asyncio.run(start_voice_session(room_name, customer_phone))

        if not session:
            raise ValidationError("Failed to start voice session", HTTP_STATUS["INTERNAL_SERVER_ERROR"])

        logger.info(f"🤖 AI voice session started in room: {room_name} for {customer_phone}")

        return (
            jsonify(
                {
                    "status": "success",
                    "data": {
                        "sessionId": id(session),  # Simple session ID
                        "roomName": room_name,
                        "customerPhone": customer_phone,
                        "startedAt": asyncio.run(session.get_timestamp()),
                    },
                }
            ),
            HTTP_STATUS["OK"],
        )

    except Exception as e:
        logger.error(f"Failed to start voice session: {e}")
        raise ValidationError("Failed to start voice session", HTTP_STATUS["INTERNAL_SERVER_ERROR"])


# ============================================
# POST /api/voice/stop-session
# ============================================
@voice_bp.route('/stop-session', methods=['POST'])
@handle_exceptions
def stop_session():
    """
    Stop current AI voice agent session.

    Returns:
    {
      "status": "success",
      "data": {
        "stoppedAt": "..."
      }
    }
    """
    try:
        # Stop voice session asynchronously
        asyncio.run(stop_voice_session())

        logger.info("🛑 AI voice session stopped")

        return (
            jsonify(
                {
                    "status": "success",
                    "data": {
                        "stoppedAt": asyncio.get_event_loop().time(),
                    },
                }
            ),
            HTTP_STATUS["OK"],
        )

    except Exception as e:
        logger.error(f"Failed to stop voice session: {e}")
        raise ValidationError("Failed to stop voice session", HTTP_STATUS["INTERNAL_SERVER_ERROR"])
