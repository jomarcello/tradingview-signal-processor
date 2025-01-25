import os
from openai import OpenAI
from typing import List, Dict, Any
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def analyze_news(self, news_articles: List[Dict[str, Any]], instrument: str) -> Dict[str, Any]:
        """Analyze news articles and provide a summary with sentiment analysis."""
        try:
            # Create a prompt for news analysis
            articles_text = "\n\n".join([
                f"Title: {article.get('title', 'No Title')}\n"
                f"Content: {article.get('content', 'No Content')}\n"
                f"Source: {article.get('source', 'Unknown')}\n"
                f"Date: {article.get('date', 'Unknown')}"
                for article in news_articles
            ])
            
            prompt = f"""Analyze these news articles about {instrument} and provide:
            1. A concise summary of the key points
            2. Overall market sentiment (Bullish/Bearish/Neutral)
            3. Key factors influencing the market
            4. Potential impact on trading decisions
            
            News Articles:
            {articles_text}
            
            Format your response in a clear, structured way with emoji where appropriate."""

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[{
                    "role": "system",
                    "content": "You are a financial news analyst specializing in market sentiment analysis. Your job is to analyze news articles and provide clear, actionable insights for traders."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.5,
                max_tokens=1000
            )
            
            # Extract the analysis
            analysis = response.choices[0].message.content
            
            # Get a specific trading verdict
            verdict_prompt = f"""Based on the news analysis, provide a clear trading verdict for {instrument}.
            Previous analysis: {analysis}
            
            Format your response as a JSON with these fields:
            - verdict: (STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL)
            - confidence: (percentage between 0-100)
            - key_reason: (brief explanation)"""
            
            verdict_response = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[{
                    "role": "system",
                    "content": "You are a trading advisor that provides clear, decisive trading verdicts based on news analysis."
                }, {
                    "role": "user",
                    "content": verdict_prompt
                }],
                temperature=0.3,
                max_tokens=200
            )
            
            # Return both the detailed analysis and the trading verdict
            return {
                "analysis": analysis,
                "verdict": verdict_response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Error analyzing news: {str(e)}")
            return {
                "analysis": "Error analyzing news articles.",
                "verdict": {
                    "verdict": "NEUTRAL",
                    "confidence": 0,
                    "key_reason": "Error in analysis"
                }
            }

    async def get_market_context(self, instrument: str) -> str:
        """Get broader market context and potential correlations."""
        try:
            prompt = f"""Provide a brief market context analysis for {instrument}. Consider:
            1. Related instruments and their performance
            2. Key market drivers
            3. Important technical levels
            4. Upcoming economic events that might impact the instrument
            
            Format your response in a clear, concise way."""

            response = await self.client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[{
                    "role": "system",
                    "content": "You are a market analyst providing context and correlation analysis for trading instruments."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.5,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error getting market context: {str(e)}")
            return f"Unable to retrieve market context for {instrument}"
