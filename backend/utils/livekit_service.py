"""
LiveKit integration service for voice and video
"""

import os
import logging
from datetime import datetime, timedelta
from livekit import api

from config.restaurant_config import RESTAURANT_CONFIG

logger = logging.getLogger(__name__)

class LiveKitService:
    """LiveKit service for WebRTC voice/video"""
    
    def __init__(self):
        """Initialize LiveKit service"""
        self.api_key = os.getenv('LIVEKIT_API_KEY')
        self.api_secret = os.getenv('LIVEKIT_API_SECRET')
        self.livekit_url = os.getenv('LIVEKIT_URL', 'ws://localhost:7880')
        
        if not all([self.api_key, self.api_secret]):
            logger.error('❌ LiveKit credentials not configured')
        else:
            logger.info('✅ LiveKit service initialized')
    
    def create_access_token(self, room_name, participant_name, can_publish=True, can_subscribe=True):
        """
        Create LiveKit access token
        
        Args:
            room_name: Name of the room
            participant_name: Participant name (identity)
            can_publish: Allow publishing
            can_subscribe: Allow subscribing
        
        Returns:
            Access token string or None
        """
        try:
            if not self.api_key or not self.api_secret:
                logger.error("❌ LiveKit API key/secret not set; cannot create token")
                return None

            # Build grants for this participant
            grants = api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=can_publish,
                can_subscribe=can_subscribe,
                can_publish_data=True,
            )

            # Create access token with 1 hour TTL
            token = (
                api.AccessToken(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                )
                .with_grants(grants=grants)
                .with_identity(identity=participant_name)
                .with_name(name=participant_name)
                .with_ttl(ttl=timedelta(hours=1))
            )

            token_str = token.to_jwt()
            logger.info(f"✅ Access token created for {participant_name} in room {room_name}")
            return token_str
        except Exception as e:
            logger.error(f"❌ Failed to create access token: {str(e)}")
            return None
    
    def create_voice_room(self, customer_phone):
        """
        Create LiveKit room for voice conversation
        
        Args:
            customer_phone: Customer phone number
        
        Returns:
            Dict with room info or None
        """
        try:
            room_name = f"{RESTAURANT_CONFIG['livekit']['room_prefix']}{customer_phone.replace(' ', '')}"
            
            # Create token for customer
            customer_token = self.create_access_token(
                room_name=room_name,
                participant_name=f"customer_{customer_phone}",
                can_publish=True,
                can_subscribe=True
            )
            
            # Create token for White Palace staff
            staff_token = self.create_access_token(
                room_name=room_name,
                participant_name="white_palace_staff",
                can_publish=True,
                can_subscribe=True
            )
            
            if not customer_token or not staff_token:
                return None
            
            return {
                'room_name': room_name,
                'livekit_url': self.livekit_url,
                'customer_token': customer_token,
                'staff_token': staff_token,
                'created_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f'❌ Failed to create voice room: {str(e)}')
            return None

# Create singleton instance
livekit_service = LiveKitService()


