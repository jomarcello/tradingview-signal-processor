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
            url = f"https://www.forexfactory.com/news"
            try:
                # Navigate and wait for network idle
                await self.page.goto(url, wait_until='networkidle', timeout=60000)
                logger.info(f"Navigated to {url}")
                
                # Wait for any content to load
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(2)  # Give JavaScript time to execute
                
            except Exception as e:
                logger.error(f"Error loading page: {str(e)}")
                return []

            articles = []
            articles_found = 0

            # Find all news links
            news_links = await self.page.query_selector_all("a[href^='/news/']")
            
            for link in news_links:
                if articles_found >= max_articles:
                    break

                try:
                    # Get title and content from the link
                    title = await link.text_content()
                    title = title.strip()
                    
                    # Get full content from title attribute
                    content = await link.get_attribute("title")
                    if not content:
                        content = title
                    
                    # Get href for the article ID
                    href = await link.get_attribute("href")
                    article_id = href.split("-")[0].split("/")[-1] if href else None
                    
                    # Get timestamp (we'll use current time as FF doesn't show time in the link)
                    time_str = datetime.now(pytz.UTC).isoformat()

                    articles.append({
                        'title': title,
                        'content': content,
                        'source': 'ForexFactory',
                        'date': time_str,
                        'article_id': article_id
                    })
                    
                    articles_found += 1
                    logger.info(f"Found article: {title}")

                except Exception as e:
                    logger.warning(f"Error processing news link: {str(e)}")
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