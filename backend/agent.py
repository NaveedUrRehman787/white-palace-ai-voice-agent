

"""
Restaurant AI Agent

Responsibilities:
- Classify user intent: order, reservation, menu question, small talk, unknown.
- Maintain simple in-memory state per customer for multi-turn order flow.
- Call Flask APIs (/api/menu, /api/orders, /api/reservations) for real actions.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Any, List
import re
import logging
import requests

logger = logging.getLogger(__name__)



# helper function to fetch menu items
MENU_API_BASE = "http://localhost:5000/api/menu"

def _fetch_menu_items(limit: int = 200):
    resp = requests.get(f"{MENU_API_BASE}?limit={limit}")
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["items"]  # uses your existing format_menu_item


# helper function to find best menu match
def _find_best_menu_match(name: str, menu_items: list[dict]) -> dict | None:
    name = name.lower()
    # very simple: exact or substring match on lowercased item name
    candidates = []
    for item in menu_items:
        item_name = item["name"].lower()
        if name == item_name or name in item_name or item_name in name:
            candidates.append(item)
    return candidates[0] if candidates else None

# ============================================
# Intent types
# ============================================
# class IntentType(Enum):
#     ORDER = auto()
#     RESERVATION = auto()
#     MENU_QUESTION = auto()
#     HOURS = auto()
#     SMALL_TALK = auto()
#     UNKNOWN = auto()

class IntentType(Enum):
    ORDER = auto()
    RESERVATION = auto()
    MENU_QUESTION = auto()
    HOURS = auto()
    SMALL_TALK = auto()
    FAQ = auto()
    UNKNOWN = auto()



@dataclass
class Intent:
    type: IntentType
    confidence: float
    # Optional extracted info (to extend later)
    entities: Optional[Dict[str, Any]] = None


# @dataclass
# class SessionState:
#     """
#     Very simple in-memory session state per customer.
#     """
#     current_intent: Optional[IntentType] = None
#     order_items: List[Dict[str, Any]] = None
#     order_type: Optional[str] = None   # "pickup" or "delivery"
#     customer_name: Optional[str] = None
#     step: Optional[str] = None         # e.g., "ASK_ITEMS", "ASK_TYPE", "ASK_NAME"
#

# # In-memory sessions keyed by normalized phone number (or "anonymous")
# sessions: Dict[str, SessionState] = {}

@dataclass
class SessionState:
    current_intent: Optional[IntentType] = None
    order_items: List[Dict[str, Any]] = None
    order_type: Optional[str] = None
    customer_name: Optional[str] = None
    step: Optional[str] = None

    # Reservation-specific
    reservation_party_size: Optional[int] = None
    reservation_date: Optional[str] = None   # "YYYY-MM-DD"
    reservation_time: Optional[str] = None   # "HH:MM"

# In-memory sessions keyed by normalized phone number (or "anonymous")
sessions: Dict[str, SessionState] = {}

