from playwright.async_api import async_playwright

class NewsScraper:
    def __init__(self):
        self.playwright = async_playwright()
        
    async def get_news_with_playwright(self, instrument: str):
        browser = await self.playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(f"https://www.tradingview.com/symbols/{instrument}/news/")
            
            # Wait for news articles to load
            await page.wait_for_selector('div[data-name="news-article"]', timeout=10000)
            
            # Click on first article
            await page.click('div[data-name="news-article"]:first-child')
            
            # Wait for article content to load
            await page.wait_for_selector('div.body-KX2tCBZq', timeout=10000)
            
            # Extract content using the specific TradingView article structure
            content = await page.evaluate('''() => {
                const article = document.querySelector('div.body-KX2tCBZq');
                if (!article) return null;
                
                // Extract text content
                const paragraphs = Array.from(article.querySelectorAll('p'))
                    .map(p => p.textContent.trim())
                    .filter(text => text.length > 0);
                    
                // Extract images with captions
                const images = Array.from(article.querySelectorAll('figure')).map(fig => {
                    const img = fig.querySelector('img');
                    const caption = fig.querySelector('.description-S5VA5POt');
                    return {
                        src: img?.src,
                        alt: img?.alt,
                        caption: caption?.textContent.trim()
                    };
                });
                
                return {
                    text: paragraphs,
                    images: images
                };
            }''')
            
            return content
            
        finally:
            await browser.close()
