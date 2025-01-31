import pytest
from unittest.mock import Mock
from .news_scraper import NewsScraper

def test_scraper_with_mock():
    mock_response = Mock()
    mock_response.content = """
        <div class="news-article">
            <h3 class="title">Test Title</h3>
            <div class="summary">Test summary</div>
            <time class="time">2023-07-20</time>
            <a href="/news/article1"></a>
        </div>
    """
    
    scraper = NewsScraper()
    results = scraper.parse_articles(mock_response.content)
    
    assert len(results) == 1
    assert results[0]['title'] == "Test Title" 