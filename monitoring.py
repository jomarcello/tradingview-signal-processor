import logging
import os
import time
import psutil
import asyncio
from typing import Dict, Any
from datetime import datetime
from logging.handlers import RotatingFileHandler

class ServiceMonitor:
    def __init__(self):
        self.logger = self._setup_logger()
        self.metrics = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_failed': 0,
            'news_articles_scraped': 0,
            'signals_processed': 0,
            'last_error': None,
            'start_time': datetime.now().isoformat()
        }
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        logger = logging.getLogger('service_monitor')
        logger.setLevel(log_level)

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            'logs/service.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def log_request(self, success: bool = True) -> None:
        """Log a request and update metrics"""
        self.metrics['requests_total'] += 1
        if success:
            self.metrics['requests_success'] += 1
        else:
            self.metrics['requests_failed'] += 1

    def log_news_scrape(self, count: int) -> None:
        """Log news articles scraped"""
        self.metrics['news_articles_scraped'] += count

    def log_signal_processed(self) -> None:
        """Log a processed signal"""
        self.metrics['signals_processed'] += 1

    def log_error(self, error: str) -> None:
        """Log an error"""
        self.metrics['last_error'] = {
            'message': str(error),
            'timestamp': datetime.now().isoformat()
        }
        self.logger.error(error)

    async def monitor_system_resources(self) -> None:
        """Monitor system resources periodically"""
        while True:
            try:
                process = psutil.Process()
                
                # Get system metrics
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_percent = process.memory_percent()
                
                # Log system metrics
                self.logger.info(
                    f"System Metrics - CPU: {cpu_percent}%, "
                    f"Memory: {memory_info.rss / 1024 / 1024:.2f}MB ({memory_percent:.1f}%)"
                )
                
                # Check for high resource usage
                if cpu_percent > 80:
                    self.logger.warning(f"High CPU usage detected: {cpu_percent}%")
                if memory_percent > 80:
                    self.logger.warning(f"High memory usage detected: {memory_percent}%")
                
            except Exception as e:
                self.logger.error(f"Error monitoring system resources: {str(e)}")
            
            await asyncio.sleep(60)  # Monitor every minute

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        metrics = self.metrics.copy()
        
        # Add system metrics
        try:
            process = psutil.Process()
            metrics.update({
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'uptime_seconds': (datetime.now() - datetime.fromisoformat(metrics['start_time'])).total_seconds()
            })
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {str(e)}")
            
        return metrics

    def get_health(self) -> Dict[str, Any]:
        """Get service health status"""
        metrics = self.get_metrics()
        
        # Calculate error rate
        total_requests = metrics['requests_total']
        error_rate = (metrics['requests_failed'] / total_requests * 100) if total_requests > 0 else 0
        
        # Determine status based on metrics
        status = 'healthy'
        if error_rate > 10:
            status = 'degraded'
        if error_rate > 50:
            status = 'unhealthy'
        if metrics['cpu_percent'] > 90 or metrics['memory_percent'] > 90:
            status = 'resource_critical'
            
        return {
            'status': status,
            'error_rate': f"{error_rate:.2f}%",
            'last_error': metrics['last_error'],
            'uptime': f"{metrics['uptime_seconds'] / 3600:.2f} hours",
            'metrics': metrics
        }

# Create singleton instance
monitor = ServiceMonitor()