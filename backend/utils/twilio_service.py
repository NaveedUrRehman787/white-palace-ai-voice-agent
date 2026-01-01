"""
Twilio integration service for SMS and voice
"""

import os
import logging
from twilio.rest import Client
from config.restaurant_config import RESTAURANT_CONFIG
from config.constants import TWILIO_MESSAGES

logger = logging.getLogger(__name__)

class TwilioService:
    """Twilio service for SMS and voice communications"""
    
    def __init__(self):
        """Initialize Twilio client"""
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, self.phone_number]):
            logger.error('❌ Twilio credentials not configured')
            self.client = None
        else:
            self.client = Client(account_sid, auth_token)
            logger.info('✅ Twilio service initialized')
    
    def send_sms(self, to_number, message):
        """
        Send SMS message
        
        Args:
            to_number: Recipient phone number
            message: Message text
        
        Returns:
            Message SID or None if failed
        """
        if not self.client:
            logger.error('Twilio client not initialized')
            return None
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )
            logger.info(f'✅ SMS sent to {to_number}: {message_obj.sid}')
            return message_obj.sid
        except Exception as e:
            logger.error(f'❌ Failed to send SMS: {str(e)}')
            return None
    
    def send_order_confirmation(self, phone_number, order_id, ready_time):
        """
        Send order confirmation SMS
        
        Args:
            phone_number: Customer phone number
            order_id: Order ID
            ready_time: Estimated ready time
        
        Returns:
            Message SID or None
        """
        message = TWILIO_MESSAGES['ORDER_CONFIRMATION'].format(
            order_id=order_id,
            ready_time=ready_time.strftime('%I:%M %p')
        )
        return self.send_sms(phone_number, message)
    
    def send_reservation_confirmation(self, phone_number, res_id, party_size, date, time):
        """
        Send reservation confirmation SMS
        
        Args:
            phone_number: Customer phone number
            res_id: Reservation ID
            party_size: Party size
            date: Reservation date
            time: Reservation time
        
        Returns:
            Message SID or None
        """
        message = TWILIO_MESSAGES['RESERVATION_CONFIRMATION'].format(
            party_size=party_size,
            time=time,
            date=date,
            res_id=res_id
        )
        return self.send_sms(phone_number, message)
    
    def initiate_outbound_call(self, to_number, url):
        """
        Initiate outbound call with TwiML URL
        
        Args:
            to_number: Recipient phone number
            url: TwiML callback URL
        
        Returns:
            Call SID or None
        """
        if not self.client:
            logger.error('Twilio client not initialized')
            return None
        
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=url
            )
            logger.info(f'✅ Call initiated to {to_number}: {call.sid}')
            return call.sid
        except Exception as e:
            logger.error(f'❌ Failed to initiate call: {str(e)}')
            return None

# Create singleton instance
twilio_service = TwilioService()