# ============================================
# Simple rule-based intent classifier
# ============================================
class IntentClassifier:
    """
    Very simple keyword-based classifier.
    Later you can replace this with an LLM or ML model.
    """

    def __init__(self):

        self.faq_keywords = [
            "where are you located",
            "address",
            "location",
            "parking",
            "do you have parking",
        ]

        self.date_keywords = ["today", "tomorrow"]
        self.time_regex = re.compile(r"\b(\d{1,2}:\d{2})\b")  # matches 7:30, 19:00
        self.order_type_keywords = ["pickup", "pick up", "delivery", "deliver", "to go"]

        # Lowercase keyword lists
        self.order_keywords = [
            "order", "pickup", "pick up", "takeout", "take out",
            "delivery", "place an order", "to go"
        ]
        self.reservation_keywords = [
            "reservation", "book a table", "book table", "reserve",
            "party of", "table for", "booking"
        ]
        self.menu_keywords = [
            "menu", "do you have", "what do you have",
            "specials", "special", "dish", "burger", "breakfast",
            "lunch", "dinner"
        ]
        self.hours_keywords = [
            "hours", "open", "close", "closing", "time do you",
            "when are you open", "when do you close"
        ]
        self.small_talk_keywords = [
            "hi", "hello", "hey", "how are you", "what's up",
            "thank you", "thanks"
        ]

    def _looks_like_date(self, t: str) -> bool:
        if any(k in t for k in self.date_keywords):
            return True
        # simple ISO date check: 2025-12-31
        return bool(re.search(r"\b\d{4}-\d{2}-\d{2}\b", t))

    def _looks_like_time(self, t: str) -> bool:
        # matches "7:30", "19:00", "07:30"
        if self.time_regex.search(t):
            return True
        # also treat simple "7pm", "7 pm" as time-like
        return bool(re.search(r"\b\d{1,2}\s*(am|pm)\b", t))

    def _looks_like_order_type(self, t: str) -> bool:
        return any(k in t for k in self.order_type_keywords)


    def classify(self, text: str) -> Intent:
        """Return Intent for a given text."""
        if not text or not text.strip():
            return Intent(type=IntentType.UNKNOWN, confidence=0.0, entities={})

        t = text.lower().strip()

        # Small talk first
        if any(k in t for k in self.small_talk_keywords):
            return Intent(type=IntentType.SMALL_TALK, confidence=0.8, entities={})
        
        # If text strongly looks like order type, bias toward ORDER
        if self._looks_like_order_type(t):
            return Intent(type=IntentType.ORDER, confidence=0.7, entities={})

        # If text strongly looks like a date or time, bias toward RESERVATION
        if self._looks_like_date(t) or self._looks_like_time(t):
            return Intent(type=IntentType.RESERVATION, confidence=0.7, entities={})


        # Order
        if any(k in t for k in self.order_keywords):
            # Simple entity extraction example: people mention "for 2" etc.
            party_match = re.search(r"\bfor (\d+)\b", t)
            entities = {}
            if party_match:
                entities["partySize"] = int(party_match.group(1))
            return Intent(type=IntentType.ORDER, confidence=0.85, entities=entities)

        # Reservation
        if any(k in t for k in self.reservation_keywords):
            entities = {}
            party_match = re.search(r"\bfor (\d+)\b", t)
            if party_match:
                entities["partySize"] = int(party_match.group(1))
            return Intent(type=IntentType.RESERVATION, confidence=0.9, entities=entities)

        # Menu question
        if any(k in t for k in self.menu_keywords):
            return Intent(type=IntentType.MENU_QUESTION, confidence=0.8, entities={})

        # Hours
        if any(k in t for k in self.hours_keywords):
            return Intent(type=IntentType.HOURS, confidence=0.85, entities={})
        
        # FAQ / location / parking
        if any(k in t for k in self.faq_keywords):
            return Intent(type=IntentType.FAQ, confidence=0.8, entities={})


        # Fallback
        return Intent(type=IntentType.UNKNOWN, confidence=0.3, entities={})


