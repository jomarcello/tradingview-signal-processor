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
        """Login to TradingView when encountering login wall"""
        try:
            # Check if we're on a login page or hit a login wall
            login_selectors = [
                'input[name="username"]',
                '.tv-signin-dialog',
                '#signin-form'
            ]
            
            login_needed = False
            for selector in login_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    login_needed = True
                    break
                except Exception:
                    continue
            
            if not login_needed:
                return True

            logger.info("Login wall encountered, attempting to log in")
            
            # Fill in credentials
            await self.page.fill('input[name="username"]', 'contact@jomarcello.com')
            await self.page.fill('input[name="password"]', 'JmT!102710')
            
            # Click sign in button
            await self.page.click('button[type="submit"]')
            
            # Wait for login to complete
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # Give extra time for session to establish
            
            logger.info("Successfully logged in")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    async def get_article_content(self, article_element) -> Optional[Dict[str, str]]:
        """Extract article content by clicking through to full article"""
        try:
            # Get title from the article element
            title = ""
            title_selectors = [
                '.apply-overflow-tooltip[data-overflow-tooltip-text]',
                '[data-name="news-headline-title"]',
                '.title-HY0D0owe'
            ]
            
            for selector in title_selectors:
                try:
                    title_element = await article_element.query_selector(selector)
                    if title_element:
                        # Try to get title from tooltip attribute first
                        title = await title_element.get_attribute('data-overflow-tooltip-text')
                        if not title:
                            title = await title_element.text_content()
                        title = title.strip()
                        break
                except Exception:
                    continue

            if not title:
                return None

            # Get provider and date
            provider = "TradingView"
            provider_element = await article_element.query_selector('.provider-TUPxzdRV')
            if provider_element:
                provider = await provider_element.text_content()
                provider = provider.strip()

            date = datetime.now(pytz.UTC).isoformat()
            date_element = await article_element.query_selector('.date-TUPxzdRV')
            if date_element:
                date = await date_element.text_content()
                date = date.strip()

            # Try to click the article title to get full content
            try:
                await title_element.click()
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(2)

                # Check for login wall
                await self.login()

                # Try to get full content
                content = title  # Default to title
                body_element = await self.page.wait_for_selector('.body-KX2tCBZq', timeout=5000)
                if body_element:
                    paragraphs = await body_element.query_selector_all('p')
                    content_parts = []
                    for p in paragraphs:
                        text = await p.text_content()
                        if text:
                            content_parts.append(text.strip())
                    if content_parts:
                        content = '\n\n'.join(content_parts)

                # Get current URL for reference
                url = self.page.url

                # Go back to news list
                await self.page.go_back()
                await self.page.wait_for_selector('article', timeout=10000)

                return {
                    'title': title,
                    'content': content,
                    'provider': provider,
                    'date': date,
                    'url': url
                }

            except Exception as e:
                logger.warning(f"Could not get full content for {title}: {str(e)}")
                # Try to go back if we're stuck on an article
                try:
                    await self.page.go_back()
                    await self.page.wait_for_selector('article', timeout=10000)
                except Exception:
                    pass
                
                # Return article with just title/summary
                return {
                    'title': title,
                    'content': title,
                    'provider': provider,
                    'date': date
                }

        except Exception as e:
            logger.warning(f"Error processing article: {str(e)}")
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