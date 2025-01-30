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

    async def login(self) -> bool:
        """Login to TradingView"""
        try:
            # Go to login page
            await self.page.goto('https://www.tradingview.com/sign-in/', timeout=60000)
            logger.info("Navigated to login page")
            
            # Wait for email input and enter credentials
            await self.page.wait_for_selector('input[name="username"]')
            await self.page.fill('input[name="username"]', 'contact@jomarcello.com')
            await self.page.fill('input[name="password"]', 'JmT!102710')
            
            # Click sign in button
            await self.page.click('button[type="submit"]')
            
            # Wait for successful login
            await self.page.wait_for_selector('.tv-header__user-menu-button')
            logger.info("Successfully logged in")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    async def get_article_content(self, article_element) -> Optional[Dict[str, str]]:
        """Extract full article content and metadata"""
        try:
            # Get title
            title_element = await article_element.query_selector('[data-name="news-headline-title"]')
            if not title_element:
                return None
            
            title = await title_element.text_content()
            title = title.strip()

            # Get full content from the article body
            content = title  # Default to title if no body found
            body_element = await article_element.query_selector('.body-KX2tCBZq')
            if body_element:
                # Get all text content, including paragraphs
                paragraphs = await body_element.query_selector_all('p')
                content_parts = []
                for p in paragraphs:
                    text = await p.text_content()
                    if text:
                        content_parts.append(text.strip())
                content = '\n\n'.join(content_parts)

            # Get date
            date = datetime.now(pytz.UTC).isoformat()
            date_element = await article_element.query_selector('.date-TUPxzdRV')
            if date_element:
                date = await date_element.text_content()
                date = date.strip()

            # Get provider
            provider = "TradingView"
            provider_element = await article_element.query_selector('.provider-TUPxzdRV')
            if provider_element:
                provider = await provider_element.text_content()
                provider = provider.strip()

            return {
                'title': title,
                'content': content,
                'provider': provider,
                'date': date
            }

        except Exception as e:
            logger.warning(f"Error extracting article content: {str(e)}")
            return None

    async def get_news(self, instrument: str, max_articles: int = 3) -> List[Dict[str, str]]:
        """Get news articles from TradingView"""
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

            # Login first
            if not await self.login():
                logger.error("Failed to login, proceeding without authentication")

            # Navigate to TradingView news page
            url = f"https://www.tradingview.com/symbols/{instrument}/news/"
            try:
                await self.page.goto(url, timeout=60000, wait_until='domcontentloaded')
                logger.info(f"Navigated to {url}")
                
                # Wait for news content
                await self.page.wait_for_selector('article', timeout=60000)
                await asyncio.sleep(2)  # Give JavaScript time to execute
                
            except Exception as e:
                logger.error(f"Error loading page: {str(e)}")
                return []

            articles = []
            articles_found = 0

            # Get all article elements
            article_elements = await self.page.query_selector_all('article')
            
            for article in article_elements:
                if articles_found >= max_articles:
                    break

                try:
                    article_data = await self.get_article_content(article)
                    if article_data:
                        articles.append(article_data)
                        articles_found += 1
                        logger.info(f"Found article: {article_data['title']}")

                except Exception as e:
                    logger.warning(f"Error processing article: {str(e)}")
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