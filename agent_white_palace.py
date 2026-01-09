

from dotenv import load_dotenv
load_dotenv(".env")

import asyncio
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.agents.types import APIConnectOptions
from backend.prompt import SYSTEM_PROMPT
import aiohttp
from pydantic import BaseModel, Field

from livekit.agents import (
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    Agent,
    RunContext,
)
from livekit.plugins import openai, deepgram, silero, elevenlabs, google, aws
from livekit.agents import AgentServer

server = AgentServer()

# BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")
# For Docker environments, use the service name 'backend'
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:5000")

class ConversationState:
    """Simple per-call state."""

    def __init__(self):
        self.start_time = datetime.now()
        self.caller_phone = "+10000000000"

    def to_context(self) -> str:
        now = datetime.now()
        return f"""
CALL START TIME: {self.start_time.isoformat()}
CALL DURATION: {(now - self.start_time).seconds} seconds
CALLER PHONE: {self.caller_phone}
CURRENT DATE & TIME: {now.strftime('%B %d, %Y %I:%M %p')}
CURRENT YEAR: {now.year}
TODAY: {now.strftime('%Y-%m-%d')}
TOMORROW: {(now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime('%Y-%m-%d')}
"""

class OrderItem(BaseModel):
    menuItemId: int
    name: str
    price: float
    quantity: int

# ============================================================================
# FUNCTION TOOLS
# ============================================================================

