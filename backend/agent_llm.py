"""
White Palace Grill - LLM-Based AI Agent

Uses OpenAI GPT-4 with function calling to handle orders and reservations.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import OpenAI

from config.database import execute_query
from config.constants import HTTP_STATUS
from config.restaurant_config import RESTAURANT_CONFIG
from utils.helpers import clean_phone_number
from prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory conversation history per session
conversation_history: Dict[str, List[Dict[str, str]]] = {}


# ============================================================================
# TOOLS: LLM Function Definitions
# ============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_menu_items",
            "description": "Get menu items by category or search term. Returns real menu items with prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category filter (breakfast, burgers, sandwiches, entrees, salads, soups, sides, desserts, beverages)",
                        "enum": ["breakfast", "burgers", "sandwiches", "entrees", "salads", "soups", "sides", "desserts", "beverages"]
                    },
                    "search": {
                        "type": "string",
                        "description": "Search term to find specific items"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Create a food order. Only call this when you have collected: items (with menuItemId, name, price, quantity), orderType, and customerName.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of order items",
                        "items": {
                            "type": "object",
                            "properties": {
                                "menuItemId": {"type": "integer"},
                                "name": {"type": "string"},
                                "price": {"type": "number"},
                                "quantity": {"type": "integer"}
                            },
                            "required": ["menuItemId", "name", "price", "quantity"]
                        }
                    },
                    "orderType": {
                        "type": "string",
                        "enum": ["pickup", "delivery", "dine-in"],
                        "description": "Type of order"
                    },
                    "customerName": {
                        "type": "string",
                        "description": "Customer name for the order"
                    },
                    "customerPhone": {
                        "type": "string",
                        "description": "Customer phone number"
                    },
                    "deliveryAddress": {
                        "type": "string",
                        "description": "Delivery address (required if orderType is delivery)"
                    },
                    "specialRequests": {
                        "type": "string",
                        "description": "Special requests or notes"
                    }
                },
                "required": ["items", "orderType", "customerName", "customerPhone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reservation",
            "description": "Create a table reservation. Only call this when you have: partySize, reservationDate (YYYY-MM-DD), reservationTime (HH:MM in 24-hour format), and customerName.",
            "parameters": {
                "type": "object",
                "properties": {
                    "partySize": {
                        "type": "integer",
                        "description": "Number of guests (1-20)"
                    },
                    "reservationDate": {
                        "type": "string",
                        "description": "Reservation date in YYYY-MM-DD format"
                    },
                    "reservationTime": {
                        "type": "string",
                        "description": "Reservation time in HH:MM 24-hour format (e.g., '19:30' for 7:30 PM)"
                    },
                    "customerName": {
                        "type": "string",
                        "description": "Customer name"
                    },
                    "customerPhone": {
                        "type": "string",
                        "description": "Customer phone number"
                    },
                    "customerEmail": {
                        "type": "string",
                        "description": "Customer email (optional)"
                    },
                    "specialRequests": {
                        "type": "string",
                        "description": "Special requests or notes"
                    }
                },
                "required": ["partySize", "reservationDate", "reservationTime", "customerName", "customerPhone"]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "check_reservation_availability",
        "description": "Check if a reservation time slot is available before booking. Always call this before creating a reservation.",
        "parameters": {
            "type": "object",
            "properties": {
                "reservationDate": {
                    "type": "string",
                    "description": "Reservation date in YYYY-MM-DD format"
                },
                "reservationTime": {
                    "type": "string",
                    "description": "Reservation time in HH:MM 24-hour format"
                },
                "partySize": {
                    "type": "integer",
                    "description": "Number of guests"
                }
            },
            "required": ["reservationDate", "reservationTime", "partySize"]
            }
        }
    },
]


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def tool_get_menu_items(category: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
    """Fetch menu items from database."""
    try:
        sql = """
            SELECT id, name, description, price, category, available
            FROM menu_items
            WHERE available = TRUE
        """
        params = []
        
        if category:
            sql += " AND category = %s"
            params.append(category)
        
        if search:
            sql += " AND (name ILIKE %s OR description ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        sql += " ORDER BY category, name LIMIT 50"
        
        rows = execute_query(sql, tuple(params) if params else None, fetch_all=True)
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "price": float(row[3]),
                "category": row[4]
            })
        
        return {
            "success": True,
            "items": items,
            "count": len(items)
        }
    
    except Exception as e:
        logger.error(f"Error fetching menu items: {e}")
        return {"success": False, "error": str(e), "items": []}



def tool_create_order(
    items: List[Dict],
    orderType: str,
    customerName: str,
    customerPhone: str,
    alternatePhone: Optional[str] = None,  # ← Add this
    deliveryAddress: Optional[str] = None,
    specialRequests: Optional[str] = None
) -> Dict[str, Any]:
    """Create order by calling internal /api/orders logic."""
    import requests
    
    # Use alternate phone if provided, otherwise use caller's phone
    contact_phone = alternatePhone if alternatePhone else customerPhone
    
    payload = {
        "items": items,
        "orderType": orderType,
        "customerPhone": contact_phone,  # ← Use contact_phone
        "customerName": customerName,
        "deliveryAddress": deliveryAddress,
        "specialRequests": specialRequests
    }
    try:
        # Call internal Flask endpoint
        resp = requests.post(
            "http://localhost:5000/api/orders",
            json=payload,
            timeout=10
        )
        
        if resp.status_code == 201:
            data = resp.json().get("data", {})
            return {
                "success": True,
                "orderNumber": data.get("orderNumber"),
                "totalPrice": data.get("totalPrice"),
                "estimatedReadyTime": data.get("estimatedReadyTime"),
                "orderType": data.get("orderType"),
                "orderItems": data.get("orderItems")
            }
        else:
            return {
                "success": False,
                "error": resp.json().get("message", "Failed to create order")
            }
    
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return {"success": False, "error": str(e)}

def tool_create_reservation(
    partySize: int,
    reservationDate: str,
    reservationTime: str,
    customerName: str,
    customerPhone: str,
    alternatePhone: Optional[str] = None,  # ← Add this
    customerEmail: Optional[str] = None,
    specialRequests: Optional[str] = None
) -> Dict[str, Any]:
    """Create reservation by calling internal /api/reservations logic."""
    import requests
    
    contact_phone = alternatePhone if alternatePhone else customerPhone


    payload = {
        "partySize": partySize,
        "reservationDate": reservationDate,
        "reservationTime": reservationTime,
        "customerPhone": contact_phone,
        "customerName": customerName,
        "customerEmail": customerEmail,
        "specialRequests": specialRequests
    }
    
    try:
        resp = requests.post(
            "http://localhost:5000/api/reservations",
            json=payload,
            timeout=10
        )
        
        if resp.status_code == 201:
            data = resp.json().get("data", {})
            return {
                "success": True,
                "reservationNumber": data.get("reservationNumber"),
                "partySize": data.get("partySize"),
                "reservationDate": data.get("reservationDate"),
                "reservationTime": data.get("reservationTime")
            }
        else:
            return {
                "success": False,
                "error": resp.json().get("message", "Failed to create reservation")
            }
    
    except Exception as e:
        logger.error(f"Error creating reservation: {e}")
        return {"success": False, "error": str(e)}

def tool_check_reservation_availability(
    reservationDate: str,
    reservationTime: str,
    partySize: int
) -> Dict[str, Any]:
    """Check if a reservation slot is available."""
    from config.database import execute_query
    from config.constants import RESERVATION_STATUS
    from config.restaurant_config import RESTAURANT_CONFIG
    from utils.helpers import is_time_slot_available
    from datetime import datetime
    
    try:
        # Validate the requested time is in the future
        requested_dt = datetime.fromisoformat(f"{reservationDate}T{reservationTime}")
        now = datetime.now()
        
        if requested_dt <= now:
            return {
                "success": False,
                "available": False,
                "message": "That time has already passed. Please choose a future date and time."
            }
        
        # Fetch existing reservations for that date
        sql = """
            SELECT reservation_time, party_size
            FROM reservations
            WHERE restaurant_id = %s
            AND reservation_date = %s
            AND status IN (%s, %s, %s)
        """
        params = (
            RESTAURANT_CONFIG["id"],
            reservationDate,
            RESERVATION_STATUS["PENDING"],
            RESERVATION_STATUS["CONFIRMED"],
            RESERVATION_STATUS["COMPLETED"]
        )
        
        existing = execute_query(sql, params, fetch_all=True)
        
        # Check capacity (simple version: max 10 concurrent reservations per time slot)
        max_concurrent = 10
        
        # Count reservations within 90 minutes of requested time
        conflict_count = 0
        for row in existing:
            existing_time_str = row[0].strftime("%H:%M") if hasattr(row[0], 'strftime') else str(row[0])
            existing_dt = datetime.fromisoformat(f"{reservationDate}T{existing_time_str}")
            
            # Check if within 90 minutes
            time_diff_minutes = abs((requested_dt - existing_dt).total_seconds() / 60)
            if time_diff_minutes < 90:
                conflict_count += 1
        
        if conflict_count >= max_concurrent:
            return {
                "success": True,
                "available": False,
                "message": f"Sorry, we're fully booked around {reservationTime}. Could you try a different time, perhaps 30 minutes earlier or later?"
            }
        
        return {
            "success": True,
            "available": True,
            "message": f"Great! We have availability for {partySize} guests on {reservationDate} at {reservationTime}."
        }
    
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        return {
            "success": False,
            "available": False,
            "message": "I'm having trouble checking availability right now. Let me try to make the reservation anyway."
        }

# ============================================================================
# MAIN AGENT CLASS
# ============================================================================
## helper functions
# In the handle_message method, add this helper function at the top of the file:

def format_phone_display(phone: str) -> str:
    """Format phone for voice-friendly display."""
    import re
    cleaned = re.sub(r'[^\d]', '', phone)
    if len(cleaned) == 10:
        return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
    elif len(cleaned) == 11 and cleaned[0] == '1':
        return f"{cleaned[1:4]}-{cleaned[4:7]}-{cleaned[7:]}"
    return phone


class LLMAgent:
    """LLM-powered restaurant agent using OpenAI function calling."""
    
    def __init__(self):
        self.model = "gpt-4o-mini"
        self.temperature = 0.3
    
    def handle_message(self, text: str, customer_phone: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle incoming message with LLM.
        
        Returns:
            {
              "response": "Agent text response",
              "intent": "order|reservation|faq",
              "data": {...}  # optional structured data
            }
        """
        session_key = customer_phone or "anonymous"
        
        # Get or create conversation history
        if session_key not in conversation_history:
            conversation_history[session_key] = []
        
        history = conversation_history[session_key]
        
        # # # Build system prompt with dynamic variables
        current_time = datetime.now().strftime("%B %d, %Y %I:%M %p")
        system_prompt = SYSTEM_PROMPT.replace("{{current_datetime}}", current_time)
        phone_display = format_phone_display(session_key)
        system_prompt = system_prompt.replace("{{session_id}}", phone_display)
        system_prompt = system_prompt.replace("{{restaurant_name}}", RESTAURANT_CONFIG["name"])
        system_prompt = system_prompt.replace("{{restaurant_address}}", RESTAURANT_CONFIG["address"])

        # Convert hours dict to string or use a simple message
        hours_text = "Open 24 hours, 7 days a week"  # White Palace Grill is 24/7
        system_prompt = system_prompt.replace("{{restaurant_hours}}", hours_text)

        # Replace other placeholders with empty or default values if not used
        system_prompt = system_prompt.replace("{{restaurant_timezone}}", RESTAURANT_CONFIG.get("timezone", "America/Chicago"))
        system_prompt = system_prompt.replace("{{conversation_history}}", "")
        system_prompt = system_prompt.replace("{{current_intent}}", "")
        system_prompt = system_prompt.replace("{{current_step}}", "")

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": text}
        ]
        
        try:
            # Call OpenAI
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                temperature=self.temperature,
                max_tokens=80
            )
            
            message = response.choices[0].message
            
            # Save user message to history
            history.append({"role": "user", "content": text})
            
            # If LLM wants to call a tool
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                logger.info(f"LLM calling tool: {function_name} with args: {arguments}")
                
                # Execute tool
                if function_name == "get_menu_items":
                    tool_result = tool_get_menu_items(**arguments)
                elif function_name == "create_order":
                    arguments["customerPhone"] = customer_phone or ""
                    tool_result = tool_create_order(**arguments)
                elif function_name == "create_reservation":
                    arguments["customerPhone"] = customer_phone or ""
                    tool_result = tool_create_reservation(**arguments)
                elif function_name == "check_reservation_availability":
                    tool_result = tool_check_reservation_availability(**arguments)
                else:
                    tool_result = {"error": "Unknown tool"}
                
                # Add tool call and result to history
                history.append(message.model_dump())
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(tool_result)
                })
                
                # Call LLM again to generate final response
                final_response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *history
                    ],
                    temperature=self.temperature,
                    max_tokens=500
                )
                
                final_message = final_response.choices[0].message.content
                history.append({"role": "assistant", "content": final_message})
                
                # Keep history manageable (last 20 messages)
                if len(history) > 20:
                    history = history[-20:]
                conversation_history[session_key] = history
                
                return {
                    "response": final_message,
                    "intent": function_name.replace("create_", "").replace("get_", ""),
                    "toolResult": tool_result
                }
            
            # If LLM just responds with text
            else:
                assistant_reply = message.content
                history.append({"role": "assistant", "content": assistant_reply})
                
                if len(history) > 20:
                    history = history[-20:]
                conversation_history[session_key] = history
                
                return {
                    "response": assistant_reply,
                    "intent": "conversation"
                }
        
        except Exception as e:
            logger.error(f"LLM agent error: {e}")
            return {
                "response": "I'm having trouble right now. Please try again or call the restaurant directly.",
                "intent": "error",
                "error": str(e)
            }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

llm_agent = LLMAgent()
