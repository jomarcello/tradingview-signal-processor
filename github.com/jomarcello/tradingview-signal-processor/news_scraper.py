from bs4 import BeautifulSoup
import fake_useragent

class NewsScraper:
    def __init__(self):
        self.user_agent = fake_useragent.UserAgent()
        self.proxy_rotator = ProxyRotator()
    
    def scrape_articles(self, asset: str) -> list:
        headers = {'User-Agent': self.user_agent.random}
        try:
            response = requests.get(
                f'https://www.tradingview.com/news/{asset}/',
                proxies=self.proxy_rotator.get_proxy(),
                headers=headers,
                timeout=15
            )
            return self.parse_articles(response.content)
        except Exception as e:
            log_error(f"Scrape error for {asset}: {str(e)}")
            return []

    def parse_articles(self, html: str) -> list:
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        for article in soup.select('.news-article'):
            articles.append({
                'title': article.select_one('.title').text.strip(),
                'summary': article.select_one('.summary').text.strip(),
                'timestamp': parse_timestamp(article.select_one('.time').text),
                'url': article.find('a')['href']
            })
        return articles 