@llm.function_tool
async def get_menu_items(
    context: RunContext,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict:
    """
    Get menu items by category or search term. Returns real menu items with prices.
    
    Args:
        category: Category filter (breakfast, burgers, sandwiches, entrees, salads, soups, sides, desserts, beverages)
        search: Search term to find specific items
    """
    print(f"🔄 GET MENU: Category='{category}', Search='{search}'")
    
    params = {}
    if category: params['category'] = category
    if search: params['q'] = search
    
    endpoint = f"{BACKEND_URL}/api/menu/search" if search else f"{BACKEND_URL}/api/menu"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Limit results to avoid overwhelming the LLM context
                    items = data.get("data", [])
                    if isinstance(items, dict) and "items" in items: # Handle /api/menu response structure
                         items = items["items"]
                    elif isinstance(items, dict) and "data" in items: # Handle /api/menu/search response structure
                         items = items["data"]
                         
                    # Determine how many to return
                    if len(items) > 10:
                        items = items[:10]
                        
                    return {"success": True, "items": items, "count": len(items)}
                else:
                    return {"success": False, "error": f"Failed to fetch menu: {resp.status}"}
    except Exception as e:
        print(f"❌ MENU ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def create_order(
    context: RunContext,
    items: List[OrderItem],
    orderType: str,
    customerName: str,
    customerPhone: str,
    deliveryAddress: Optional[str] = None,
    specialRequests: Optional[str] = None
) -> Dict:
    """
    Create a food order. Only call this when you have collected: items (with menuItemId, name, price, quantity), orderType, customerName, and customerPhone.
    
    Args:
        items: List of order items
        orderType: "pickup", "delivery", or "dine-in"
        customerName: Name of customer
        customerPhone: The customer's phone number
        deliveryAddress: Required if orderType is delivery
        specialRequests: Optional notes
    """
    print(f"🔄 CREATE ORDER: {len(items)} items for {customerName} ({customerPhone})")
    
    # Convert Pydantic models to dicts
    items_dicts = [item.model_dump() for item in items]

    payload = {
        "items": items_dicts,
        "orderType": orderType,
        "customerName": customerName,
        "customerPhone": customerPhone,
        "deliveryAddress": deliveryAddress,
        "specialRequests": specialRequests
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/api/orders", json=payload, timeout=15) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    order_data = data.get("data", {})
                    return {
                        "success": True,
                        "orderNumber": order_data.get("orderNumber"),
                        "totalPrice": order_data.get("totalPrice"),
                        "estimatedReadyTime": order_data.get("estimatedReadyTime"),
                        "message": "Order created successfully"
                    }
                else:
                    err_text = await resp.text()
                    return {"success": False, "error": f"Failed to create order: {err_text}"}
    except Exception as e:
        print(f"❌ ORDER ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def check_reservation_availability(
    context: RunContext,
    reservationDate: str,
    reservationTime: str,
    partySize: int
) -> Dict:
    """
    Check if a reservation time slot is available. Always call this BEFORE creating a reservation.

    Args:
        reservationDate: YYYY-MM-DD
        reservationTime: HH:MM (24-hour)
        partySize: Number of people
    """
    print(f"🔄 CHECK AVAILABILITY: {reservationDate} {reservationTime} for {partySize}")

    payload = {
        "reservationDate": reservationDate,
        "reservationTime": reservationTime,
        "partySize": partySize
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/api/reservations/availability", json=payload, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("data", data)  # Handle different response formats

                    # Add helpful suggestions if not available
                    if not result.get("available", False):
                        message = result.get("message", "Time not available")

                        # If it's about advance notice, suggest alternatives
                        if "15 minutes" in message or "advance" in message:
                            alternatives = await suggest_alternative_times(reservationDate, reservationTime, partySize)
                            if alternatives:
                                result["alternatives"] = alternatives
                                result["message"] = f"{message} Would you like to try {alternatives[0]} instead?"

                        # If it's capacity issue, suggest nearby times
                        elif "availability" in message.lower() or "full" in message.lower():
                            alternatives = await suggest_alternative_times(reservationDate, reservationTime, partySize)
                            if alternatives:
                                result["alternatives"] = alternatives
                                result["message"] = f"That time is fully booked. How about {alternatives[0]}?"

                    return result
                else:
                    return {"success": False, "available": False, "message": "Could not check availability."}
    except Exception as e:
        print(f"❌ AVAILABILITY ERROR: {e}")
        return {"success": False, "available": False, "message": "Sorry, I couldn't check availability right now."}

async def suggest_alternative_times(reservation_date: str, reservation_time: str, party_size: int) -> List[str]:
    """
    Suggest alternative reservation times when the requested time is not available.

    Args:
        reservation_date: YYYY-MM-DD
        reservation_time: HH:MM (24-hour)
        party_size: Number of people

    Returns:
        List of suggested time strings in "H:MM PM" format
    """
    try:
        # Parse the requested time
        requested_hour = int(reservation_time.split(':')[0])
        requested_minute = int(reservation_time.split(':')[1])

        # Generate alternative times: ±15, ±30, ±45 minutes
        time_offsets = [-45, -30, -15, 15, 30, 45]
        alternatives = []

        for offset in time_offsets:
            new_minute = requested_minute + offset
            new_hour = requested_hour

            # Handle minute overflow/underflow
            if new_minute >= 60:
                new_hour += 1
                new_minute -= 60
            elif new_minute < 0:
                new_hour -= 1
                new_minute += 60

            # Handle hour overflow (assume restaurant closes at 11 PM)
            if new_hour >= 23:
                continue
            # Handle hour underflow (assume restaurant opens at 6 AM)
            if new_hour < 6:
                continue

            # Format time
            time_str = f"{new_hour:02d}:{new_minute:02d}"
            
            # Format for spoken response (e.g., "7:30 PM")
            period = "AM" if new_hour < 12 else "PM"
            display_hour = new_hour if new_hour <= 12 else new_hour - 12
            if display_hour == 0: display_hour = 12
            formatted_time = f"{display_hour}:{new_minute:02d} {period}"

            # Check if this alternative time is available
            payload = {
                "reservationDate": reservation_date,
                "reservationTime": time_str,
                "partySize": party_size
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{BACKEND_URL}/api/reservations/availability", json=payload, timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            result = data.get("data", data)
                            if result.get("available", False):
                                alternatives.append(formatted_time)
                                if len(alternatives) >= 3:  # Only return 3 alternatives
                                    break
            except:
                continue

        return alternatives[:3]  # Return up to 3 alternatives

    except Exception as e:
        print(f"❌ ALTERNATIVE TIMES ERROR: {e}")
        return []

@llm.function_tool
async def create_reservation(
    context: RunContext,
    partySize: int,
    reservationDate: str,
    reservationTime: str,
    customerName: str,
    customerPhone: str,
    specialRequests: Optional[str] = None
) -> Dict:
    """
    Create a table reservation. Call check_reservation_availability first.
    
    Args:
        partySize: Number of people
        reservationDate: YYYY-MM-DD
        reservationTime: HH:MM (24-hour)
        customerName: Name of customer
        customerPhone: The customer's phone number
        specialRequests: Optional notes
    """
    print(f"🔄 CREATE RESERVATION: {partySize} ppl on {reservationDate} at {reservationTime} for {customerName}")
    
    payload = {
        "partySize": partySize,
        "reservationDate": reservationDate,
        "reservationTime": reservationTime,
        "customerName": customerName,
        "customerPhone": customerPhone,
        "specialRequests": specialRequests
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/api/reservations", json=payload, timeout=15) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    res_data = data.get("data", {})
                    return {
                        "success": True,
                        "reservationNumber": res_data.get("reservationNumber"),
                        "message": "Reservation confirmed"
                    }
                else:
                    err_text = await resp.text()
                    return {"success": False, "error": f"Failed to create reservation: {err_text}"}
    except Exception as e:
        print(f"❌ RESERVATION ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def transfer_to_human(
    context: RunContext,
    reason: str = "complex_issue",
) -> Dict:
    """
    Transfer the call to a human staff member.
    Use this only when explicitly requested by the customer or for very complex issues.

    Args:
        reason: Why transfer is needed

    Returns:
        Dict with transfer status
    """
    print(f"🔀 TRANSFER REQUESTED: Reason={reason}")

    return {
        "success": True,
        "message": "I'll connect you with a staff member at the restaurant for more help.",
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    }

@llm.function_tool
async def get_hours(context: RunContext) -> Dict:
    """
    Get the restaurant's operating hours.

    Returns:
        Dict with hours information
    """
    from backend.config.restaurant_config import RESTAURANT_CONFIG

    print("🕒 GET HOURS REQUESTED")

    hours = RESTAURANT_CONFIG.get("hours", {})
    timezone = RESTAURANT_CONFIG.get("timezone", "America/Chicago")

    # Format hours for response
    formatted_hours = {}
    for day, times in hours.items():
        formatted_hours[day] = {
            "open": times.get("open", "Closed"),
            "close": times.get("close", "Closed")
        }

    return {
        "success": True,
        "hours": formatted_hours,
        "timezone": timezone,
        "message": "Here are our operating hours."
    }

@llm.function_tool
async def get_location(context: RunContext) -> Dict:
    """
    Get the restaurant's location and contact information.

    Returns:
        Dict with location information
    """
    from backend.config.restaurant_config import RESTAURANT_CONFIG

    print("📍 GET LOCATION REQUESTED")

    return {
        "success": True,
        "name": RESTAURANT_CONFIG.get("name"),
        "address": RESTAURANT_CONFIG.get("address"),
        "city": RESTAURANT_CONFIG.get("city"),
        "state": RESTAURANT_CONFIG.get("state"),
        "zip_code": RESTAURANT_CONFIG.get("zip_code"),
        "phone": RESTAURANT_CONFIG.get("phone"),
        "website": RESTAURANT_CONFIG.get("website"),
        "email": RESTAURANT_CONFIG.get("email"),
        "established_year": RESTAURANT_CONFIG.get("established_year"),
        "message": f"We're located at {RESTAURANT_CONFIG.get('address')}, {RESTAURANT_CONFIG.get('city')}, {RESTAURANT_CONFIG.get('state')} {RESTAURANT_CONFIG.get('zip_code')}."
    }

@llm.function_tool
async def get_order_by_number(
    context: RunContext,
    orderNumber: str
) -> Dict:
    """
    Get order details by order number.

    Args:
        orderNumber: The order number to look up (e.g., OR-12345)

    Returns:
        Dict with order information
    """
    print(f"🔍 GET ORDER: {orderNumber}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/orders/number/{orderNumber}", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    order = data.get("data", {})
                    return {
                        "success": True,
                        "order": order,
                        "message": f"Found order {orderNumber}."
                    }
                else:
                    return {"success": False, "error": f"Order {orderNumber} not found."}
    except Exception as e:
        print(f"❌ ORDER LOOKUP ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def update_order_status_by_orderNumber(
    context: RunContext,
    orderNumber: str,
    status: str
) -> Dict:
    """
    Update an order's status by order number.

    Args:
        orderNumber: The order number to update
        status: New status ("confirmed", "preparing", "ready", "completed", "cancelled")

    Returns:
        Dict with update result
    """
    print(f"📝 UPDATE ORDER STATUS: {orderNumber} -> {status}")

    payload = {"status": status}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(f"{BACKEND_URL}/api/orders/number/{orderNumber}/status", json=payload, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    order = data.get("data", {})
                    return {
                        "success": True,
                        "order": order,
                        "message": f"Order {orderNumber} status updated to {status}."
                    }
                else:
                    err_text = await resp.text()
                    return {"success": False, "error": f"Failed to update order {orderNumber}: {err_text}"}
    except Exception as e:
        print(f"❌ ORDER UPDATE ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def cancel_order_by_number(
    context: RunContext,
    orderNumber: str
) -> Dict:
    """
    Cancel an order by order number.

    Args:
        orderNumber: The order number to cancel

    Returns:
        Dict with cancellation result
    """
    print(f"❌ CANCEL ORDER: {orderNumber}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{BACKEND_URL}/api/orders/number/{orderNumber}", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    order = data.get("data", {})
                    return {
                        "success": True,
                        "order": order,
                        "message": f"Order {orderNumber} has been cancelled."
                    }
                else:
                    err_text = await resp.text()
                    return {"success": False, "error": f"Failed to cancel order {orderNumber}: {err_text}"}
    except Exception as e:
        print(f"❌ ORDER CANCEL ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def get_reservation_by_number(
    context: RunContext,
    reservationNumber: str
) -> Dict:
    """
    Get reservation details by reservation number.

    Args:
        reservationNumber: The reservation number to look up

    Returns:
        Dict with reservation information
    """
    print(f"🔍 GET RESERVATION: {reservationNumber}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/reservations/number/{reservationNumber}", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    reservation = data.get("data", {})
                    return {
                        "success": True,
                        "reservation": reservation,
                        "message": f"Found reservation {reservationNumber}."
                    }
                else:
                    return {"success": False, "error": f"Reservation {reservationNumber} not found."}
    except Exception as e:
        print(f"❌ RESERVATION LOOKUP ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def update_reservation_status_by_reservationNumber(
    context: RunContext,
    reservationNumber: str,
    status: str
) -> Dict:
    """
    Update a reservation's status by reservation number.

    Args:
        reservationNumber: The reservation number to update
        status: New status ("pending", "confirmed", "completed", "cancelled", "no_show")

    Returns:
        Dict with update result
    """
    print(f"📝 UPDATE RESERVATION STATUS: {reservationNumber} -> {status}")

    payload = {"status": status}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(f"{BACKEND_URL}/api/reservations/number/{reservationNumber}/status", json=payload, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    reservation = data.get("data", {})
                    return {
                        "success": True,
                        "reservation": reservation,
                        "message": f"Reservation {reservationNumber} status updated to {status}."
                    }
                else:
                    err_text = await resp.text()
                    return {"success": False, "error": f"Failed to update reservation {reservationNumber}: {err_text}"}
    except Exception as e:
        print(f"❌ RESERVATION UPDATE ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def cancel_reservation_by_number(
    context: RunContext,
    reservationNumber: str
) -> Dict:
    """
    Cancel a reservation by reservation number.

    Args:
        reservationNumber: The reservation number to cancel

    Returns:
        Dict with cancellation result
    """
    print(f"❌ CANCEL RESERVATION: {reservationNumber}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{BACKEND_URL}/api/reservations/number/{reservationNumber}", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    reservation = data.get("data", {})
                    return {
                        "success": True,
                        "reservation": reservation,
                        "message": f"Reservation {reservationNumber} has been cancelled."
                    }
                else:
                    err_text = await resp.text()
                    return {"success": False, "error": f"Failed to cancel reservation {reservationNumber}: {err_text}"}
    except Exception as e:
        print(f"❌ RESERVATION CANCEL ERROR: {e}")
        return {"success": False, "error": str(e)}

# ============================================================================
# SYSTEM PROMPT
# ============================================================================
RESTAURANT_SYSTEM_PROMPT = SYSTEM_PROMPT

# ============================================================================
# ENTRYPOINT
# ============================================================================

async def entrypoint(ctx: JobContext):
    """Restaurant telephony agent entrypoint."""
    
    await ctx.connect()
    print(f"🚀 Connected to room: {ctx.room.name}")

    conversation_state = ConversationState()

    # Extract caller phone from metadata if available
    try:
        if ctx.job.metadata:
            meta = json.loads(ctx.job.metadata)
            conversation_state.caller_phone = meta.get("phone_number", "+10000000000")
    except Exception as e:
        print(f"⚠️ Could not parse metadata: {e}")

    print(f"📞 Caller phone: {conversation_state.caller_phone}")

    # Build system prompt with live state and current datetime
    now = datetime.now()
    system_prompt = RESTAURANT_SYSTEM_PROMPT.replace(
        "{{conversation_state}}",
        conversation_state.to_context()
    ).replace(
        "{{CURRENT_DATETIME}}", now.strftime('%Y-%m-%d %H:%M:%S')
    ).replace(
        "{{CURRENT_YEAR}}", str(now.year)
    ).replace(
        "{{TODAY}}", now.strftime('%Y-%m-%d')
    ).replace(
        "{{TOMORROW}}", (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime('%Y-%m-%d')
    ).replace(
        "{{CALLER_PHONE}}", conversation_state.caller_phone
    ).replace(
        "{{SESSION_ID}}", "local-console-session"
    )

    # Create agent with instructions and tools
    restaurant_agent = Agent(
        instructions=system_prompt,
        tools=[
            get_menu_items,
            create_order,
            check_reservation_availability,
            create_reservation,
            transfer_to_human,
            get_hours,
            get_location,
            get_order_by_number,
            update_order_status_by_orderNumber,
            cancel_order_by_number,
            get_reservation_by_number,
            update_reservation_status_by_reservationNumber,
            cancel_reservation_by_number
        ],
    )
    

    # ✨ USE NOVA SONIC - Just this one line!
    session = AgentSession(
        llm=aws.realtime.RealtimeModel(
            voice="matthew",  # Professional female voice
            region=os.getenv("AWS_REGION", "us-east-1"),
        ),
    )


#
    # Create session with STT/LLM/TTS
    # session = AgentSession(
    #     stt=deepgram.STT(
    #         model="nova-2-phonecall",
    #         language="en-US",
    #         interim_results=True,
    #     ),
    #     llm=openai.LLM(
    #         model="gpt-4o-mini",
    #         timeout=20.0,
    #         temperature=0.1,
    #         max_completion_tokens=64, # 🔧 Keep responses short for lower latency
    #     ),
    #     tts=openai.TTS(
    #         model="tts-1",
    #         voice="alloy", # 🔧 Safer baseline for local testing
    #     ),
    #     vad=silero.VAD.load(
    #         min_speech_duration=0.05, 
    #         min_silence_duration=0.2, 
    #         prefix_padding_duration=0.05,
    #         activation_threshold=0.25, # 🔧 More sensitive (less static/noise rejection)
    #         max_buffered_speech=30.0,
    #     ),
        
    #     allow_interruptions=True,
    #     min_endpointing_delay=0.05, 
    # )


    # session = AgentSession(
    #     stt=deepgram.STT(
    #         model="nova-2",
    #         language="en-US",
    #         interim_results=True,  # Skip interim
    #     ),

    #     llm=openai.LLM(
    #         model="gpt-4.1",
    #         timeout=12.0,
    #         temperature=0.1,
    #         max_completion_tokens=60,
    #     ),
    #      tts=deepgram.TTS(
    #         model="nova-2",
    #     ),
    #     vad=silero.VAD.load(
    #         min_speech_duration=0.05,
    #         min_silence_duration=0.02,
    #         activation_threshold=0.4,
    #         max_buffered_speech=25.0,
    #     ),
    #     allow_interruptions=True,
    #     min_endpointing_delay=0.1,
    # )


    # Attach state to session for tool access
    session.conversation_state = conversation_state

    # Start the session - this handles the conversation loop automatically
    await session.start(room=ctx.room, agent=restaurant_agent)

    # Opening greeting
    # await session.say(
    #     "Hi, thanks for calling White Palace Grill. "
    #     "How can I help you today with an order or a reservation?"
    # )

    print("✅ Agent started and ready")

@server.rtc_session(agent_name="restaurant-telephony-agent")
async def telephony_entrypoint(ctx: JobContext):
    await entrypoint(ctx)

if __name__ == "__main__":
    cli.run_app(server)
