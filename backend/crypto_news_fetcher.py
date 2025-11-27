"""
Crypto News Fetcher - Sichere Webzugriffe zu Kryptoportalen
Mit Whitelist, Rate Limiting und Content Filtering gegen Spam/Fake News
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict
import httpx
from bs4 import BeautifulSoup
import feedparser

logger = logging.getLogger(__name__)

# Whitelist für vertrauenswürdige Krypto-News-Quellen
TRUSTED_SOURCES = {
    "coindesk.com": {
        "name": "CoinDesk",
        "rss": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "enabled": True,
        "reliability_score": 0.95
    },
    "cointelegraph.com": {
        "name": "CoinTelegraph",
        "rss": "https://cointelegraph.com/rss",
        "enabled": True,
        "reliability_score": 0.90
    },
    "cryptoslate.com": {
        "name": "CryptoSlate",
        "rss": "https://cryptoslate.com/feed/",
        "enabled": True,
        "reliability_score": 0.85
    },
    "decrypt.co": {
        "name": "Decrypt",
        "rss": "https://decrypt.co/feed",
        "enabled": True,
        "reliability_score": 0.88
    },
    "theblock.co": {
        "name": "The Block",
        "rss": "https://www.theblock.co/rss.xml",
        "enabled": True,
        "reliability_score": 0.87
    }
}

# Spam/Fake News Keywords (Blacklist)
SPAM_KEYWORDS = [
    r'\b(guaranteed|guarantee|100%|guaranteed profit|risk-free|free money|get rich quick)\b',
    r'\b(pump|dump|pump and dump|pump group|telegram pump)\b',
    r'\b(click here|limited time|act now|urgent|immediate action)\b',
    r'\b(crypto giveaway|free crypto|airdrop scam|fake airdrop)\b',
    r'\b(ponzi|pyramid|mlm|multi-level marketing)\b',
    r'\b(secret method|hidden strategy|insider secret)\b'
]

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE = 10
RATE_LIMIT_WINDOW_SECONDS = 60

class CryptoNewsFetcher:
    """Sicherer News-Fetcher mit Whitelist, Rate Limiting und Content Filtering."""
    
    def __init__(self):
        self.rate_limit_tracker = defaultdict(list)
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl_seconds = 300  # 5 minutes cache
        self.http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
    
    def _check_rate_limit(self, source: str) -> bool:
        """Prüft ob Rate Limit für eine Quelle erreicht wurde."""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS
        
        # Clean old entries
        self.rate_limit_tracker[source] = [
            timestamp for timestamp in self.rate_limit_tracker[source]
            if timestamp > window_start
        ]
        
        # Check limit
        if len(self.rate_limit_tracker[source]) >= RATE_LIMIT_REQUESTS_PER_MINUTE:
            logger.warning(f"Rate limit reached for {source}")
            return False
        
        # Add current request
        self.rate_limit_tracker[source].append(now)
        return True
    
    def _is_spam_or_fake(self, title: str, content: str) -> bool:
        """Prüft ob ein Artikel Spam oder Fake News enthält."""
        text = f"{title} {content}".lower()
        
        # Check for spam keywords
        for pattern in SPAM_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Spam detected: {pattern} in title/content")
                return True
        
        # Check for excessive capitalization (common in spam)
        if len(re.findall(r'[A-Z]{3,}', title)) > 3:
            logger.warning(f"Excessive capitalization detected in title: {title}")
            return True
        
        # Check for suspicious patterns
        if re.search(r'[!]{2,}', title):  # Multiple exclamation marks
            logger.warning(f"Multiple exclamation marks in title: {title}")
            return True
        
        return False
    
    def _extract_article_content(self, html: str) -> str:
        """Extrahiert den Hauptinhalt aus HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Try to find main content
            main_content = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile(r'content|article|post'))
            
            if main_content:
                # Get text and clean it
                text = main_content.get_text(separator=' ', strip=True)
                # Remove excessive whitespace
                text = re.sub(r'\s+', ' ', text)
                return text[:2000]  # Limit to 2000 chars
            
            # Fallback: get all text
            text = soup.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text[:2000]
        
        except Exception as e:
            logger.error(f"Error extracting article content: {e}")
            return ""
    
    async def fetch_rss_feed(self, source_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Lädt News von einer RSS-Feed-Quelle."""
        if source_key not in TRUSTED_SOURCES:
            logger.error(f"Source {source_key} not in whitelist")
            return []
        
        source_info = TRUSTED_SOURCES[source_key]
        if not source_info.get("enabled", True):
            logger.warning(f"Source {source_key} is disabled")
            return []
        
        # Check rate limit
        if not self._check_rate_limit(source_key):
            logger.warning(f"Rate limit exceeded for {source_key}")
            return []
        
        try:
            rss_url = source_info["rss"]
            logger.info(f"Fetching RSS feed from {source_key}: {rss_url}")
            
            # Fetch RSS feed
            response = await self.http_client.get(rss_url)
            response.raise_for_status()
            
            # Parse RSS
            feed = feedparser.parse(response.text)
            
            articles = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")
                summary = entry.get("summary", "")
                
                # Check for spam/fake news
                if self._is_spam_or_fake(title, summary):
                    logger.info(f"Filtered spam/fake article: {title}")
                    continue
                
                # Parse published date
                published_date = None
                if published:
                    try:
                        published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except:
                        pass
                
                article = {
                    "title": title,
                    "link": link,
                    "summary": summary[:500],  # Limit summary
                    "published": published_date.isoformat() if published_date else published,
                    "source": source_info["name"],
                    "source_key": source_key,
                    "reliability_score": source_info.get("reliability_score", 0.5),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                }
                
                articles.append(article)
            
            logger.info(f"Fetched {len(articles)} articles from {source_key}")
            return articles
        
        except Exception as e:
            logger.error(f"Error fetching RSS feed from {source_key}: {e}")
            return []
    
    async def fetch_news(self, 
                         sources: Optional[List[str]] = None,
                         limit_per_source: int = 5,
                         max_total: int = 20,
                         symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Lädt News von mehreren vertrauenswürdigen Quellen.
        
        Args:
            sources: Liste von Source-Keys (None = alle aktivierten Quellen)
            limit_per_source: Max. Artikel pro Quelle
            max_total: Max. Gesamtanzahl Artikel
            symbols: Optional: Filter für spezifische Kryptowährungen (z.B. ["BTC", "ETH"])
        """
        if sources is None:
            sources = [
                key for key, info in TRUSTED_SOURCES.items()
                if info.get("enabled", True)
            ]
        
        all_articles = []
        
        # Fetch from all sources
        for source_key in sources:
            articles = await self.fetch_rss_feed(source_key, limit=limit_per_source)
            all_articles.extend(articles)
            
            # Check if we have enough
            if len(all_articles) >= max_total:
                break
        
        # Sort by published date (newest first)
        all_articles.sort(
            key=lambda x: x.get("published", ""),
            reverse=True
        )
        
        # Filter by symbols if provided
        if symbols:
            filtered_articles = []
            symbol_patterns = [re.compile(rf'\b{symbol}\b', re.IGNORECASE) for symbol in symbols]
            
            for article in all_articles:
                title = article.get("title", "")
                summary = article.get("summary", "")
                text = f"{title} {summary}"
                
                # Check if any symbol matches
                if any(pattern.search(text) for pattern in symbol_patterns):
                    filtered_articles.append(article)
            
            all_articles = filtered_articles[:max_total]
        else:
            all_articles = all_articles[:max_total]
        
        logger.info(f"Fetched {len(all_articles)} total articles")
        return all_articles
    
    async def search_news(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Sucht nach News-Artikeln basierend auf einem Query."""
        # Fetch recent news
        all_articles = await self.fetch_news(max_total=50)
        
        # Simple keyword matching
        query_lower = query.lower()
        query_words = query_lower.split()
        
        matching_articles = []
        for article in all_articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()
            text = f"{title} {summary}"
            
            # Score based on keyword matches
            score = sum(1 for word in query_words if word in text)
            if score > 0:
                article["relevance_score"] = score / len(query_words)
                matching_articles.append(article)
        
        # Sort by relevance
        matching_articles.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return matching_articles[:limit]
    
    def get_available_sources(self) -> List[Dict[str, Any]]:
        """Gibt eine Liste aller verfügbaren Quellen zurück."""
        return [
            {
                "key": key,
                "name": info["name"],
                "enabled": info.get("enabled", True),
                "reliability_score": info.get("reliability_score", 0.5)
            }
            for key, info in TRUSTED_SOURCES.items()
        ]
    
    def _evaluate_news_importance(self, article: Dict[str, Any]) -> float:
        """
        Bewertet die Wichtigkeit einer News für Trading-Entscheidungen.
        Returns: Score 0.0-1.0 (höher = wichtiger)
        """
        score = 0.0
        title = article.get("title", "").lower()
        summary = article.get("summary", "").lower()
        text = f"{title} {summary}"
        
        # Wichtige Keywords für Trading
        high_importance_keywords = [
            r'\b(regulation|regulatory|sec|sec lawsuit|sec approval|government|ban|legal)\b',
            r'\b(etf|exchange traded fund|spot etf|bitcoin etf|approval|rejection)\b',
            r'\b(hack|exploit|security breach|stolen|compromised)\b',
            r'\b(major|breakthrough|milestone|all-time high|all time high|ath)\b',
            r'\b(partnership|integration|adoption|institutional|whale|whale movement)\b',
            r'\b(upgrade|hard fork|soft fork|network upgrade|consensus)\b',
            r'\b(crash|flash crash|market crash|correction|bear market)\b',
            r'\b(bull run|bull market|rally|surge|breakout)\b',
            r'\b(halving|halvening|supply|mining reward)\b',
            r'\b(central bank|cbdc|digital currency|monetary policy)\b'
        ]
        
        # Mittlere Wichtigkeit
        medium_importance_keywords = [
            r'\b(listing|delisting|exchange|binance|coinbase)\b',
            r'\b(partnership|collaboration|integration)\b',
            r'\b(update|release|launch|announcement)\b',
            r'\b(price|valuation|market cap)\b'
        ]
        
        # Zähle Matches
        high_matches = sum(1 for pattern in high_importance_keywords if re.search(pattern, text, re.IGNORECASE))
        medium_matches = sum(1 for pattern in medium_importance_keywords if re.search(pattern, text, re.IGNORECASE))
        
        # Berechne Score
        score += high_matches * 0.3  # Jedes High-Importance Keyword = +0.3
        score += medium_matches * 0.1  # Jedes Medium-Importance Keyword = +0.1
        
        # Reliability Score der Quelle
        reliability = article.get("reliability_score", 0.5)
        score += reliability * 0.2  # Quelle-Qualität = bis zu +0.2
        
        # Cap bei 1.0
        return min(score, 1.0)
    
    def filter_important_news(self, articles: List[Dict[str, Any]], min_importance: float = 0.4) -> List[Dict[str, Any]]:
        """
        Filtert News nach Wichtigkeit.
        
        Args:
            articles: Liste von News-Artikeln
            min_importance: Mindest-Importance-Score (0.0-1.0)
        
        Returns:
            Gefilterte Liste mit Importance-Score
        """
        important_articles = []
        
        for article in articles:
            importance = self._evaluate_news_importance(article)
            article["importance_score"] = importance
            
            if importance >= min_importance:
                important_articles.append(article)
        
        # Sortiere nach Importance (höchste zuerst)
        important_articles.sort(key=lambda x: x.get("importance_score", 0.0), reverse=True)
        
        return important_articles
    
    async def close(self):
        """Schließt HTTP-Client."""
        await self.http_client.aclose()

# Global instance
_news_fetcher_instance: Optional[CryptoNewsFetcher] = None

def get_news_fetcher() -> CryptoNewsFetcher:
    """Gibt die globale News-Fetcher-Instanz zurück."""
    global _news_fetcher_instance
    if _news_fetcher_instance is None:
        _news_fetcher_instance = CryptoNewsFetcher()
    return _news_fetcher_instance

