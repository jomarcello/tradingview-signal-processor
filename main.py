from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json
import os
from dotenv import load_dotenv
import time
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Get TradingView credentials from environment
TRADINGVIEW_EMAIL = os.getenv('TRADINGVIEW_EMAIL')
TRADINGVIEW_PASSWORD = os.getenv('TRADINGVIEW_PASSWORD')

if not TRADINGVIEW_EMAIL or not TRADINGVIEW_PASSWORD:
    raise ValueError("TradingView credentials not set in environment variables")

app = FastAPI()

def setup_logging():
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)

logger = setup_logging()

class TradingSignal(BaseModel):
    instrument: str
    timestamp: Optional[str]

async def login_to_tradingview(page):
    """Login to TradingView using environment credentials"""
    try:
        logger.info("Attempting to log in to TradingView")
        
        # First try the main page with header login
        logger.info("Going to main page")
        await page.goto('https://www.tradingview.com/', 
                       wait_until='networkidle',
                       timeout=10000)
        
        # Look for the sign in button in the header
        logger.info("Looking for header sign in button")
        try:
            header_signin = await page.wait_for_selector('button[data-name="header-signin-button"]', timeout=5000)
            if header_signin:
                logger.info("Found header sign in button, clicking it")
                await header_signin.click()
                # Wait for the modal to appear
                await page.wait_for_selector('[data-dialog-name="sign-in-dialog"]', timeout=5000)
        except Exception as e:
            logger.warning(f"Could not find header sign in button: {str(e)}")
            # If header button not found, try direct URL
            logger.info("Trying direct sign in URL")
            await page.goto('https://www.tradingview.com/accounts/signin/', 
                          wait_until='networkidle',
                          timeout=10000)
        
        # Try to fill the form using JavaScript with retry
        logger.info("Attempting to fill form using JavaScript")
        fill_result = await page.evaluate(f'''() => {{
            function sleep(ms) {{
                return new Promise(resolve => setTimeout(resolve, ms));
            }}
            
            async function findElements(maxAttempts = 5) {{
                for (let attempt = 0; attempt < maxAttempts; attempt++) {{
                    // Try different strategies to find elements
                    const selectors = {{
                        email: [
                            'input[name="username"]',
                            'input[type="email"]',
                            'input[data-purpose="username"]',
                            'input[data-name="username"]',
                            'form input[type="text"]'
                        ],
                        password: [
                            'input[name="password"]',
                            'input[type="password"]',
                            'input[data-purpose="password"]',
                            'input[data-name="password"]'
                        ],
                        submit: [
                            'button[type="submit"]',
                            'button.tv-button--primary',
                            'button[data-name*="sign-in"]',
                            'button:has-text("Sign in")',
                            'button.submitButton'
                        ]
                    }};
                    
                    let emailInput, passwordInput, submitButton;
                    
                    // Try each selector
                    for (const emailSelector of selectors.email) {{
                        emailInput = document.querySelector(emailSelector);
                        if (emailInput) break;
                    }}
                    
                    for (const passwordSelector of selectors.password) {{
                        passwordInput = document.querySelector(passwordSelector);
                        if (passwordInput) break;
                    }}
                    
                    for (const submitSelector of selectors.submit) {{
                        submitButton = document.querySelector(submitSelector);
                        if (submitButton) break;
                    }}
                    
                    // Log what we found
                    console.log('Attempt', attempt + 1, 'found:', {{
                        email: emailInput ? emailInput.outerHTML : null,
                        password: passwordInput ? passwordInput.outerHTML : null,
                        submit: submitButton ? submitButton.outerHTML : null
                    }});
                    
                    if (emailInput && passwordInput && submitButton) {{
                        return {{ emailInput, passwordInput, submitButton }};
                    }}
                    
                    // Wait before next attempt
                    await sleep(1000);
                }}
                
                return null;
            }}
            
            return findElements().then(elements => {{
                if (!elements) {{
                    return {{
                        success: false,
                        error: 'Could not find elements after multiple attempts'
                    }};
                }}
                
                const {{ emailInput, passwordInput, submitButton }} = elements;
                
                // Fill in the form
                emailInput.value = '{os.getenv("TRADINGVIEW_EMAIL")}';
                emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                emailInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                
                passwordInput.value = '{os.getenv("TRADINGVIEW_PASSWORD")}';
                passwordInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                passwordInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                
                // Small delay before clicking
                return sleep(500).then(() => {{
                    submitButton.click();
                    return {{ 
                        success: true,
                        elements: {{
                            email: emailInput.outerHTML,
                            password: passwordInput.outerHTML,
                            submit: submitButton.outerHTML
                        }}
                    }};
                }});
            }});
        }}''')
        
        logger.info(f"Form fill result: {fill_result}")
        
        if not fill_result.get('success'):
            raise Exception(f"Could not find form elements: {fill_result.get('error')}")
            
        # Wait for login to complete with retry
        logger.info("Waiting for login to complete")
        retry_count = 0
        while retry_count < 3:
            try:
                await page.wait_for_selector('.tv-header__user-menu-button', timeout=3000)
                logger.info("Successfully logged in to TradingView")
                return
            except Exception as e:
                retry_count += 1
                if retry_count == 3:
                    raise Exception("Login verification failed after retries")
                logger.warning(f"Retry {retry_count}: Waiting for login completion")
                await page.wait_for_timeout(1000)
        
    except Exception as e:
        logger.error(f"Failed to log in to TradingView: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to log in to TradingView: {str(e)}")

