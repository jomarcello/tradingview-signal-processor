import logging
import traceback
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page
import asyncio
from datetime import datetime
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsScraper:
    def __init__(self):
        self.browser = None
        self.page = None
        
    async def initialize(self) -> None:
        """Initialize browser with optimized settings"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-software-rasterizer',
                    '--js-flags=--max-old-space-size=500'
                ]
            )
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    async def get_news(self, instrument: str, max_articles: int = 3) -> List[Dict[str, str]]:
        """Get news articles for a specific instrument"""
        try:
            if not self.browser:
                await self.initialize()

            logger.info(f"Getting news for {instrument}")
            
            # Create new page with custom viewport
            self.page = await self.browser.new_page(
                viewport={'width': 1920, 'height': 1080}
            )
            
            # Set headers to avoid detection
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            })

            # Navigate to TradingView news page
            url = f"https://www.tradingview.com/symbols/{instrument}/news/"
            await self.page.goto(url, wait_until='networkidle')
            logger.info(f"Navigated to {url}")

            # Wait for content to load
            await self.page.wait_for_selector("article", timeout=30000)
            
            articles = []
            scroll_attempts = 0
            max_scroll_attempts = 3

            # Scroll to load more articles
            while scroll_attempts < max_scroll_attempts and len(articles) < max_articles:
                # Get current articles
                new_articles = await self._extract_articles()
                articles.extend(new_articles)
                
                if len(articles) >= max_articles:
                    break

                # Scroll down
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                scroll_attempts += 1

            # Filter and format articles
            formatted_articles = []
            wanted_providers = {'reuters', 'forexlive', 'dow jones newswires', 'trading economics'}
            
            for article in articles:
                if article['provider'].lower() in wanted_providers:
                    formatted_articles.append({
                        'title': article['title'],
                        'content': article['content'],
                        'provider': article['provider'],
                        'date': article['date']
                    })
                    
                    if len(formatted_articles) >= max_articles:
                        break

            logger.info(f"Found {len(formatted_articles)} relevant articles")
            return formatted_articles[:max_articles]

        except Exception as e:
            logger.error(f"Error getting news: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

        finally:
            if self.page:
                await self.page.close()

    async def _extract_articles(self) -> List[Dict[str, str]]:
        """Extract article information from the current page"""
        articles = []
        
        # Get all article elements
        article_elements = await self.page.query_selector_all("article")
        
        for article in article_elements:
            try:
                # Get provider
                provider_element = await article.query_selector('.provider-TUPxzdRV')
                if not provider_element:
                    continue
                provider = await provider_element.text_content()
                
                # Get title
                title_element = await article.query_selector('[data-name="news-headline-title"]')
                if not title_element:
                    continue
                title = await title_element.text_content()
                
                # Get date if available
                date = datetime.now(pytz.UTC).isoformat()
                date_element = await article.query_selector('.date-TUPxzdRV')
                if date_element:
                    date = await date_element.text_content()
                
                articles.append({
                    'title': title.strip(),
                    'content': title.strip(),  # Use title as content since full content requires login
                    'provider': provider.strip(),
                    'date': date
                })
                
            except Exception as e:
                logger.warning(f"Error extracting article: {str(e)}")
                continue
                
        return articles

    async def cleanup(self) -> None:
        """Clean up browser resources"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                logger.info("Browser resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up browser: {str(e)}")

async def get_news_articles(instrument: str, max_articles: int = 3) -> List[Dict[str, str]]:
    """Helper function to get news articles"""
    scraper = NewsScraper()
    try:
        return await scraper.get_news(instrument, max_articles)
    finally:
        await scraper.cleanup()