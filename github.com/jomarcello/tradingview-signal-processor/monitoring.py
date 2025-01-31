from prometheus_client import start_http_server, Counter, Gauge

REQUESTS_TOTAL = Counter('scrape_requests_total', 'Total scrape requests')
ERRORS_TOTAL = Counter('scrape_errors_total', 'Total scrape errors')
LATENCY = Gauge('scrape_latency_seconds', 'Scraping latency')

def monitor_performance(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        REQUESTS_TOTAL.inc()
        
        try:
            result = func(*args, **kwargs)
            latency = time.time() - start_time
            LATENCY.set(latency)
            return result
        except Exception as e:
            ERRORS_TOTAL.inc()
            raise
    return wrapper 