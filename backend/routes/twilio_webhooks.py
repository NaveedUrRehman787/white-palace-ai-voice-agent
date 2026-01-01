# """
# Twilio Webhook Routes
# Handles incoming voice calls and call status callbacks.

# Endpoints:
# - POST /api/twilio/voice   -> Voice webhook (A Call Comes In)
# - POST /api/twilio/status  -> Call status callback
# """

# from flask import Blueprint, request, Response, current_app
# from config.constants import HTTP_STATUS
# from middleware.error_handler import handle_exceptions
# from utils.helpers import clean_phone_number
# from twilio.twiml.voice_response import VoiceResponse
# import logging

# logger = logging.getLogger(__name__)

# twilio_bp = Blueprint("twilio", __name__)


# # ============================================
# # POST /api/twilio/voice  -> Incoming call
# # ============================================
# @twilio_bp.route("/voice", methods=["POST"])
# @handle_exceptions
# def incoming_call():
#     """
#     Twilio Voice webhook: called when an incoming call hits your Twilio number.

#     For now:
#     - Greets the caller.
#     - Announces this is a test backend.
#     - Keeps the call simple (no media stream yet).
#     """
#     from_number = request.values.get("From", "")
#     to_number = request.values.get("To", "")
#     call_sid = request.values.get("CallSid", "")

#     # Normalize caller phone if present
#     normalized_from = clean_phone_number(from_number) if from_number else None

#     logger.info(
#         f"📞 Incoming call: From={from_number} (normalized={normalized_from}), "
#         f"To={to_number}, CallSid={call_sid}"
#     )

#     # Build TwiML response
#     resp = VoiceResponse()

#     # Simple greeting for now
#     resp.say(
#         "Thank you for calling White Palace Grill. "
#         "This is the test backend speaking. "
#         "Your call reached our AI voice agent system. "
#         "Goodbye.",
#         voice="alice",
#         language="en-US",
#     )
#     resp.hangup()

#     xml = str(resp)
#     return Response(xml, mimetype="text/xml", status=HTTP_STATUS["OK"])


# # ============================================
# # POST /api/twilio/status  -> Call status callback
# # ============================================
# @twilio_bp.route("/status", methods=["POST"])
# @handle_exceptions
# def call_status():
#     """
#     Optional: Twilio Voice status callback.

#     Twilio sends this when the call status changes (ringing, in-progress, completed, etc.).
#     For now, just log the events.
#     """
#     call_sid = request.values.get("CallSid", "")
#     call_status = request.values.get("CallStatus", "")
#     from_number = request.values.get("From", "")
#     to_number = request.values.get("To", "")

#     logger.info(
#         f"📊 Call status update: CallSid={call_sid}, Status={call_status}, "
#         f"From={from_number}, To={to_number}"
#     )

#     # Twilio expects a 200 with empty body or simple XML
#     return Response("", status=HTTP_STATUS["NO_CONTENT"])


"""
Twilio Webhook Routes
Handles incoming voice calls and call status callbacks.

Flows:
- /api/twilio/voice        -> Main greeting + menu (Gather)
- /api/twilio/voice/gather -> Handle key press and respond
- /api/twilio/status       -> Call status callback (logging only)
"""

from flask import Blueprint, request, Response
from config.constants import HTTP_STATUS
from middleware.error_handler import handle_exceptions
from utils.helpers import clean_phone_number
from twilio.twiml.voice_response import VoiceResponse, Gather, Start, Stream
import logging

logger = logging.getLogger(__name__)

twilio_bp = Blueprint("twilio", __name__)


# ============================================
# POST /api/twilio/voice  -> Main IVR entry
# ============================================
@twilio_bp.route("/voice", methods=["POST"])
@handle_exceptions
def incoming_call():
    """
    Main Twilio Voice webhook: greets caller with White Palace message
    and offers a simple menu using <Gather>.
    """
    from_number = request.values.get("From", "")
    to_number = request.values.get("To", "")
    call_sid = request.values.get("CallSid", "")

    normalized_from = clean_phone_number(from_number) if from_number else None

    logger.info(
        f"📞 Incoming call: From={from_number} (normalized={normalized_from}), "
        f"To={to_number}, CallSid={call_sid}"
    )

    resp = VoiceResponse()

    # Start Gather: wait for 1 digit, then POST to /api/twilio/voice/gather
    gather = Gather(
        num_digits=1,
        action="/api/twilio/voice/gather",
        method="POST",
        timeout=5,
    )

    gather.say(
        "Welcome to White Palace Grill in Chicago. "
        "For pickup or delivery orders, press 1. "
        "To make or check a reservation, press 2. "
        "For hours and location, press 3. "
        "To hear these options again, press 9.",
        voice="alice",
        language="en-US",
    )

    resp.append(gather)

    # If no input, fall back message
    resp.say(
        "We did not receive any input. "
        "Please call back or visit us at White Palace Grill. Goodbye.",
        voice="alice",
        language="en-US",
    )
    resp.hangup()

    return Response(str(resp), mimetype="text/xml", status=HTTP_STATUS["OK"])


