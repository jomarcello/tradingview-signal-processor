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

async def login_to_tradingview(page):
    """Login to TradingView using environment credentials"""
    try:
        logger.info("Attempting to log in to TradingView")
        
        # Set extra headers
        await page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Track loaded resources
        loaded_resources = set()
        required_resources = {
            'auth_page_tvd',
            'runtime',
            'quote-ticker'
        }

        def log_request(request):
            url = request.url
            logger.info(f"Network request: {url}")
            for resource in required_resources:
                if resource in url:
                    loaded_resources.add(resource)

        def log_response(response):
            url = response.url
            logger.info(f"Network response: {url} - {response.status}")

        page.on("request", log_request)
        page.on("response", log_response)
        
        # Go directly to the email sign in page
        logger.info("Going to email sign in page")
        await page.goto('https://www.tradingview.com/accounts/signin/', wait_until='networkidle', timeout=10000)
        
        # Wait for the page to load and stabilize
        logger.info("Waiting for page to stabilize")
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_load_state('networkidle')

        # Wait for required resources
        logger.info("Waiting for required resources to load")
        timeout = time.time() + 10  # 10 second timeout
        while len(loaded_resources) < len(required_resources) and time.time() < timeout:
            await page.wait_for_timeout(100)
            logger.info(f"Loaded resources: {loaded_resources}")
        
        if len(loaded_resources) < len(required_resources):
            logger.warning(f"Not all resources loaded. Missing: {required_resources - loaded_resources}")
        
        # Extra wait for dynamic content
        logger.info("Waiting for dynamic content")
        await page.wait_for_timeout(5000)
        
        # Take screenshot of initial state
        logger.info("Taking screenshot of initial state")
        await page.screenshot(path="/tmp/initial-state.png")
        
        # Log the current URL and content
        current_url = page.url
        content = await page.content()
        logger.info(f"Current URL: {current_url}")
        logger.info(f"Page content length: {len(content)} characters")
        logger.info(f"Page content preview: {content[:500]}...")

        # Wait for any form elements to be present
        logger.info("Waiting for form elements")
        form_present = await page.evaluate('''() => {
            return new Promise((resolve) => {
                const checkForm = () => {
                    const inputs = document.querySelectorAll('input');
                    const visibleInputs = Array.from(inputs).filter(el => {
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' && style.visibility !== 'hidden' && !el.hidden;
                    });
                    
                    if (visibleInputs.length > 0) {
                        resolve(true);
                    } else {
                        setTimeout(checkForm, 100);
                    }
                };
                checkForm();
            });
        }''')

        # Try to fill the form using JavaScript
        logger.info("Attempting to fill form using JavaScript")
        fill_result = await page.evaluate(f'''() => {{
            function findInput(attributes) {{
                // Try different query strategies
                for (const selector of [
                    'input[type="email"], input[type="text"]',
                    'input:not([type="hidden"])',
                    'input'
                ]) {{
                    const inputs = Array.from(document.querySelectorAll(selector));
                    const input = inputs.find(el => {{
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none' && 
                               style.visibility !== 'hidden' && 
                               !el.hidden &&
                               rect.width > 0 &&
                               rect.height > 0;
                    }});
                    if (input) return input;
                }}
                return null;
            }}

            function findPasswordInput() {{
                const selectors = [
                    'input[type="password"]',
                    'input[name="password"]',
                    'input.tv-control-material-textbox__input[type="password"]'
                ];
                
                for (const selector of selectors) {{
                    const input = document.querySelector(selector);
                    if (input) {{
                        const style = window.getComputedStyle(input);
                        const rect = input.getBoundingClientRect();
                        if (style.display !== 'none' && 
                            style.visibility !== 'hidden' && 
                            !input.hidden &&
                            rect.width > 0 &&
                            rect.height > 0) {{
                            return input;
                        }}
                    }}
                }}
                return null;
            }}

            function findSubmitButton() {{
                for (const selector of [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button.tv-button--primary',
                    '[data-name="submit"]',
                    'button'
                ]) {{
                    const buttons = document.querySelectorAll(selector);
                    const button = Array.from(buttons).find(el => {{
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none' && 
                               style.visibility !== 'hidden' && 
                               !el.hidden &&
                               rect.width > 0 &&
                               rect.height > 0;
                    }});
                    if (button) return button;
                }}
                return null;
            }}

            // Log all form-related elements for debugging
            const allElements = Array.from(document.querySelectorAll('input, button, form')).map(el => {{
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return {{
                    tag: el.tagName,
                    type: el.type,
                    id: el.id,
                    name: el.name,
                    class: el.className,
                    hidden: el.hidden,
                    display: style.display,
                    visibility: style.visibility,
                    dimensions: {{
                        width: rect.width,
                        height: rect.height
                    }},
                    attributes: Object.fromEntries(
                        Array.from(el.attributes).map(attr => [attr.name, attr.value])
                    )
                }};
            }});

            console.log('Available elements:', allElements);

            const emailInput = findInput();
            const passwordInput = findPasswordInput();
            const submitButton = findSubmitButton();

            if (!emailInput || !passwordInput || !submitButton) {{
                return {{
                    success: false,
                    error: 'Missing elements',
                    found: {{
                        email: !!emailInput,
                        password: !!passwordInput,
                        submit: !!submitButton
                    }},
                    allElements
                }};
            }}

            emailInput.value = '{TRADINGVIEW_EMAIL}';
            emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            emailInput.dispatchEvent(new Event('change', {{ bubbles: true }}));

            passwordInput.value = '{TRADINGVIEW_PASSWORD}';
            passwordInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            passwordInput.dispatchEvent(new Event('change', {{ bubbles: true }}));

            return {{
                success: true,
                elements: {{
                    email: {{
                        tag: emailInput.tagName,
                        type: emailInput.type,
                        id: emailInput.id,
                        name: emailInput.name,
                        class: emailInput.className,
                        rect: emailInput.getBoundingClientRect()
                    }},
                    password: {{
                        tag: passwordInput.tagName,
                        type: passwordInput.type,
                        id: passwordInput.id,
                        name: passwordInput.name,
                        class: passwordInput.className,
                        rect: passwordInput.getBoundingClientRect()
                    }},
                    submit: {{
                        tag: submitButton.tagName,
                        type: submitButton.type,
                        id: submitButton.id,
                        name: submitButton.name,
                        class: submitButton.className,
                        rect: submitButton.getBoundingClientRect()
                    }}
                }},
                allElements
            }};
        }}''')
        
        logger.info(f"Form fill result: {json.dumps(fill_result, indent=2)}")
        
        if not fill_result.get('success'):
            logger.error(f"Failed to fill form: {fill_result.get('error')}")
            logger.info(f"Found elements: {fill_result.get('found')}")
            logger.info(f"All elements: {json.dumps(fill_result.get('allElements'), indent=2)}")
            raise Exception("Could not find all form elements")
            
        # Take screenshot after filling
        logger.info("Taking screenshot after filling")
        await page.screenshot(path="/tmp/after-fill.png")
        
        # Click submit using JavaScript
        logger.info("Clicking submit button")
        click_result = await page.evaluate('''() => {
            const button = document.querySelector('button[type="submit"]') ||
                          document.querySelector('input[type="submit"]') ||
                          document.querySelector('button.tv-button--primary') ||
                          document.querySelector('[data-name="submit"]') ||
                          document.querySelector('button');
            
            if (button) {
                const rect = button.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    button.click();
                    return {success: true, rect};
                }
                return {success: false, error: 'Button has no dimensions'};
            }
            return {success: false, error: 'No button found'};
        }''')
        
        logger.info(f"Click result: {json.dumps(click_result, indent=2)}")
        
        if not click_result.get('success'):
            raise Exception(f"Could not click submit button: {click_result.get('error')}")
            
        # Wait for login to complete
        logger.info("Waiting for login to complete")
        await page.wait_for_selector('.tv-header__user-menu-button', timeout=5000)
        logger.info("Successfully logged in to TradingView")
        
    except Exception as e:
        logger.error(f"Failed to log in to TradingView: {str(e)}")
        logger.info("Taking error screenshot")
        await page.screenshot(path="/tmp/login-error.png")
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
async def receive_trading_signal(signal: Dict):
    try:
        # Log incoming signal
        logger.info(f"Received trading signal: {json.dumps(signal, indent=2)}")
        
        # Get the trading pair
        pair = signal.get('instrument')
        if not pair:
            raise HTTPException(status_code=400, detail="No trading pair provided")
        
        # Get news for the pair
        news = await get_news(pair)
        
        # Analyze sentiment
        sentiment = await analyze_sentiment(news['content'])
        
        # Combine all data
        combined_data = {
            "signal": signal,
            "news": news,
            "sentiment": sentiment,
            "timestamp": signal.get('timestamp', None)
        }
        
        return {
            "status": "success",
            "message": "Signal processed successfully",
            "data": combined_data
        }
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
