

"""
Agent API Routes
Handles AI agent conversation
"""

from flask import Blueprint, jsonify, request
from config.constants import HTTP_STATUS
from middleware.error_handler import handle_exceptions
from agent_llm import llm_agent  # Import LLM agent instead
import logging

logger = logging.getLogger(__name__)

agent_bp = Blueprint('agent', __name__)

@agent_bp.route('/message', methods=['POST'])
@handle_exceptions
def agent_message():
    """
    Handle agent conversation message.
    
    Expected JSON:
    {
      "text": "I want to order two burgers",
      "customerPhone": "+13125551234"
    }
    
    Returns:
    {
      "data": {
        "response": "Great! I have 2 burgers..."
      }
    }
    """
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    customer_phone = data.get("customerPhone")
    
    if not text:
        return jsonify({
            "error": "text is required",
            "message": "Please provide a text message"
        }), HTTP_STATUS["BAD_REQUEST"]
    
    logger.info(f"Agent message from {customer_phone}: {text}")
    
    # Call LLM agent
    result = llm_agent.handle_message(text, customer_phone)
    
    return jsonify({
        "data": {
            "response": result["response"],
            "intent": result.get("intent"),
            "metadata": result.get("toolResult")
        }
    }), HTTP_STATUS["OK"]
