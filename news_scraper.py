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
        """Get news articles from ForexFactory market page"""
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

            # Format instrument for URL (e.g., EURUSD -> eurusd)
            instrument_lower = instrument.lower()

            # Navigate to ForexFactory market page for the specific instrument
            url = f"https://www.forexfactory.com/market/{instrument_lower}"
            try:
                await self.page.goto(url, timeout=60000, wait_until='domcontentloaded')
                logger.info(f"Navigated to {url}")
                
                # Wait for the Latest Stories section
                await self.page.wait_for_selector(".market__stories", timeout=60000)
            except Exception as e:
                logger.error(f"Error loading page: {str(e)}")
                return []

            articles = []
            articles_found = 0

            # Get all story items from the Latest Stories section
            story_items = await self.page.query_selector_all(".market__stories .story")
            
            for item in story_items:
                if articles_found >= max_articles:
                    break

                try:
                    # Get source
                    source_element = await item.query_selector(".story__source")
                    source = "Unknown"
                    if source_element:
                        source = await source_element.text_content()
                        source = source.strip()

                    # Get title
                    title_element = await item.query_selector(".story__title")
                    if not title_element:
                        continue
                        
                    title = await title_element.text_content()
                    title = title.strip()

                    # Get time
                    time_str = datetime.now(pytz.UTC).isoformat()
                    time_element = await item.query_selector(".story__time")
                    if time_element:
                        time_str = await time_element.text_content()
                        time_str = time_str.strip()

                    # Get link to full article
                    link = None
                    link_element = await title_element.query_selector("a")
                    if link_element:
                        link = await link_element.get_attribute("href")
                        if link and not link.startswith("http"):
                            link = f"https://www.forexfactory.com{link}"

                    # Get full content if link is available
                    content = title  # Default to title
                    if link:
                        try:
                            await self.page.goto(link, timeout=30000, wait_until='domcontentloaded')
                            content_element = await self.page.wait_for_selector(".story__content", timeout=5000)
                            if content_element:
                                content = await content_element.text_content()
                                content = content.strip()
                            # Go back to the market page
                            await self.page.goto(url, timeout=30000, wait_until='domcontentloaded')
                            await self.page.wait_for_selector(".market__stories", timeout=30000)
                        except Exception as e:
                            logger.warning(f"Could not get full content, using title: {str(e)}")

                    articles.append({
                        'title': title,
                        'content': content,
                        'source': source,
                        'date': time_str,
                        'link': link
                    })
                    
                    articles_found += 1
                    logger.info(f"Found article from {source}: {title}")

                except Exception as e:
                    logger.warning(f"Error processing story item: {str(e)}")
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