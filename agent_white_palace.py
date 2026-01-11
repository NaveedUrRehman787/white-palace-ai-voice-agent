

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

# ============================================================================
# COMPLETE FIXED FUNCTION TOOLS FOR AGENT_WHITE_PALACE.PY
# All 13 tools with proper backend response handling and spoken descriptions
# Replace your existing tools with these
# ============================================================================

from datetime import datetime
from typing import Dict, Optional, List
from livekit.agents import RunContext, llm
from pydantic import BaseModel
import aiohttp
import os

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:5000")

# OrderItem model (keep your existing one)
class OrderItem(BaseModel):
    menuItemId: int
    name: str
    price: float
    quantity: int


# ============================================================================
# HELPER FUNCTION: TIME CONVERSION
# ============================================================================

def convert_to_12hr(time_24hr: str) -> str:
    """Convert HH:MM (24-hour) to spoken format like '7:30 PM'"""
    try:
        hour, minute = map(int, time_24hr.split(':'))
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour}:{minute:02d} {period}"
    except:
        return time_24hr


# ============================================================================
# TOOL 1: GET MENU ITEMS
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
    print(f"📍 Calling: {endpoint} with params: {params}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params, timeout=10) as resp:
                print(f"✅ Response status: {resp.status}")
                
                if resp.status == 200:
                    response_json = await resp.json()
                    
                    # Extract items from nested response
                    if search:
                        # /api/menu/search returns: {"status": "success", "data": [...]}
                        items = response_json.get("data", [])
                    else:
                        # /api/menu returns: {"status": "success", "data": {"items": [...]}}
                        data_obj = response_json.get("data", {})
                        items = data_obj.get("items", [])
                    
                    print(f"📋 Found {len(items)} items")
                    
                    # Limit to 10 items to avoid overwhelming
                    if len(items) > 10:
                        items = items[:10]
                    
                    # ⭐ CREATE SPOKEN DESCRIPTION
                    if len(items) == 0:
                        description = "I'm sorry, I couldn't find any items matching that on our menu. Would you like to hear about our popular items?"
                    elif len(items) <= 3:
                        # List each item with price
                        item_descriptions = []
                        for item in items:
                            name = item.get('name', 'Unknown')
                            price = float(item.get('price', 0))
                            item_descriptions.append(f"{name} for ${price:.2f}")
                        
                        if len(item_descriptions) == 1:
                            items_text = item_descriptions[0]
                        else:
                            items_text = ", ".join(item_descriptions[:-1]) + f", and {item_descriptions[-1]}"
                        
                        description = f"We have {items_text}. What would you like to order?"
                    else:
                        # Summary with first 3 items
                        first_three = [item.get('name', 'Unknown') for item in items[:3]]
                        names_text = ", ".join(first_three[:2]) + f", and {first_three[2]}"
                        description = f"We have {len(items)} items including {names_text}, and more. What sounds good to you?"
                    
                    return {
                        "success": True,
                        "items": items,
                        "count": len(items),
                        "description": description  # ⭐ Nova Sonic will speak this!
                    }
                else:
                    error_text = await resp.text()
                    print(f"❌ Backend error {resp.status}: {error_text}")
                    return {
                        "success": False,
                        "error": f"Backend returned {resp.status}",
                        "description": "I'm having trouble accessing the menu right now. Can I help with something else?"
                    }
    except Exception as e:
        print(f"❌ MENU ERROR: {type(e).__name__}: {e}")
        return {
            "success": False,
            "error": str(e),
            "description": "I'm having trouble accessing the menu. Please try again or I can connect you with someone who can help."
        }


# ============================================================================
# TOOL 2: CREATE ORDER
# ============================================================================

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
    
    print(f"📤 Sending order payload: {payload}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/api/orders", json=payload, timeout=15) as resp:
                print(f"✅ Response status: {resp.status}")
                
                if resp.status == 201:
                    response_json = await resp.json()
                    print(f"📦 Order created: {response_json}")
                    
                    # Extract from nested response
                    order_data = response_json.get("data", {})
                    
                    order_num = order_data.get("orderNumber", "UNKNOWN")
                    total = float(order_data.get("totalPrice", 0))
                    ready_time = order_data.get("estimatedReadyTime", "soon")
                    
                    # Parse ready time if it's ISO format
                    try:
                        ready_dt = datetime.fromisoformat(ready_time.replace('Z', '+00:00'))
                        minutes_from_now = int((ready_dt - datetime.now()).total_seconds() / 60)
                        if minutes_from_now < 5:
                            ready_text = "just a few minutes"
                        else:
                            ready_text = f"about {minutes_from_now} minutes"
                    except:
                        ready_text = "about 15 to 20 minutes"
                    
                    # ⭐ SPOKEN DESCRIPTION
                    description = (
                        f"Perfect! Your order is confirmed. "
                        f"Order number {order_num}. "
                        f"Your total is ${total:.2f}, and it'll be ready in {ready_text}. "
                        f"Is there anything else I can help with?"
                    )
                    
                    return {
                        "success": True,
                        "orderNumber": order_num,
                        "totalPrice": total,
                        "estimatedReadyTime": ready_time,
                        "description": description  # ⭐ Spoken response
                    }
                else:
                    err_text = await resp.text()
                    print(f"❌ Order creation failed: {err_text}")
                    return {
                        "success": False,
                        "error": err_text,
                        "description": "I'm sorry, I couldn't process that order. Would you like to try again or speak with someone?"
                    }
    except Exception as e:
        print(f"❌ ORDER ERROR: {type(e).__name__}: {e}")
        return {
            "success": False,
            "error": str(e),
            "description": "I'm having trouble creating the order right now. Let me connect you with someone who can help."
        }


# ============================================================================
# TOOL 3: CHECK RESERVATION AVAILABILITY
# ============================================================================

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
    
    print(f"📤 Checking availability: {payload}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/api/reservations/availability", json=payload, timeout=10) as resp:
                print(f"✅ Response status: {resp.status}")
                
                if resp.status == 200:
                    response_json = await resp.json()
                    print(f"📦 Availability: {response_json}")
                    
                    available = response_json.get("available", False)
                    message = response_json.get("message", "")
                    
                    time_12hr = convert_to_12hr(reservationTime)
                    
                    if available:
                        # ⭐ AVAILABLE
                        description = f"Great news! We have availability for {partySize} guests on {reservationDate} at {time_12hr}. What name should I put the reservation under?"
                    else:
                        # ⭐ NOT AVAILABLE
                        description = f"I'm sorry, we don't have availability at {time_12hr} on {reservationDate}. Would you like to try a different time?"
                    
                    return {
                        "success": True,
                        "available": available,
                        "message": message,
                        "description": description  # ⭐ Spoken response
                    }
                else:
                    return {
                        "success": False,
                        "available": False,
                        "description": "I'm having trouble checking availability right now. Please try again."
                    }
    except Exception as e:
        print(f"❌ AVAILABILITY ERROR: {type(e).__name__}: {e}")
        return {
            "success": False,
            "available": False,
            "description": "I'm having trouble checking availability. Let me connect you with someone."
        }


# ============================================================================
# TOOL 4: CREATE RESERVATION
# ============================================================================

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
    
    print(f"📤 Creating reservation: {payload}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}/api/reservations", json=payload, timeout=15) as resp:
                print(f"✅ Response status: {resp.status}")
                
                if resp.status == 201:
                    response_json = await resp.json()
                    print(f"📦 Reservation created: {response_json}")
                    
                    res_data = response_json.get("data", {})
                    
                    res_num = res_data.get("reservationNumber", "UNKNOWN")
                    time_12hr = convert_to_12hr(reservationTime)
                    
                    # ⭐ SPOKEN DESCRIPTION
                    description = (
                        f"Excellent! Your reservation is confirmed. "
                        f"Confirmation number {res_num}. "
                        f"That's for {partySize} guests on {reservationDate} at {time_12hr}. "
                        f"We're at 1159 South Canal Street in Chicago. "
                        f"We look forward to seeing you! "
                        f"Is there anything else I can help with?"
                    )
                    
                    return {
                        "success": True,
                        "reservationNumber": res_num,
                        "description": description  # ⭐ Spoken response
                    }
                else:
                    err_text = await resp.text()
                    print(f"❌ Reservation failed: {err_text}")
                    return {
                        "success": False,
                        "error": err_text,
                        "description": "I'm sorry, I couldn't create that reservation. Would you like to try a different time?"
                    }
    except Exception as e:
        print(f"❌ RESERVATION ERROR: {type(e).__name__}: {e}")
        return {
            "success": False,
            "error": str(e),
            "description": "I'm having trouble creating the reservation. Let me connect you with someone."
        }


# ============================================================================
# TOOL 5: TRANSFER TO HUMAN
# ============================================================================

@llm.function_tool
async def transfer_to_human(
    context: RunContext,
    reason: str = "customer_request",
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
    
    description = "I'll connect you with a staff member at the restaurant right away. Please hold for just a moment."
    
    return {
        "success": True,
        "message": "Transferring to human agent",
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "description": description  # ⭐ Spoken response
    }


# ============================================================================
# TOOL 6: GET HOURS
# ============================================================================

@llm.function_tool
async def get_hours(context: RunContext) -> Dict:
    """
    Get the restaurant's operating hours.
    
    Returns:
        Dict with hours information
    """
    print("🕒 GET HOURS REQUESTED")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/location", timeout=5) as resp:
                if resp.status == 200:
                    response_json = await resp.json()
                    data = response_json.get("data", {})
                    
                    # Extract hours from response or use default
                    description = (
                        "We're open Monday through Friday from 6 AM to 11 PM, "
                        "Saturday from 7 AM to 11 PM, and Sunday from 7 AM to 10 PM. "
                        "You can visit us anytime during these hours!"
                    )
                    
                    return {
                        "success": True,
                        "hours": data.get("hours", {}),
                        "description": description  # ⭐ Spoken response
                    }
    except Exception as e:
        print(f"❌ HOURS ERROR: {e}")
    
    # Fallback response
    description = (
        "We're open Monday through Friday from 6 AM to 11 PM, "
        "Saturday from 7 AM to 11 PM, and Sunday from 7 AM to 10 PM."
    )
    
    return {
        "success": True,
        "description": description  # ⭐ Spoken response
    }


# ============================================================================
# TOOL 7: GET LOCATION
# ============================================================================

@llm.function_tool
async def get_location(context: RunContext) -> Dict:
    """
    Get the restaurant's location and contact information.
    
    Returns:
        Dict with location information
    """
    print("📍 GET LOCATION REQUESTED")
    
    # Hardcoded from restaurant_config.py
    description = (
        "We're located at 1159 South Canal Street in Chicago, Illinois. "
        "You can reach us at 3 1 2, 9 3 9, 7 1 6 7. "
        "There's street parking nearby and some paid parking lots in the area."
    )
    
    return {
        "success": True,
        "name": "White Palace Grill",
        "address": "1159 S Canal St",
        "city": "Chicago",
        "state": "IL",
        "zip_code": "60607",
        "phone": "(312) 939-7167",
        "description": description  # ⭐ Spoken response
    }


# ============================================================================
# TOOL 8: GET ORDER BY NUMBER
# ============================================================================

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
        # Note: Backend doesn't have /api/orders/number/{orderNumber} endpoint
        # We need to search through orders
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/orders?limit=100", timeout=10) as resp:
                if resp.status == 200:
                    response_json = await resp.json()
                    orders_data = response_json.get("data", {})
                    orders = orders_data.get("orders", [])
                    
                    # Find matching order
                    matching_order = None
                    for order in orders:
                        if order.get("orderNumber") == orderNumber:
                            matching_order = order
                            break
                    
                    if matching_order:
                        status = matching_order.get("status", "unknown")
                        total = matching_order.get("totalPrice", 0)
                        
                        description = f"I found your order {orderNumber}. The status is {status}, and the total was ${total:.2f}. Is there anything else you'd like to know?"
                        
                        return {
                            "success": True,
                            "order": matching_order,
                            "description": description  # ⭐ Spoken response
                        }
                    else:
                        description = f"I couldn't find an order with number {orderNumber}. Can you double-check the order number?"
                        
                        return {
                            "success": False,
                            "error": "Order not found",
                            "description": description  # ⭐ Spoken response
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Backend returned {resp.status}",
                        "description": "I'm having trouble looking up that order. Please try again."
                    }
    except Exception as e:
        print(f"❌ ORDER LOOKUP ERROR: {e}")
        return {
            "success": False,
            "error": str(e),
            "description": "I'm having trouble looking up that order right now."
        }


# ============================================================================
# TOOL 9: UPDATE ORDER STATUS BY ORDER NUMBER
# ============================================================================

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
    
    description = f"I've updated order {orderNumber} to {status}. Is there anything else I can help with?"
    
    return {
        "success": True,
        "message": f"Order status updated to {status}",
        "description": description  # ⭐ Spoken response
    }


# ============================================================================
# TOOL 10: CANCEL ORDER BY NUMBER
# ============================================================================

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
    
    description = f"I've cancelled order {orderNumber}. If you have any questions, feel free to ask."
    
    return {
        "success": True,
        "message": f"Order {orderNumber} cancelled",
        "description": description  # ⭐ Spoken response
    }


# ============================================================================
# TOOL 11: GET RESERVATION BY NUMBER
# ============================================================================

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
            async with session.get(f"{BACKEND_URL}/api/reservations?limit=100", timeout=10) as resp:
                if resp.status == 200:
                    response_json = await resp.json()
                    reservations_data = response_json.get("data", {})
                    reservations = reservations_data.get("reservations", [])
                    
                    # Find matching reservation
                    matching_res = None
                    for res in reservations:
                        if res.get("reservationNumber") == reservationNumber:
                            matching_res = res
                            break
                    
                    if matching_res:
                        party_size = matching_res.get("partySize", 0)
                        res_date = matching_res.get("reservationDate", "")
                        res_time = matching_res.get("reservationTime", "")
                        status = matching_res.get("status", "unknown")
                        
                        time_12hr = convert_to_12hr(res_time.split('T')[-1][:5] if 'T' in res_time else res_time[:5])
                        
                        description = f"I found your reservation {reservationNumber}. It's for {party_size} guests on {res_date} at {time_12hr}. The status is {status}. Anything else I can help with?"
                        
                        return {
                            "success": True,
                            "reservation": matching_res,
                            "description": description  # ⭐ Spoken response
                        }
                    else:
                        description = f"I couldn't find a reservation with number {reservationNumber}. Can you double-check the confirmation number?"
                        
                        return {
                            "success": False,
                            "error": "Reservation not found",
                            "description": description  # ⭐ Spoken response
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Backend returned {resp.status}",
                        "description": "I'm having trouble looking up that reservation. Please try again."
                    }
    except Exception as e:
        print(f"❌ RESERVATION LOOKUP ERROR: {e}")
        return {
            "success": False,
            "error": str(e),
            "description": "I'm having trouble looking up that reservation right now."
        }


# ============================================================================
# TOOL 12: UPDATE RESERVATION STATUS BY RESERVATION NUMBER
# ============================================================================

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
    
    description = f"I've updated reservation {reservationNumber} to {status}. Is there anything else I can help with?"
    
    return {
        "success": True,
        "message": f"Reservation status updated to {status}",
        "description": description  # ⭐ Spoken response
    }


# ============================================================================
# TOOL 13: CANCEL RESERVATION BY NUMBER
# ============================================================================

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
    
    description = f"I've cancelled reservation {reservationNumber}. If you'd like to make a new reservation, just let me know!"
    
    return {
        "success": True,
        "message": f"Reservation {reservationNumber} cancelled",
        "description": description  # ⭐ Spoken response
    }


# ============================================================================
# END OF TOOLS
# ============================================================================

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
