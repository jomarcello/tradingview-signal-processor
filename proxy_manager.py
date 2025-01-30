import os
import logging
import aiohttp
import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        self.proxy_url = os.getenv('PROXY_URL')
        self.proxy_username = os.getenv('PROXY_USERNAME')
        self.proxy_password = os.getenv('PROXY_PASSWORD')
        
        # Proxy pool management
        self.proxy_pool = []
        self.last_refresh = None
        self.refresh_interval = timedelta(minutes=30)
        self.max_retries = 3
        self.current_proxy = None
        
    async def initialize(self) -> None:
        """Initialize the proxy manager and fetch initial proxies"""
        if not all([self.proxy_url, self.proxy_username, self.proxy_password]):
            logger.warning("Proxy configuration not complete. Running without proxies.")
            return
            
        await self.refresh_proxy_pool()
        
    async def refresh_proxy_pool(self) -> None:
        """Refresh the pool of available proxies"""
        try:
            if not all([self.proxy_url, self.proxy_username, self.proxy_password]):
                return
                
            # Basic proxy rotation using the main proxy with different ports
            base_ports = [8000, 8001, 8002, 8003, 8004]
            self.proxy_pool = []
            
            for port in base_ports:
                proxy_config = {
                    'server': f"{self.proxy_url.split(':')[0]}:{port}",
                    'username': self.proxy_username,
                    'password': self.proxy_password
                }
                
                # Test the proxy
                if await self.test_proxy(proxy_config):
                    self.proxy_pool.append(proxy_config)
                    
            self.last_refresh = datetime.now()
            logger.info(f"Refreshed proxy pool. {len(self.proxy_pool)} working proxies available.")
            
        except Exception as e:
            logger.error(f"Error refreshing proxy pool: {str(e)}")
            
    async def test_proxy(self, proxy_config: Dict[str, str]) -> bool:
        """Test if a proxy is working"""
        try:
            proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['server']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.ipify.org?format=json',
                    proxy=proxy_url,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        return True
            return False
            
        except Exception as e:
            logger.debug(f"Proxy test failed: {str(e)}")
            return False
            
    async def get_proxy(self) -> Optional[Dict[str, str]]:
        """Get a working proxy from the pool"""
        try:
            if not self.proxy_pool:
                if not await self.should_use_proxies():
                    return None
                await self.refresh_proxy_pool()
                if not self.proxy_pool:
                    return None
                    
            # Check if we need to refresh the pool
            if self.last_refresh and datetime.now() - self.last_refresh > self.refresh_interval:
                await self.refresh_proxy_pool()
                
            # Rotate through proxies
            if self.proxy_pool:
                self.current_proxy = random.choice(self.proxy_pool)
                return self.current_proxy
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting proxy: {str(e)}")
            return None
            
    async def should_use_proxies(self) -> bool:
        """Determine if proxies should be used"""
        return all([self.proxy_url, self.proxy_username, self.proxy_password])
        
    async def mark_proxy_failed(self, proxy_config: Dict[str, str]) -> None:
        """Mark a proxy as failed and remove it from the pool"""
        try:
            if proxy_config in self.proxy_pool:
                self.proxy_pool.remove(proxy_config)
                logger.warning(f"Removed failed proxy: {proxy_config['server']}")
                
            # Refresh pool if running low on proxies
            if len(self.proxy_pool) < 2:
                await self.refresh_proxy_pool()
                
        except Exception as e:
            logger.error(f"Error marking proxy as failed: {str(e)}")
            
    async def get_working_proxy(self, max_attempts: int = 3) -> Optional[Dict[str, str]]:
        """Get a working proxy with retry logic"""
        for attempt in range(max_attempts):
            proxy = await self.get_proxy()
            if not proxy:
                return None
                
            if await self.test_proxy(proxy):
                return proxy
                
            await self.mark_proxy_failed(proxy)
            await asyncio.sleep(1)
            
        return None
        
    def get_proxy_url(self, proxy_config: Dict[str, str]) -> str:
        """Convert proxy config to URL format"""
        if not proxy_config:
            return None
            
        return f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['server']}"
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.proxy_pool = []
        self.current_proxy = None
        logger.info("Proxy manager cleaned up")

# Create singleton instance
proxy_manager = ProxyManager()