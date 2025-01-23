# TradingView Signal Processor

A FastAPI service that processes TradingView signals, enriches them with news data and sentiment analysis, and forwards them to n8n.

## Features

- Receives trading signals from TradingView
- Scrapes latest news for the trading pair
- Performs sentiment analysis on the news
- Forwards enriched data to n8n for further processing

## API Endpoints

### POST `/trading-signal`

Receives trading signals and processes them.

Example request:
```json
{
    "instrument": "EURUSD",
    "action": "buy",
    "price": 1.2345,
    "timestamp": "2025-01-23T10:30:00Z"
}
```

Example response:
```json
{
    "status": "success",
    "message": "Signal processed and sent to n8n",
    "data": {
        "signal": {
            "instrument": "EURUSD",
            "action": "buy",
            "price": 1.2345,
            "timestamp": "2025-01-23T10:30:00Z"
        },
        "news": {
            "title": "EUR/USD rises on positive economic data",
            "content": "The EUR/USD pair showed strength today...",
            "url": "https://www.tradingview.com/news/..."
        },
        "sentiment": {
            "score": 0.75,
            "label": "bullish",
            "bullish_words": 3,
            "bearish_words": 1
        }
    }
}
```

### GET `/health`

Health check endpoint.

## Setup

1. Copy `.env.example` to `.env` and fill in your n8n webhook URL:
```bash
cp .env.example .env
```

2. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

3. Run the server:
```bash
uvicorn main:app --reload
```

## Deployment

This project is set up for deployment on Railway.app through GitHub integration.

## Environment Variables

- `N8N_WEBHOOK_URL`: Your n8n webhook URL where the processed data should be sent
