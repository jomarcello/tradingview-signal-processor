import os
from openai import OpenAI
from typing import Dict, Any
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def format_signal(self, signal_data: Dict[Any, Any]) -> str:
        """Format a trading signal into a clear message using OpenAI."""
        try:
            # Create a prompt for the signal formatting
            prompt = f"""Format this trading signal into a clear, professional message for subscribers.
            Include all relevant information and add emoji where appropriate.
            
            Signal Data:
            - Instrument: {signal_data.get('instrument', 'Unknown')}
            - Direction: {signal_data.get('direction', 'Unknown')}
            - Entry Price: {signal_data.get('entry_price', 'Unknown')}
            - Stop Loss: {signal_data.get('stop_loss', 'Unknown')}
            - Take Profit: {signal_data.get('take_profit', 'Unknown')}
            - Timeframe: {signal_data.get('timeframe', 'Unknown')}
            - Strategy: {signal_data.get('strategy', 'Unknown')}
            
            Format the message to be engaging and easy to read."""

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[{
                    "role": "system",
                    "content": "You are a professional trading signal formatter. Your job is to take raw trading signals and format them into clear, engaging messages for subscribers."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract and return the formatted message
            formatted_message = response.choices[0].message.content
            logger.info(f"Successfully formatted signal: {formatted_message[:100]}...")
            return formatted_message
            
        except Exception as e:
            logger.error(f"Error formatting signal: {str(e)}")
            # Return a basic formatted message as fallback
            return f"🚨 Trading Signal for {signal_data.get('instrument', 'Unknown')}\n" \
                   f"Direction: {signal_data.get('direction', 'Unknown')}\n" \
                   f"Entry: {signal_data.get('entry_price', 'Unknown')}\n" \
                   f"SL: {signal_data.get('stop_loss', 'Unknown')}\n" \
                   f"TP: {signal_data.get('take_profit', 'Unknown')}"