# ============================================
# POST /api/twilio/voice/agent  -> AI Voice Agent
# ============================================
@twilio_bp.route("/voice/agent", methods=["POST"])
@handle_exceptions
def voice_agent():
    """
    Twilio Voice webhook for AI voice agent: creates LiveKit room and connects agent.
    """
    from_number = request.values.get("From", "")
    to_number = request.values.get("To", "")
    call_sid = request.values.get("CallSid", "")

    normalized_from = clean_phone_number(from_number) if from_number else None

    logger.info(
        f"🤖 Starting AI voice agent: From={from_number} (normalized={normalized_from}), "
        f"To={to_number}, CallSid={call_sid}"
    )

    resp = VoiceResponse()

    # For now, provide a placeholder response
    # In production, this would create a LiveKit room and connect the agent
    resp.say(
        "Connecting you to our AI assistant now. Please hold for a moment.",
        voice="alice",
        language="en-US",
    )

    # TODO: Integrate with LiveKit room creation and agent connection
    # This would involve:
    # 1. Create LiveKit room for this call
    # 2. Start voice agent session in the room
    # 3. Connect Twilio media stream to LiveKit room
    # 4. Handle the bidirectional audio

    resp.say(
        "Our AI voice assistant is currently in development. "
        "Please try our text-based ordering system or call back later. "
        "Thank you for calling White Palace Grill.",
        voice="alice",
        language="en-US",
    )

    resp.hangup()

    return Response(str(resp), mimetype="text/xml", status=HTTP_STATUS["OK"])


# ============================================
# POST /api/twilio/voice/gather  -> Handle keypress
# ============================================
@twilio_bp.route("/voice/gather", methods=["POST"])
@handle_exceptions
def handle_gather():
    """
    Handle the result of <Gather> from the main menu.
    """
    digits = request.values.get("Digits", "")
    from_number = request.values.get("From", "")
    call_sid = request.values.get("CallSid", "")

    logger.info(
        f"📲 Gather input: Digits={digits}, From={from_number}, CallSid={call_sid}"
    )

    resp = VoiceResponse()

    if digits == "1":
        # Orders path - redirect to AI voice agent
        resp.say(
            "You selected orders. Connecting you to our AI assistant now.",
            voice="alice",
            language="en-US",
        )
        resp.redirect("/api/twilio/voice/agent", method="POST")

    elif digits == "2":
        # Reservations path - redirect to AI voice agent
        resp.say(
            "You selected reservations. Connecting you to our AI assistant now.",
            voice="alice",
            language="en-US",
        )
        resp.redirect("/api/twilio/voice/agent", method="POST")

    elif digits == "3":
        # Hours & location
        resp.say(
            "White Palace Grill is open twenty four hours a day, seven days a week, "
            "at fourteen fifty five South Canal Street in Chicago. "
            "We look forward to serving you. Goodbye.",
            voice="alice",
            language="en-US",
        )
        resp.hangup()

    elif digits == "9":
        # Repeat menu by redirecting back to /voice
        resp.say("Repeating the menu.", voice="alice", language="en-US")
        resp.redirect("/api/twilio/voice", method="POST")

    else:
        # Invalid or unexpected input
        resp.say(
            "Sorry, that is not a valid option. Goodbye.",
            voice="alice",
            language="en-US",
        )
        resp.hangup()

    return Response(str(resp), mimetype="text/xml", status=HTTP_STATUS["OK"])


# ============================================
# POST /api/twilio/status  -> Call status callback
# ============================================
@twilio_bp.route("/status", methods=["POST"])
@handle_exceptions
def call_status():
    """
    Twilio Voice status callback for logging call lifecycle.
    """
    call_sid = request.values.get("CallSid", "")
    call_status = request.values.get("CallStatus", "")
    from_number = request.values.get("From", "")
    to_number = request.values.get("To", "")

    logger.info(
        f"📊 Call status update: CallSid={call_sid}, Status={call_status}, "
        f"From={from_number}, To={to_number}"
    )

    return Response("", status=HTTP_STATUS["NO_CONTENT"])
