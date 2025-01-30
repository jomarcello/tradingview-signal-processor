# TradingView Signal Processor

This service processes trading signals from TradingView, enriches them with news and AI analysis, and distributes them to subscribers through Telegram.

## Features

- Trading signal processing and distribution
- Real-time news scraping from TradingView
- AI-powered signal analysis
- Subscriber matching and notification
- Technical chart generation
- System monitoring and health checks
- Proxy support for reliable scraping

## Architecture Improvements

1. **Code Organization**
   - Modular structure with separate components
   - Configuration management using environment variables
   - Clear separation of concerns

2. **Reliability**
   - Proxy rotation for stable scraping
   - Proper error handling and recovery
   - Request retries with backoff
   - System monitoring and health checks

3. **Security**
   - Environment-based configuration
   - SSL verification enabled
   - No hardcoded credentials
   - Proper API authentication

4. **Performance**
   - Async operations
   - Connection pooling
   - Resource cleanup
   - Optimized browser automation

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run the service:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080 --reload
   ```

## Environment Variables

Required environment variables:

- `SUPABASE_KEY`: Your Supabase API key
- `SIGNAL_AI_SERVICE_URL`: URL for the AI analysis service
- `NEWS_AI_SERVICE_URL`: URL for the news analysis service
- `SUBSCRIBER_MATCHER_URL`: URL for the subscriber matching service
- `TELEGRAM_SERVICE_URL`: URL for the Telegram service
- `CHART_SERVICE_URL`: URL for the chart service

Optional environment variables:

- `PROXY_URL`: Proxy service URL
- `PROXY_USERNAME`: Proxy service username
- `PROXY_PASSWORD`: Proxy service password
- `LOG_LEVEL`: Logging level (default: INFO)
- `ENABLE_MONITORING`: Enable system monitoring (default: true)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `REQUEST_TIMEOUT`: Request timeout in seconds (default: 60)

## API Endpoints

### POST /trading-signal
Process a new trading signal

Request body:
```json
{
    "instrument": "EURUSD",
    "action": "BUY",
    "price": 1.2345,
    "stoploss": 1.2300,
    "takeprofit": 1.2400,
    "timeframe": "1h",
    "strategy": "MA Crossover",
    "timestamp": "2024-01-30T12:00:00Z"
}
```

### GET /get-news
Get news articles for an instrument

Query parameters:
- `instrument`: Trading instrument (e.g., "EURUSD")

### GET /health
Get service health status

### GET /metrics
Get service metrics

## Monitoring

The service includes comprehensive monitoring:

- Request success/failure rates
- News scraping statistics
- System resource usage
- Error tracking
- Performance metrics

Access monitoring data through the `/metrics` endpoint.

## Error Handling

The service implements proper error handling:

- Request retries with exponential backoff
- Graceful degradation for non-critical failures
- Detailed error logging
- Error reporting through monitoring

## Development

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run tests:
   ```bash
   pytest
   ```

3. Format code:
   ```bash
   black .
   ```

4. Lint code:
   ```bash
   flake8
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License
