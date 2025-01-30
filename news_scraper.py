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
                # Navigate and wait for network idle
                await self.page.goto(url, wait_until='networkidle', timeout=60000)
                logger.info(f"Navigated to {url}")
                
                # Wait for any content to load
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(2)  # Give JavaScript time to execute
                
                # Try different selectors for news content
                selectors = [
                    ".market__stories",
                    ".market-content",
                    "div[class*='stories']",
                    "div[class*='news']"
                ]
                
                content_found = False
                for selector in selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        logger.info(f"Found content with selector: {selector}")
                        content_found = True
                        break
                    except Exception:
                        continue
                
                if not content_found:
                    logger.error("Could not find news content with any selector")
                    return []
                
            except Exception as e:
                logger.error(f"Error loading page: {str(e)}")
                return []

            articles = []
            articles_found = 0

            # Try to find news items with different selectors
            story_selectors = [
                ".market__stories .story",
                ".market-content article",
                "div[class*='stories'] article",
                "div[class*='news'] article"
            ]
            
            story_items = []
            for selector in story_selectors:
                try:
                    items = await self.page.query_selector_all(selector)
                    if items:
                        story_items = items
                        logger.info(f"Found news items with selector: {selector}")
                        break
                except Exception:
                    continue

            if not story_items:
                logger.error("No news items found")
                return []

            for item in story_items:
                if articles_found >= max_articles:
                    break

                try:
                    # Try different selectors for each element
                    title = ""
                    for title_selector in [".story__title", ".title", "h2", "h3"]:
                        try:
                            title_element = await item.query_selector(title_selector)
                            if title_element:
                                title = await title_element.text_content()
                                title = title.strip()
                                break
                        except Exception:
                            continue

                    if not title:
                        continue

                    # Get source
                    source = "ForexFactory"
                    for source_selector in [".story__source", ".source", ".provider"]:
                        try:
                            source_element = await item.query_selector(source_selector)
                            if source_element:
                                source = await source_element.text_content()
                                source = source.strip()
                                break
                        except Exception:
                            continue

                    # Get time
                    time_str = datetime.now(pytz.UTC).isoformat()
                    for time_selector in [".story__time", ".time", ".date"]:
                        try:
                            time_element = await item.query_selector(time_selector)
                            if time_element:
                                time_str = await time_element.text_content()
                                time_str = time_str.strip()
                                break
                        except Exception:
                            continue

                    # Get content
                    content = title  # Default to title
                    for content_selector in [".story__content", ".content", ".description"]:
                        try:
                            content_element = await item.query_selector(content_selector)
                            if content_element:
                                content = await content_element.text_content()
                                content = content.strip()
                                if len(content) > len(title):  # Only use if it's longer than title
                                    break
                        except Exception:
                            continue

                    articles.append({
                        'title': title,
                        'content': content,
                        'source': source,
                        'date': time_str
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