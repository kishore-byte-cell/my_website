import os

APP_TITLE = "Paper Boy | Global News Dispatch"
DB_PATH = "news.db"
CACHE_PATH = "cache.json"
CACHE_TTL = 3600  # 1 hour cache time-to-live in seconds
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
DEFAULT_LIMIT = 50

CATEGORIES = [
    "World",
    "Technology",
    "Business",
    "Markets",
    "Science",
    "General",
]

CATEGORY_PLACEHOLDER_IMAGES = {
    "World": "https://images.unsplash.com/photo-1526470608268-f674ce90ebd4?w=600&auto=format&fit=crop",
    "Technology": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&auto=format&fit=crop",
    "Business": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&auto=format&fit=crop",
    "Markets": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&auto=format&fit=crop",
    "Science": "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=600&auto=format&fit=crop",
    "General": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=600&auto=format&fit=crop",
}
