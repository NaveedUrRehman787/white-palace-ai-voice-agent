
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
from utils.livekit_service import livekit_service  # ← Add this
import asyncio  # ← Add this


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
# @twilio_bp.route("/voice/agent", methods=["POST"])
# @handle_exceptions
# def voice_agent():
#     """
#     Twilio Voice webhook for AI voice agent: creates LiveKit room and connects agent.
#     """
#     from_number = request.values.get("From", "")
#     to_number = request.values.get("To", "")
#     call_sid = request.values.get("CallSid", "")

#     normalized_from = clean_phone_number(from_number) if from_number else None

#     logger.info(
#         f"🤖 Starting AI voice agent: From={from_number} (normalized={normalized_from}), "
#         f"To={to_number}, CallSid={call_sid}"
#     )

#     resp = VoiceResponse()

#     # For now, provide a placeholder response
#     # In production, this would create a LiveKit room and connect the agent
#     resp.say(
#         "Connecting you to our AI assistant now. Please hold for a moment.",
#         voice="alice",
#         language="en-US",
#     )

#     # TODO: Integrate with LiveKit room creation and agent connection
#     # This would involve:
#     # 1. Create LiveKit room for this call
#     # 2. Start voice agent session in the room
#     # 3. Connect Twilio media stream to LiveKit room
#     # 4. Handle the bidirectional audio

#     resp.say(
#         "Our AI voice assistant is currently in development. "
#         "Please try our text-based ordering system or call back later. "
#         "Thank you for calling White Palace Grill.",
#         voice="alice",
#         language="en-US",
#     )

#     resp.hangup()

#     return Response(str(resp), mimetype="text/xml", status=HTTP_STATUS["OK"])

async def start_agent_session(room_info: dict, customer_phone: str):
    """Start AI voice agent session in LiveKit room"""
    try:
        from routes.voice_pipeline import start_voice_session
        
        # Start the voice session
        session = await start_voice_session(
            room_name=room_info["room_name"], 
            customer_phone=customer_phone
        )
        
        if session:
            logger.info(f"✅ AI agent started for {customer_phone} in room {room_info['room_name']}")
        else:
            logger.error(f"❌ Failed to start AI agent for {customer_phone}")
            
    except Exception as e:
        logger.error(f"❌ Agent session startup error: {e}")


@twilio_bp.route("/voice/agent", methods=["POST"])
@handle_exceptions
def voice_agent():
    """
    Connect incoming Twilio call to LiveKit AI voice agent
    """
    from_number = request.values.get("From", "")
    call_sid = request.values.get("CallSid", "")
    
    normalized_from = clean_phone_number(from_number)
    
    logger.info(f"🤖 Starting AI agent for: {normalized_from}")
    
    # 1. Create LiveKit room for this call
    room_info = livekit_service.create_voice_room(normalized_from)
    if not room_info:
        # Fallback response
        resp = VoiceResponse()
        resp.say("Sorry, our voice assistant is temporarily unavailable. Please try again later.")
        resp.hangup()
        return Response(str(resp), mimetype="text/xml")
    
    # 2. Start the AI agent session in the room
    try:
        # Start agent synchronously (LiveKit requires main thread for plugins)
        import asyncio

        # Create event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Schedule the agent startup
        loop.create_task(start_agent_session(room_info, normalized_from))
        logger.info("✅ Agent startup task scheduled")
    except Exception as e:
        logger.error(f"❌ Failed to start agent session: {e}")
    
    # 3. Connect Twilio to LiveKit room
    resp = VoiceResponse()
    
    # Start bidirectional media stream
    start = Start()
    stream = Stream(url=f"{room_info['livekit_url']}/twilio")
    stream.parameter(name="roomName", value=room_info["room_name"])
    stream.parameter(name="participantIdentity", value=f"customer_{normalized_from}")
    stream.parameter(name="token", value=room_info["customer_token"])
    start.append(stream)
    resp.append(start)
    
    return Response(str(resp), mimetype="text/xml")


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
