"""
Voice Pipeline using LiveKit Agents

Implements voice AI using LiveKit Agents framework:
- STT: Deepgram nova-2-phonecall
- LLM: OpenAI GPT-4o-mini
- TTS: OpenAI alloy voice
- VAD: Silero with optimized parameters
- Interruptions: enabled

Integrates with existing RestaurantAgent for business logic.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any

from livekit import agents, rtc
from livekit.agents import stt, llm, tts, vad
from livekit.agents.voice import AgentSession
from agent import RestaurantAgent
from utils.helpers import clean_phone_number

logger = logging.getLogger(__name__)

class RestaurantVoiceAgent(agents.Agent):
    """LiveKit Agent for Restaurant Voice Conversations"""

    def __init__(self):
        super().__init__()
        self.restaurant_agent = RestaurantAgent()
        self.customer_phone: Optional[str] = None

    async def on_enter(self):
        """Called when agent starts"""
        logger.info(f"🤖 Restaurant Voice Agent started for {self.customer_phone}")
        await self.say("Hello! Welcome to White Palace Grill. How can I help you today?", allow_interruptions=True)

    async def on_speech_recognized(self, event: stt.SpeechEvent):
        """Handle speech recognition results"""
        if event.text:
            logger.info(f"🎤 Recognized: '{event.text}'")

            # Process through restaurant agent
            try:
                customer_phone = self.customer_phone or "anonymous"
                response = self.restaurant_agent.handle_message(event.text, customer_phone)
                agent_response = response.get('response', '')

                if agent_response:
                    logger.info(f"🗣️ Agent response: '{agent_response}'")
                    await self.say(agent_response, allow_interruptions=True)
                else:
                    await self.say("I'm sorry, I didn't understand that. Could you please repeat?", allow_interruptions=True)

            except Exception as e:
                logger.error(f"Error processing agent response: {e}")
                await self.say("I'm having trouble right now. Please try again later.", allow_interruptions=True)

    async def on_interrupt(self, interrupted_text: str):
        """Handle interruptions"""
        logger.info(f"⏸️ Interrupted: '{interrupted_text}'")

    def set_customer_phone(self, phone: str):
        """Set customer phone for session tracking"""
        self.customer_phone = clean_phone_number(phone) or "anonymous"
        logger.info(f"📞 Set customer phone: {self.customer_phone}")

# Global agent session
agent_session: Optional[AgentSession] = None

def create_agent_session(customer_phone: str = "anonymous") -> AgentSession:
    """Create LiveKit Agent session with restaurant agent"""

    global agent_session

    # Create the agent
    restaurant_agent = RestaurantVoiceAgent()
    restaurant_agent.set_customer_phone(customer_phone)

    # Create session with specified components
    session = AgentSession(
        agent=restaurant_agent,
        stt=stt.Deepgram(
            model="nova-2-phonecall",
            language="en-US",
            interim_results=True,
        ),
        llm=llm.OpenAI(
            model="gpt-4o-mini",
            temperature=0.4,  # Lower temperature for consistent rule enforcement
        ),
        tts=tts.OpenAI(
            voice="alloy",
            speed=1.0,
        ),
        vad=vad.Silero.load(
            min_speech_duration=0.3,
            min_silence_duration=0.8,
            padding_duration=0.2,
            activation_threshold=0.5,
        ),
        allow_interruptions=True,
    )

    agent_session = session
    logger.info("✅ Agent session created with LiveKit Agents framework")
    return session

def get_agent_session() -> Optional[AgentSession]:
    """Get current agent session"""
    return agent_session

# async def start_voice_session(room_name: str, customer_phone: str = "anonymous") -> Optional[AgentSession]:
#     """Start voice session in LiveKit room"""
#     try:
#         session = create_agent_session(customer_phone)

#         # Connect to LiveKit room
#         await session.connect(room_name)
#         logger.info(f"🔗 Connected to LiveKit room: {room_name}")

#         return session

#     except Exception as e:
#         logger.error(f"❌ Failed to start voice session: {e}")
#         return None

# async def stop_voice_session():
#     """Stop current voice session"""
#     global agent_session
#     if agent_session:
#         try:
#             await agent_session.disconnect()
#             logger.info("🔌 Voice session stopped")
#         except Exception as e:
#             logger.error(f"Error stopping voice session: {e}")
#         finally:
#             agent_session = None

# Initialize logging

async def start_voice_session(room_name: str, customer_phone: str = "anonymous"):
    """Start White Palace AI agent in LiveKit room"""
    try:
        # Import from parent directory
        import sys
        import os
        # sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # from agent_white_palace import entrypoint as start_white_palace_agent
        from agent_white_palace_local import entrypoint as start_white_palace_agent
        # Create a mock job context for the agent
        class MockJobContext:
            def __init__(self, room_name, customer_phone):
                self.room_name = room_name
                self.customer_phone = customer_phone

            async def connect(self):
                pass  # Already connected via LiveKit

            @property
            def room(self):
                return MockRoom(room_name)

        class MockRoom:
            def __init__(self, name):
                self.name = name

        # Start the agent with the mock context
        ctx = MockJobContext(room_name, customer_phone)
        await start_white_palace_agent(ctx)

        logger.info(f"🔗 White Palace agent connected to room: {room_name}")
        return ctx  # Return context as session

    except Exception as e:
        logger.error(f"❌ Failed to start voice session: {e}")
        return None
async def stop_voice_session():
    """Stop current voice session"""
    global agent_session
    if agent_session:
        try:
            await agent_session.disconnect()
            logger.info("🔌 Voice session stopped")
        except Exception as e:
            logger.error(f"Error stopping voice session: {e}")
        finally:
            agent_session = None
logging.basicConfig(level=logging.INFO)

logger.info("🎙️ Restaurant Voice Pipeline initialized with LiveKit Agents")
