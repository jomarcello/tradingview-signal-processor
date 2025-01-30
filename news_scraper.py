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
        """Get news articles from ForexFactory"""
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

            # Navigate to ForexFactory news page
            url = "https://www.forexfactory.com/news"
            try:
                await self.page.goto(url, timeout=60000, wait_until='domcontentloaded')
                logger.info(f"Navigated to {url}")
                
                # Wait for content
                await self.page.wait_for_selector(".ff-news-headlines", timeout=60000)
            except Exception as e:
                logger.error(f"Error loading page: {str(e)}")
                return []

            # Get currency pair components (e.g., EUR/USD -> EUR and USD)
            currency1 = instrument[:3]
            currency2 = instrument[3:] if len(instrument) > 3 else None

            articles = []
            articles_found = 0

            # Get all news items
            news_items = await self.page.query_selector_all(".ff-news-headlines .headline")
            
            for item in news_items:
                if articles_found >= max_articles:
                    break

                try:
                    # Get currency tag
                    currency_element = await item.query_selector(".currency")
                    if not currency_element:
                        continue
                        
                    currencies = await currency_element.text_content()
                    currencies = currencies.upper().strip()
                    
                    # Check if the news is relevant for our currency pair
                    if currency1 not in currencies and (not currency2 or currency2 not in currencies):
                        continue

                    # Get title
                    title_element = await item.query_selector(".title")
                    if not title_element:
                        continue
                        
                    title = await title_element.text_content()
                    
                    # Get impact
                    impact = "medium"  # default
                    impact_element = await item.query_selector(".impact")
                    if impact_element:
                        impact_class = await impact_element.get_attribute("class")
                        if "high" in impact_class:
                            impact = "high"
                        elif "low" in impact_class:
                            impact = "low"

                    # Get time
                    time_str = datetime.now(pytz.UTC).isoformat()
                    time_element = await item.query_selector(".date")
                    if time_element:
                        time_str = await time_element.text_content()

                    # Click to get full content
                    await title_element.click()
                    await asyncio.sleep(2)

                    # Get full content
                    content = title  # Default to title
                    content_element = await self.page.wait_for_selector(".ff-news-content", timeout=5000)
                    if content_element:
                        content = await content_element.text_content()
                        content = content.strip()

                    articles.append({
                        'title': title.strip(),
                        'content': content,
                        'impact': impact,
                        'date': time_str,
                        'currencies': currencies,
                        'provider': 'ForexFactory'
                    })
                    
                    articles_found += 1
                    logger.info(f"Found article: {title} (Impact: {impact})")

                    # Go back to news list
                    await self.page.go_back()
                    await self.page.wait_for_selector(".ff-news-headlines", timeout=5000)

                except Exception as e:
                    logger.warning(f"Error processing news item: {str(e)}")
                    continue

            logger.info(f"Found {len(articles)} relevant articles")
            return articles[:max_articles]

        except Exception as e:
            logger.error(f"Error getting news: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

        finally:
            if self.page:
                await self.page.close()

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