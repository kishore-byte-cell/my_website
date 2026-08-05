import json
import time
import os
import config
from fetch_news import fetch_all_feeds

def load_cache():
    """Load cached articles from cache.json if valid and not expired."""
    if not os.path.exists(config.CACHE_PATH):
        return None

    try:
        with open(config.CACHE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        timestamp = data.get('timestamp', 0)
        current_time = time.time()

        # Check if cache is within TTL
        if current_time - timestamp < config.CACHE_TTL:
            return data.get('articles', [])
    except Exception as e:
        print(f"Error loading cache: {e}")

    return None

def save_cache(articles):
    """Save articles list to cache.json with current timestamp."""
    try:
        data = {
            'timestamp': time.time(),
            'count': len(articles),
            'articles': articles
        }
        with open(config.CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

def clear_cache():
    """Safely clear the persisted cache file and keep a clean empty cache state."""
    try:
        if os.path.exists(config.CACHE_PATH):
            os.remove(config.CACHE_PATH)
        save_cache([])
        return True
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return False


def get_news_with_cache(force_refresh=False):
    """Retrieve news articles from cache or trigger fresh fetch if expired/forced."""
    if not force_refresh:
        cached_articles = load_cache()
        if cached_articles is not None:
            return cached_articles, False  # (articles, is_fresh_fetch)

    # Perform fresh fetch
    articles = fetch_all_feeds()
    save_cache(articles)
    return articles, True
