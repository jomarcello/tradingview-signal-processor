# Mogelijke verbeterpunten:
# 1. Robustere error handling voor TradingView API
# 2. Distributed task queue voor schaalbaarheid
# 3. Duidelijkere scheiding tussen signalen en news scraping

import os
from celery import Celery
from flask import Flask, request, jsonify
from flask_cors import CORS
from tenacity import retry, wait_exponential, stop_after_attempt
import requests
from news_scraper import NewsScraper
from celery.chain import chain, group
from subscriber_manager import find_subscribers
import logging

# Flask app initialisatie
flask_app = Flask(__name__)
CORS(flask_app)

# Celery app initialisatie
celery_app = Celery(__name__, broker=os.getenv('RABBITMQ_URL'))
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Amsterdam',
    enable_utc=True
)

scraper = NewsScraper()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def validate_signal(signal):
    required_fields = ['asset', 'action', 'price', 'timeframe']
    return all(field in signal for field in required_fields)

def log_error(message):
    print(f"[ERROR] {message}")

@retry(before_sleep=lambda retry_state: print(f"Retry attempt {retry_state.attempt_number}"))
def log_retry_attempt(retry_state):
    pass

@flask_app.route('/signal', methods=['POST'])
def handle_signal():
    try:
        data = request.get_json()
        if not validate_signal(data):
            return jsonify({"error": "Ongeldig signaalformaat"}), 400
            
        process_signal_task.delay(data)
        return jsonify({"status": "success", "message": "Signaal in verwerking"})
        
    except Exception as e:
        log_error(str(e))
        return jsonify({"error": "Interne serverfout"}), 500

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "version": "1.0.0"})

@celery_app.task(bind=True, max_retries=3)
def process_signal_task(self, signal):
    try:
        # Parallelle taken chain
        chain(
            scrape_news.s(signal['asset']) | 
            group(
                ai_process_news.s() | match_subscribers.s(),
                ai_process_signal.s(signal)
            )
        ).apply_async()
        
    except Exception as e:
        self.retry(exc=e, countdown=60)

@celery_app.task
def scrape_news(asset):
    try:
        return scraper.scrape_articles(asset)
    except Exception as e:
        log_error(f"Nieuws scraping mislukt: {str(e)}")
        raise

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), 
       stop=stop_after_attempt(3))
def fetch_signal():
    try:
        response = requests.get(
            'https://api.tradingview.com/v1/signals',
            headers={'Authorization': f'Bearer {os.getenv("TRADINGVIEW_API_KEY")}'},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log_error(f"Signaal ophalen mislukt: {str(e)}")
        raise

@celery_app.task
def ai_process_news(news_data):
    response = requests.post(
        os.getenv('AI_NEWS_PROCESSOR_URL'),
        json=news_data,
        timeout=30
    )
    return response.json()

@celery_app.task
def ai_process_signal(signal):
    response = requests.post(
        os.getenv('AI_SIGNAL_PROCESSOR_URL'),
        json=signal,
        timeout=30
    )
    return response.json()

@celery_app.task
def match_subscribers(processed_data):
    subscribers = find_subscribers(processed_data)
    return {
        "count": len(subscribers),
        "details": processed_data
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    flask_app.run(host='0.0.0.0', port=port) 