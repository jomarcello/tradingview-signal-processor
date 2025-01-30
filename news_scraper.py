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
                    '--disable-extensions'
                ]
            )
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    async def login(self) -> bool:
        """Login to TradingView when encountering login wall"""
        try:
            # Fill in credentials
            await self.page.fill('input[name="username"]', 'contact@jomarcello.com')
            await self.page.fill('input[name="password"]', 'JmT!102710')
            
            # Click sign in button
            await self.page.click('button[type="submit"]')
            
            # Wait for login to complete
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            logger.info("Successfully logged in")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    async def get_article_content(self, headline_element) -> Optional[Dict[str, str]]:
        """Get full article content by navigating to the article page"""
        try:
            # Get the article link
            link = await headline_element.evaluate('(element) => element.closest("a").href')
            if not link:
                return None

            # Get initial metadata before navigation
            title = await headline_element.text_content()
            title = title.strip()

            # Get provider
            provider = "TradingView"
            provider_element = await headline_element.evaluate('(element) => element.closest("article").querySelector(".provider-TUPxzdRV")')
            if provider_element:
                provider = provider_element['textContent'].strip()

            # Get date
            date = datetime.now(pytz.UTC).isoformat()
            date_element = await headline_element.evaluate('(element) => element.closest("article").querySelector(".date-TUPxzdRV")')
            if date_element:
                date = date_element['textContent'].strip()

            # Navigate to article
            await self.page.goto(link, timeout=30000)
            await asyncio.sleep(2)

            # Check for login wall
            login_button = await self.page.query_selector('button[type="submit"]')
            if login_button:
                await self.login()
                await asyncio.sleep(2)

            # Get full article content
            content = title  # Default to title if we can't get content
            body_element = await self.page.query_selector('.body-KX2tCBZq')
            if body_element:
                paragraphs = await body_element.query_selector_all('p')
                content_parts = []
                for p in paragraphs:
                    text = await p.text_content()
                    if text:
                        content_parts.append(text.strip())
                if content_parts:
                    content = '\n\n'.join(content_parts)

            # Go back to news list
            await self.page.goto(f"https://www.tradingview.com/symbols/{self.current_instrument}/news/", timeout=30000)
            await self.page.wait_for_selector('.news-headline-card', timeout=10000)

            return {
                'title': title,
                'content': content,
                'provider': provider,
                'date': date,
                'url': link
            }

        except Exception as e:
            logger.warning(f"Error getting article content: {str(e)}")
            # Try to go back to news list
            try:
                await self.page.goto(f"https://www.tradingview.com/symbols/{self.current_instrument}/news/", timeout=30000)
                await self.page.wait_for_selector('.news-headline-card', timeout=10000)
            except Exception:
                pass
            return None

    async def get_news(self, instrument: str, max_articles: int = 3) -> List[Dict[str, str]]:
        """Get news articles from TradingView"""
        try:
            if not self.browser:
                await self.initialize()

            self.current_instrument = instrument
            logger.info(f"Getting news for {instrument}")
            
            # Create new page
            self.page = await self.browser.new_page()
            
            # Navigate to TradingView news page
            url = f"https://www.tradingview.com/symbols/{instrument}/news/"
            try:
                await self.page.goto(url, timeout=30000)
                logger.info(f"Navigated to {url}")
                
                # Wait for news content
                await self.page.wait_for_selector('.news-headline-card', timeout=10000)
                
            except Exception as e:
                logger.error(f"Error loading page: {str(e)}")
                return []

            articles = []
            articles_found = 0

            # Get all headlines
            headlines = await self.page.query_selector_all('[data-name="news-headline-title"]')
            
            for headline in headlines:
                if articles_found >= max_articles:
                    break

                try:
                    article_data = await self.get_article_content(headline)
                    if article_data:
                        articles.append(article_data)
                        articles_found += 1
                        logger.info(f"Found article: {article_data['title']}")

                except Exception as e:
                    logger.warning(f"Error processing headline: {str(e)}")
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