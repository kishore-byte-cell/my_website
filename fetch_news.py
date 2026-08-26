"""
fetch_news.py
=============
RSS feed fetcher for Paper Boy — parallel fetch using ThreadPoolExecutor.
Feeds are fetched concurrently (not sequentially) so 60 feeds takes the
time of the SLOWEST single feed, not 60× a single feed.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

import news_sources

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class FeedRateLimiter:
    def __init__(self, cooldown_seconds: float = 10.0):
        self.cooldown_seconds = cooldown_seconds
        self.last_fetch_time = 0.0

    def is_allowed(self) -> bool:
        current_time = time.time()
        if current_time - self.last_fetch_time >= self.cooldown_seconds:
            self.last_fetch_time = current_time
            return True
        return False

    def seconds_until_reset(self) -> float:
        remaining = self.cooldown_seconds - (time.time() - self.last_fetch_time)
        return max(0.0, remaining)

    def acquire(self, url: str):
        pass


feed_rate_limiter = FeedRateLimiter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

FEED_TIMEOUT_SECS = 4       # per-feed HTTP timeout
MAX_ARTICLES_PER_FEED = 6   # articles kept per feed
MAX_FEEDS_PER_RUN = 40      # cap to avoid overwhelming on refresh
MAX_WORKERS = 20            # parallel threads

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    """Create a requests.Session with retry + connection pool."""
    if requests is None:
        return None
    sess = requests.Session()
    retry = Retry(total=1, backoff_factor=0.2, status_forcelist=[500, 502, 503])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    sess.headers.update(HEADERS)
    return sess


def _parse_date(entry) -> str:
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6]).strftime("%Y-%m-%dT%H:%M:%S")
            except Exception:
                pass
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _extract_image(entry) -> str:
    # media:thumbnail
    media_thumb = getattr(entry, "media_thumbnail", None)
    if media_thumb and isinstance(media_thumb, list) and media_thumb:
        url = media_thumb[0].get("url", "")
        if url:
            return url
    # media:content
    media_content = getattr(entry, "media_content", None)
    if media_content and isinstance(media_content, list) and media_content:
        url = media_content[0].get("url", "")
        if url:
            return url
    # enclosures
    for enc in getattr(entry, "enclosures", []):
        if "image" in enc.get("type", ""):
            return enc.get("href", "")
    # img in summary
    summary = getattr(entry, "summary", "") or ""
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
    if match:
        return match.group(1)
    return ""


def _fetch_single_feed(
    session,
    category: str,
    label: str,
    url: str,
) -> List[Dict[str, Any]]:
    """Fetch one feed. Runs inside a thread from the pool."""
    articles = []
    if feedparser is None:
        return articles
    try:
        if session is not None:
            resp = session.get(url, timeout=FEED_TIMEOUT_SECS)
            if resp.status_code != 200:
                return articles
            parsed = feedparser.parse(resp.content)
        else:
            parsed = feedparser.parse(url)

        for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
            title = getattr(entry, "title", "").strip()
            link  = getattr(entry, "link", "").strip()
            if not title or not link:
                continue

            summary = (
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or ""
            )
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

            articles.append({
                "title":            title,
                "link":             link,
                "summary":          summary,
                "source":           label,
                "category":         category,
                "published":        _parse_date(entry),
                "media_url":        _extract_image(entry),
                "importance_score": 5.0,
            })
    except Exception as e:
        pass  # silently skip unavailable feeds

    return articles


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def fetch_all_feeds(categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Fetch articles from all official RSS feeds IN PARALLEL.

    Args:
        categories: Optional list of category names to filter.
                    If None, fetches from all categories.

    Returns:
        Deduplicated list of article dicts.
    """
    # Build feed list
    if categories:
        feed_list = []
        for cat in categories:
            for label, url in news_sources.get_feeds_for_category(cat):
                feed_list.append((cat, label, url))
    else:
        feed_list = news_sources.get_all_feeds()

    # Cap total feeds
    feed_list = feed_list[:MAX_FEEDS_PER_RUN]

    session = _make_session()
    all_articles: List[Dict[str, Any]] = []
    seen_links: set = set()

    # --- Parallel fetch using thread pool ---
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {
            executor.submit(_fetch_single_feed, session, cat, label, url): (cat, label)
            for cat, label, url in feed_list
        }
        for future in as_completed(future_map):
            try:
                articles = future.result()
                for art in articles:
                    if art["link"] not in seen_links:
                        seen_links.add(art["link"])
                        all_articles.append(art)
            except Exception:
                pass

    if session:
        session.close()

    print(f"[FeedFetch] {len(all_articles)} articles from {len(feed_list)} feeds (parallel).")
    return all_articles