# ============================================
# Agent core
# ============================================
class RestaurantAgent:
    """
    Core agent that:
    - Classifies intent.
    - Routes to handler methods.
    - Maintains a simple per-customer session for multi-turn flows.
    """

    def __init__(self):
        self.classifier = IntentClassifier()



    def handle_message(self, text: str, customer_phone: Optional[str] = None) -> Dict[str, Any]:
        """
        Entry point: given user text, return response + metadata.

        Returns:
            {
              "intent": "order",
              "confidence": 0.9,
              "response": "text",
              "entities": {...},
              "session": {...}
            }
        """
        intent = self.classifier.classify(text)
        logger.info(
            f"Classified intent={intent.type.name}, "
            f"confidence={intent.confidence}, entities={intent.entities}"
        )

        # Fetch or create session
        session_key = customer_phone or "anonymous"
        if session_key not in sessions:
            sessions[session_key] = SessionState(order_items=[], step=None)
        session = sessions[session_key]

        # Check for cancel keywords
        cancel_keywords = ["never mind", "cancel", "stop", "i changed my mind"]
        if any(k in text.lower() for k in cancel_keywords):
            # Reset session
            session.current_intent = None
            session.step = None
            session.order_items = []
            session.order_type = None
            session.customer_name = None
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "response": "Okay, I've cancelled this. I can help you place an order or make a reservation if you'd like.",
                "entities": {},
                "session": {
                    "currentIntent": None,
                    "step": None,
                },
            }

        # If in the middle of an order, override intent to ORDER
        if session.current_intent == IntentType.ORDER:
            intent.type = IntentType.ORDER

        # If in the middle of a reservation, override intent to RESERVATION
        if session.current_intent == IntentType.RESERVATION:
            intent.type = IntentType.RESERVATION

        if intent.type == IntentType.ORDER:
            reply = self._handle_order_intent(text, intent.entities or {}, customer_phone, session)
        elif intent.type == IntentType.RESERVATION:
              reply = self._handle_reservation_intent(text, intent.entities or {}, customer_phone, session)
        elif intent.type == IntentType.MENU_QUESTION:
            reply = self._handle_menu_intent(text, intent.entities or {})
        elif intent.type == IntentType.HOURS:
            reply = self._handle_hours_intent()
        elif intent.type == IntentType.FAQ:
             reply = self._handle_faq_intent(text)
        elif intent.type == IntentType.SMALL_TALK:
            reply = self._handle_small_talk(text)
        else:
            reply = self._handle_unknown(text)

        # Save updated session
        sessions[session_key] = session

        return {
            "intent": intent.type.name.lower(),
            "confidence": intent.confidence,
            "response": reply,
            "entities": intent.entities or {},
            "session": {
                "currentIntent": session.current_intent.name if session.current_intent else None,
                "step": session.step,
            },
        }
    
    def _handle_faq_intent(self, text: str) -> str:
        t = text.lower()
        if "parking" in t:
            return (
                "White Palace Grill has street parking nearby and some paid lots in the area. "
                "Parking availability can vary depending on the time of day."
            )
        # Default to location/address
        return (
            "White Palace Grill is located at fourteen fifty five South Canal Street in Chicago. "
            "We are open twenty four hours a day, seven days a week."
        )


    # ----------------------------------------
    # Intent handlers
    # ----------------------------------------
    
    def _parse_items_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse '<number> <word>' patterns, then map each word to a real menu item
        using /api/menu so we get real menuItemId and price.
        """
        t = text.lower()
        tokens = t.split()
        raw_items: list[dict] = []

        i = 0
        while i < len(tokens) - 1:
            if tokens[i].isdigit():
                qty = int(tokens[i])
                name = tokens[i + 1]
                raw_items.append(
                    {
                        "name": name,
                        "quantity": qty,
                    }
                )
                i += 2
            else:
                i += 1

        if not raw_items and len(tokens) >= 1:
            raw_items.append(
                {
                    "name": " ".join(tokens),
                    "quantity": 1,
                }
            )

        # Fetch menu once per call
        menu_items = _fetch_menu_items()

        items: list[dict] = []
        for raw in raw_items:
            match = _find_best_menu_match(raw["name"], menu_items)
            if match:
                items.append(
                    {
                        "menuItemId": match["id"],
                        "name": match["name"],
                        "price": float(match["price"]),
                        "quantity": raw["quantity"],
                    }
                )
            else:
                # For now, keep unknowns as zero; later you can ask clarification
                items.append(
                    {
                        "menuItemId": 0,
                        "name": raw["name"],
                        "price": 0.0,
                        "quantity": raw["quantity"],
                    }
                )

        return items


    def _handle_order_intent(
        self,
        text: str,
        entities: Dict[str, Any],
        customer_phone: Optional[str],
        session: SessionState,
    ) -> str:
        """
        Multi-turn order flow with simple in-memory state.

        Steps:
        1. ASK_ITEMS -> ask user for items
        2. ASK_TYPE  -> ask pickup vs delivery
        3. ASK_NAME  -> ask for customer name
        4. CREATE_ORDER -> call /api/orders
        """
        # Initialize session intent
        if session.current_intent != IntentType.ORDER or not session.step:
            session.current_intent = IntentType.ORDER
            session.order_items = []
            session.order_type = None
            session.customer_name = None
            session.step = "ASK_ITEMS"
            return (
                "You would like to place an order. "
                "Please tell me what you would like to order. "
                "For example: two classic burgers and one fries."
            )

        # STEP 1: collect items
        if session.step == "ASK_ITEMS":
            items = self._parse_items_from_text(text)
            if not items:
                return (
                    "I did not catch any items. "
                    "Please say something like: one cheeseburger and one coffee."
                )

            # Basic sanity checks on items
            total_qty = sum(it.get("quantity", 0) for it in items)
            known_items = [it for it in items if it.get("menuItemId", 0) != 0]

            # If no recognized menu items
            if not known_items:
                return (
                    "I could not match those items to our menu. "
                    "Please try again and use names like classic burger, pancakes, or coffee."
                )

            # If the order is unusually large, confirm
            if total_qty > 20:
                summary = ", ".join(f"{it['quantity']} x {it['name']}" for it in items)
                return (
                    f"That sounds like a big order: {summary}. "
                    "Did you really want that many items?"
                )

            session.order_items.extend(items)
            session.step = "ASK_TYPE"


            summary = ", ".join(
                f"{it['quantity']} x {it['name']}" for it in session.order_items
            )
            return (
                f"Great, I have {summary}. "
                "Is this order for pickup or delivery?"
            )

        # STEP 2: ask pickup vs delivery
        if session.step == "ASK_TYPE":
            t = text.lower()
            if "pickup" in t or "pick up" in t or "to go" in t:
                session.order_type = "pickup"
            elif "delivery" in t or "deliver" in t:
                session.order_type = "delivery"
            else:
                return "Is this order for pickup or delivery?"

            session.step = "ASK_NAME"
            return "Got it. What name should I put on the order?"

        # STEP 3: ask for customer name
        if session.step == "ASK_NAME":
            name = text.strip()
            if len(name) == 0:
                return "Please tell me the name for the order."

            session.customer_name = name
            session.step = "CREATE_ORDER"

        # STEP 4: create order via API
        if session.step == "CREATE_ORDER":
            payload = {
                "items": session.order_items,
                "orderType": session.order_type or "pickup",
                "customerPhone": customer_phone or "",
                "customerName": session.customer_name or "Guest",
                "specialRequests": None,
            }

            try:
                resp = requests.post(
                    "http://localhost:5000/api/orders",
                    json=payload,
                    timeout=5,
                )
               
                if resp.status_code != 201:
                    logger.warning(f"/api/reservations returned {resp.status_code}: {resp.text}")

                    # Reset session
                    session.current_intent = None
                    session.step = None
                    session.reservation_party_size = None
                    session.reservation_date = None
                    session.reservation_time = None

                    if resp.status_code == 400:
                        return (
                            "The system could not accept that reservation, possibly due to time or availability. "
                            "Would you like to try a different time or date?"
                        )
                    elif resp.status_code >= 500:
                        return (
                            "I am having trouble creating reservations right now. "
                            "Please try again later or call the restaurant directly."
                        )
                    else:
                        return (
                            "I could not complete the reservation due to a technical issue. "
                            "Would you like to try again with a different time or date?"
                        )


                data = resp.json().get("data", {})
                order_number = data.get("orderNumber")
                total = data.get("totalPrice")
                order_type = data.get("orderType")
                items = data.get("orderItems") or []
                estimated_ready = data.get("estimatedReadyTime")

                # Build item summary
                item_phrases = []
                for item in items:
                    q = item.get("quantity", 1)
                    name = item.get("name", "")
                    if name:
                        item_phrases.append(f"{q} {name}")
                items_str = ", ".join(item_phrases) if item_phrases else "your items"

                # Format total nicely
                total_str = f"{total:.2f}" if total is not None else "0.00"

                # Build response text
                if estimated_ready:
                    response_text = (
                        f"Your {order_type} order has been placed successfully. "
                        f"You ordered {items_str}. "
                        f"Your order number is {order_number}. "
                        f"The total is {total_str} dollars. "
                        f"It should be ready around {estimated_ready}. "
                        "Thank you for ordering from White Palace Grill."
                    )
                else:
                    response_text = (
                        f"Your {order_type} order has been placed successfully. "
                        f"You ordered {items_str}. "
                        f"Your order number is {order_number}. "
                        f"The total is {total_str} dollars. "
                        "Thank you for ordering from White Palace Grill."
                    )

                # Reset session after success
                session.current_intent = None
                session.step = None
                session.order_items = []
                session.order_type = None
                session.customer_name = None

                return response_text


            except Exception as e:
                logger.error(f"Error calling /api/orders: {e}")
                session.current_intent = None
                session.step = None
                session.order_items = []
                session.order_type = None
                session.customer_name = None
                return (
                    "Something went wrong while placing your order. "
                    "Please try again later."
                )

        # Fallback
        return (
            "You are placing an order. "
            "Please tell me what you would like to order."
        )

   
    def _handle_reservation_intent(
        self,
        text: str,
        entities: Dict[str, Any],
        customer_phone: Optional[str],
        session: SessionState,
    ) -> str:
        """
        Multi-turn reservation flow:

        1. ASK_PARTY   -> ask for party size
        2. ASK_DATE    -> ask for reservation date
        3. ASK_TIME    -> ask for reservation time
        4. ASK_NAME    -> ask for customer name (if needed)
        5. CREATE_RES  -> call /api/reservations
        """

        # Initialize reservation flow if not already in it
        if session.current_intent != IntentType.RESERVATION or not session.step:
            session.current_intent = IntentType.RESERVATION
            session.reservation_party_size = entities.get("partySize")
            session.reservation_date = None
            session.reservation_time = None
            # Reuse customer_name from order if already known
            # or leave None and ask explicitly later
            if session.reservation_party_size:
                session.step = "ASK_DATE"
                return (
                    f"You want a reservation for {session.reservation_party_size} guests. "
                    "What date would you like? You can say something like, "
                    "today, tomorrow, or December 31st."
                )
            else:
                session.step = "ASK_PARTY"
                return (
                    "You want to make a reservation. "
                    "How many people is the reservation for?"
                )

        # STEP 1: party size
        # if session.step == "ASK_PARTY":
        #     # Check if text looks like time, if so, don't treat as party size
        #     if self.classifier._looks_like_time(text):
        #         return "I think you are telling me a time. First, how many people is the reservation for?"

        #     # Try to extract a number from text
        #     m = re.search(r"\b(\d+)\b", text)
        #     if not m:
        #         return (
        #             "I did not catch the party size. "
        #             "Please tell me how many people, for example: four people."
        #         )
        #     party_size = int(m.group(1))
        #     if party_size < 1 or party_size > 20:
        #         return (
        #             "We can book reservations between 1 and 20 guests. "
        #             "How many people is your reservation for?"
        #         )

        #     session.reservation_party_size = party_size
        #     session.step = "ASK_DATE"
        #     return (
        #         f"Great, a table for {party_size}. "
        #         "What date would you like? You can say something like, "
        #         "today, tomorrow, or December 31st."
        #     )
        # STEP 1: party size
        if session.step == "ASK_PARTY":
            # Check if text looks like time, if so, don't treat as party size
            if self.classifier._looks_like_time(text):
                return "I think you are telling me a time. First, how many people is the reservation for?"

            # Helper: convert word numbers to digits
            number_words = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
                'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
                'nineteen': 19, 'twenty': 20
            }
            
            t = text.lower().strip()
            party_size = None
            
            # Try word numbers first
            for word, num in number_words.items():
                if re.search(rf'\b{word}\b', t):
                    party_size = num
                    break
            
            # Try digit numbers
            if party_size is None:
                m = re.search(r'\b(\d+)\b', t)
                if m:
                    party_size = int(m.group(1))
            
            if party_size is None:
                return (
                    "I did not catch the party size. "
                    "Please tell me how many people, for example: four people."
                )
            
            if party_size < 1 or party_size > 20:
                return (
                    "We can book reservations between 1 and 20 guests. "
                    "How many people is your reservation for?"
                )

            session.reservation_party_size = party_size
            session.step = "ASK_DATE"
            return (
                f"Great, a table for {party_size}. "
                "What date would you like? You can say something like, "
                "today, tomorrow, or December 31st."
            )

        # STEP 2: date
        if session.step == "ASK_DATE":
            # For now, expect an ISO-like date or simple 'today' / 'tomorrow'
            t = text.lower().strip()

            from datetime import datetime, timedelta

            if "today" in t:
                res_date = datetime.now().date().isoformat()
            elif "tomorrow" in t:
                res_date = (datetime.now().date() + timedelta(days=1)).isoformat()
            else:
                # Very simple date parse: expect YYYY-MM-DD
                # You can improve later with NLP date parsing
                try:
                    datetime.fromisoformat(text.strip())
                    res_date = text.strip()
                except Exception:
                    return (
                        "Please give the date in a format like 2025-12-31, "
                        "or say today or tomorrow."
                    )

            session.reservation_date = res_date
            session.step = "ASK_TIME"
            return (
                f"Got it, {res_date}. "
                "What time would you like the reservation? "
                "Please say a time like 7:30 PM."
            )

        # # STEP 3: time
        # if session.step == "ASK_TIME":
        #     t = text.lower().strip()
        #     # Very naive time parsing: look for HH:MM 24-hour or '7:30 pm'
        #     time_match = re.search(r"\b(\d{1,2}):(\d{2})", t)
        #     if not time_match:
        #         return (
        #             "I did not catch the time. "
        #             "Please say a time like 7:30 PM."
        #         )

        #     hour = int(time_match.group(1))
        #     minute = int(time_match.group(2))

        #     # Simple AM/PM handling
        #     if "pm" in t and hour < 12:
        #         hour += 12
        #     if "am" in t and hour == 12:
        #         hour = 0

        #     if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        #         return (
        #             "That time does not look valid. "
        #             "Please say a time like 7:30 PM."
        #         )

        #     res_time = f"{hour:02d}:{minute:02d}"
        #     session.reservation_time = res_time

        #     # If we do not yet know the customer name, ask for it
        #     if not session.customer_name:
        #         session.step = "ASK_NAME"
        #         return (
        #             f"Okay, a reservation on {session.reservation_date} at {res_time} "
        #             f"for {session.reservation_party_size} guests. "
        #             "What name should I put on the reservation?"
        #         )
        #     else:
        #         session.step = "CREATE_RES"
        # STEP 3: time
        if session.step == "ASK_TIME":
            t = text.lower().strip()
            
            # Word-to-number mapping
            time_words = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                'eleven': 11, 'twelve': 12,
                'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16,
                'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
                'thirty': 30, 'forty': 40, 'fifty': 50
            }
            
            hour = None
            minute = 0
            is_pm = 'pm' in t or 'p.' in t or 'p ' in t
            is_am = 'am' in t or 'a.' in t or 'a ' in t
            
            # Try pattern 1: digit format "7:30" or "19:30"
            time_match = re.search(r'\b(\d{1,2}):(\d{2})\b', t)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            
            # Try pattern 2: digit without colon "8 pm", "8pm", "8"
            elif re.search(r'\b(\d{1,2})\s*(pm|am|p|a)?\b', t):
                digit_match = re.search(r'\b(\d{1,2})\b', t)
                if digit_match:
                    hour = int(digit_match.group(1))
                    minute = 0
            
            # Try pattern 3: word format "eight thirty pm", "seven pm"
            else:
                # Look for hour word
                for word, num in time_words.items():
                    if num <= 12 and re.search(rf'\b{word}\b', t):
                        hour = num
                        break
                
                # Look for minute word (like "thirty" in "seven thirty")
                if hour is not None:
                    for word, num in time_words.items():
                        if num >= 30 and re.search(rf'\b{word}\b', t):
                            minute = num
                            break
            
            if hour is None:
                return (
                    "I did not catch the time. "
                    "Please say a time like 7:30 PM, eight PM, or seven thirty."
                )
            
            # Apply AM/PM conversion
            if is_pm and hour < 12:
                hour += 12
            if is_am and hour == 12:
                hour = 0
            
            # Validate
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                return (
                    "That time does not look valid. "
                    "Please say a time like 7:30 PM or eight PM."
                )
            
            res_time = f"{hour:02d}:{minute:02d}"
            session.reservation_time = res_time
            
            # If we do not yet know the customer name, ask for it
            if not session.customer_name:
                session.step = "ASK_NAME"
                return (
                    f"Okay, a reservation on {session.reservation_date} at {res_time} "
                    f"for {session.reservation_party_size} guests. "
                    "What name should I put on the reservation?"
                )
            else:
                session.step = "CREATE_RES"

        # STEP 4: name
        if session.step == "ASK_NAME":
            name = text.strip()
            if not name:
                return "Please tell me the name for the reservation."
            session.customer_name = name
            session.step = "CREATE_RES"

        # STEP 5: create reservation via API
        if session.step == "CREATE_RES":
            payload = {
                "reservationDate": session.reservation_date,
                "reservationTime": session.reservation_time,
                "partySize": session.reservation_party_size,
                "customerName": session.customer_name or "Guest",
                "customerPhone": customer_phone or "",
                "customerEmail": None,
                "specialRequests": None,
            }

            try:
                resp = requests.post(
                    "http://localhost:5000/api/reservations",
                    json=payload,
                    timeout=5,
                )

                if resp.status_code != 201:
                    logger.warning(f"/api/reservations returned {resp.status_code}: {resp.text}")

                    # Reset session
                    session.current_intent = None
                    session.step = None
                    session.reservation_party_size = None
                    session.reservation_date = None
                    session.reservation_time = None

                    if resp.status_code == 400:
                        return (
                            "The system could not accept that reservation, possibly due to time or availability. "
                            "Please try a different time or date."
                        )
                    elif resp.status_code >= 500:
                        return (
                            "I am having trouble creating reservations right now. "
                            "Please try again later or call the restaurant directly."
                        )
                    else:
                        return (
                            "I could not complete the reservation due to a technical issue. "
                            "Please try again later."
                        )

                data = resp.json().get("data", {})
                res_number = data.get("reservationNumber")
                res_date = data.get("reservationDate")
                res_time = data.get("reservationTime")
                party_size = data.get("partySize")

                # Reset session after success
                session.current_intent = None
                session.step = None
                session.reservation_party_size = None
                session.reservation_date = None
                session.reservation_time = None

                return (
                    f"Your reservation has been created. "
                    f"Your confirmation number is {res_number}. "
                    f"That is a table for {party_size} on {res_date} at {res_time}. "
                    "We look forward to seeing you at White Palace Grill."
                )

            except Exception as e:
                logger.error(f"Error calling /api/reservations: {e}")
                session.current_intent = None
                session.step = None
                session.reservation_party_size = None
                session.reservation_date = None
                session.reservation_time = None
                return (
                    "Something went wrong while creating your reservation. "
                    "Please try again later or call the restaurant directly."
                )

        # Fallback
        return (
            "You want to make a reservation. "
            "How many people is the reservation for?"
        )


    def _handle_menu_intent(self, text: str, entities: Dict[str, Any]) -> str:
        """
        Handle menu questions.

        Calls the /api/menu/categories endpoint to give real categories.
        """
        try:
            resp = requests.get("http://localhost:5000/api/menu/categories", timeout=3)
            if resp.status_code != 200:
                logger.warning(f"/api/menu/categories returned {resp.status_code}")
                return (
                    "I can help with the menu. "
                    "We have breakfast, burgers, sandwiches, entrees, salads, soups, sides, desserts, and beverages."
                )

            data = resp.json()
            categories = list(data.get("categories", {}).keys())
            if not categories:
                return (
                    "I can help with the menu, but I could not load the categories right now."
                )

            # Build a natural list
            if len(categories) > 1:
                nice = ", ".join(categories[:-1]) + f", and {categories[-1]}"
            else:
                nice = categories[0]

            return (
                f"Our menu has {nice}. "
                "Which category are you interested in?"
            )

        except Exception as e:
            logger.error(f"Error calling /api/menu/categories: {e}")
            return (
                "I can help with the menu. "
                "We have breakfast, burgers, sandwiches, entrees, salads, soups, sides, desserts, and beverages."
            )

    def _handle_hours_intent(self) -> str:
        """
        Handle hours/location (still static for now).
        """
        return (
            "White Palace Grill is open twenty four hours a day, seven days a week, "
            "at fourteen fifty five South Canal Street in Chicago."
        )

    def _handle_small_talk(self, text: str) -> str:
        return (
            "Hello from White Palace Grill. "
            "I can help you place an order, make a reservation, or answer questions about the menu."
        )

    def _handle_unknown(self, text: str) -> str:
        return (
            "Sorry, I’m not sure what you meant. "
            "You can ask to place an order, make a reservation, or ask about the menu."
        )


# ============================================
# Simple CLI test (optional)
# ============================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = RestaurantAgent()

    print("White Palace Agent test. Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit"]:
            break
        result = agent.handle_message(user_input, customer_phone="13125559999")
        print(f"Agent ({result['intent']}): {result['response']}")
        print(f"Session: {result['session']}\n")
