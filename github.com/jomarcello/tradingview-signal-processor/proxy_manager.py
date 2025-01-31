import random
from typing import Dict

class ProxyRotator:
    def __init__(self):
        self.proxies = [
            'http://proxy1:port',
            'http://proxy2:port',
            'http://proxy3:port'
        ]
        self.current = 0
    
    def get_proxy(self) -> Dict[str, str]:
        proxy = {'http': self.proxies[self.current]}
        self.current = (self.current + 1) % len(self.proxies)
        return proxy

    def add_proxy(self, proxy: str):
        if proxy not in self.proxies:
            self.proxies.append(proxy) 