async def get_news(pair: str) -> Dict:
    logger.info(f"Starting news scraping for {pair}")
    special_symbols = {
        'XAUUSD': 'GOLD'
    }
    
    symbol = special_symbols.get(pair, pair)
    logger.info(f"Using symbol: {symbol}")
    
    async with async_playwright() as p:
        logger.info("Launching browser")
        browser = await p.chromium.launch(headless=True)
        try:
            logger.info("Creating new page")
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            # First login to TradingView
            await login_to_tradingview(page)
            
            # Now navigate to news page
            url = f"https://www.tradingview.com/symbols/{symbol}/news/"
            logger.info(f"Navigating to {url}")
            await page.goto(url)
            
            logger.info("Waiting for news table")
            await page.wait_for_selector('.news-table', timeout=10000)
            
            logger.info("Finding first news article")
            first_news = page.locator('.news-table tr:first-child td.desc a')
            news_title = await first_news.text_content()
            news_link = await first_news.get_attribute('href')
            
            full_news_url = f"https://www.tradingview.com{news_link}"
            logger.info(f"Navigating to news article: {full_news_url}")
            await page.goto(full_news_url)
            
            logger.info("Waiting for article content")
            article = await page.wait_for_selector('article')
            article_content = await article.text_content()
            
            logger.info("Successfully scraped news")
            return {
                "title": news_title.strip(),
                "content": article_content.strip(),
                "url": full_news_url
            }
        except Exception as e:
            logger.error(f"Error scraping news: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            logger.info("Closing browser")
            await browser.close()

async def analyze_sentiment(content: str) -> Dict:
    # Simple sentiment analysis based on keywords
    bullish_words = ['bullish', 'surge', 'gain', 'rise', 'higher', 'positive']
    bearish_words = ['bearish', 'drop', 'fall', 'lower', 'negative', 'decline']
    
    content_lower = content.lower()
    bullish_count = sum(1 for word in bullish_words if word in content_lower)
    bearish_count = sum(1 for word in bearish_words if word in content_lower)
    
    total = bullish_count + bearish_count
    if total == 0:
        score = 0.5
        label = "neutral"
    else:
        score = bullish_count / total
        if score > 0.6:
            label = "bullish"
        elif score < 0.4:
            label = "bearish"
        else:
            label = "neutral"
    
    return {
        "score": score,
        "label": label,
        "bullish_words": bullish_count,
        "bearish_words": bearish_count
    }

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "TradingView Signal Processor API",
        "endpoints": {
            "POST /trading-signal": "Process trading signals and news",
            "GET /health": "Health check"
        }
    }

@app.post("/trading-signal")
async def process_trading_signal(signal: TradingSignal):
    try:
        logger.info(f"Received trading signal: {json.dumps(signal.dict(), indent=2)}")
        
        # Initialize Playwright
        logger.info("Starting news scraping for EURUSD")
        logger.info(f"Using symbol: {signal.instrument}")
        async with async_playwright() as p:
            # Launch browser with optimized settings
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--no-sandbox',
                    '--disable-extensions',
                    '--disable-notifications',
                    '--disable-geolocation'
                ]
            )
            
            # Create a new context with specific settings
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True
            )

            # Add route to block unnecessary resources
            await context.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,otf,eot}", lambda route: route.abort())
            await context.route("**/{analytics,tracking,advertisement}**", lambda route: route.abort())
            
            # Create new page
            logger.info("Creating new page")
            page = await context.new_page()
            
            try:
                # Login to TradingView
                await login_to_tradingview(page)
                
                # Now navigate to news page
                url = f"https://www.tradingview.com/symbols/{signal.instrument}/news/"
                logger.info(f"Navigating to {url}")
                await page.goto(url)
                
                logger.info("Waiting for news table")
                await page.wait_for_selector('.news-table', timeout=10000)
                
                logger.info("Finding first news article")
                first_news = page.locator('.news-table tr:first-child td.desc a')
                news_title = await first_news.text_content()
                news_link = await first_news.get_attribute('href')
                
                full_news_url = f"https://www.tradingview.com{news_link}"
                logger.info(f"Navigating to news article: {full_news_url}")
                await page.goto(full_news_url)
                
                logger.info("Waiting for article content")
                article = await page.wait_for_selector('article')
                article_content = await article.text_content()
                
                logger.info("Successfully scraped news")
                news = {
                    "title": news_title.strip(),
                    "content": article_content.strip(),
                    "url": full_news_url
                }
                
                # Analyze sentiment
                sentiment = await analyze_sentiment(news['content'])
                
                # Combine all data
                combined_data = {
                    "signal": signal.dict(),
                    "news": news,
                    "sentiment": sentiment,
                    "timestamp": signal.timestamp
                }
                
                return {
                    "status": "success",
                    "message": "Signal processed successfully",
                    "data": combined_data
                }
            except Exception as e:
                logger.error(f"Error during processing: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
            finally:
                await browser.close()
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
