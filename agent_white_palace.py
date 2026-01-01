

from dotenv import load_dotenv
load_dotenv(".env")

import asyncio
import os
import json
from datetime import datetime
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
from livekit.plugins import openai, deepgram, cartesia, silero, elevenlabs, google
from livekit.agents import AgentServer

server = AgentServer()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")

class ConversationState:
    """Simple per-call state."""

    def __init__(self):
        self.start_time = datetime.now()
        self.caller_phone = "+10000000000"

    def to_context(self) -> str:
        return f"""
CALL START TIME: {self.start_time.isoformat()}
CALL DURATION: {(datetime.now() - self.start_time).seconds} seconds
CALLER PHONE: {self.caller_phone}
CURRENT DATE & TIME: {datetime.now().strftime('%B %d, %Y %I:%M %p')}
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
    deliveryAddress: Optional[str] = None,
    specialRequests: Optional[str] = None
) -> Dict:
    """
    Create a food order. Only call this when you have collected: items (with menuItemId, name, price, quantity), orderType, and customerName.
    
    Args:
        items: List of order items
        orderType: "pickup", "delivery", or "dine-in"
        customerName: Name of customer
        deliveryAddress: Required if orderType is delivery
        specialRequests: Optional notes
    """
    state = getattr(context.session, 'conversation_state', None)
    customer_phone = state.caller_phone if state else "+10000000000"
    
    print(f"🔄 CREATE ORDER: {len(items)} items for {customerName} ({customer_phone})")
    
    # Convert Pydantic models to dicts
    items_dicts = [item.model_dump() for item in items]

    payload = {
        "items": items_dicts,
        "orderType": orderType,
        "customerName": customerName,
        "customerPhone": customer_phone,
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
                    return data # Contains "available": True/False and "message"
                else:
                    return {"success": False, "available": False, "message": "Could not check availability."}
    except Exception as e:
        print(f"❌ AVAILABILITY ERROR: {e}")
        return {"success": False, "error": str(e)}

@llm.function_tool
async def create_reservation(
    context: RunContext,
    partySize: int,
    reservationDate: str,
    reservationTime: str,
    customerName: str,
    specialRequests: Optional[str] = None
) -> Dict:
    """
    Create a table reservation. Call check_reservation_availability first.
    
    Args:
        partySize: Number of people
        reservationDate: YYYY-MM-DD
        reservationTime: HH:MM (24-hour)
        customerName: Name of customer
        specialRequests: Optional notes
    """
    state = getattr(context.session, 'conversation_state', None)
    customer_phone = state.caller_phone if state else "+10000000000"
    
    print(f"🔄 CREATE RESERVATION: {partySize} ppl on {reservationDate} at {reservationTime}")
    
    payload = {
        "partySize": partySize,
        "reservationDate": reservationDate,
        "reservationTime": reservationTime,
        "customerName": customerName,
        "customerPhone": customer_phone,
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

    # Build system prompt with live state
    system_prompt = RESTAURANT_SYSTEM_PROMPT.replace(
        "{{conversation_state}}", 
        conversation_state.to_context()
    )

    # Create agent with instructions and tools
    restaurant_agent = Agent(
        instructions=system_prompt,
        tools=[
            get_menu_items,
            create_order,
            check_reservation_availability,
            create_reservation,
            transfer_to_human
        ],
    )

    # Create session with STT/LLM/TTS
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-2-phonecall",
            language="en-US",
            interim_results=True,
        ),
        llm=openai.LLM(
            model="gpt-4o-mini",  # Faster model
            timeout=60.0,
        ),
        tts=openai.TTS(
            model="gpt-4o-mini-tts",
            voice="alloy",
            speed=1.0,
        ),
        vad=silero.VAD.load(
            min_speech_duration=0.3,
            min_silence_duration=0.8,
            padding_duration=0.2,
            activation_threshold=0.5,
        ),
        allow_interruptions=True,
    )

    # Attach state to session for tool access
    session.conversation_state = conversation_state

    # Start the session - this handles the conversation loop automatically
    await session.start(room=ctx.room, agent=restaurant_agent)

    # Opening greeting
    await session.say(
        "Hi, thanks for calling White Palace Grill. "
        "How can I help you today with an order or a reservation?"
    )

    print("✅ Agent started and ready")

@server.rtc_session(agent_name="restaurant-telephony-agent")
async def telephony_entrypoint(ctx: JobContext):
    await entrypoint(ctx)

if __name__ == "__main__":
    cli.run_app(server)


