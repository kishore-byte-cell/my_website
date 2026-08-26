from typing import Any, Dict, List
import sqlite_db


def rank_articles_for_user(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank articles based on user interest scores and importance score."""
    if not articles:
        return []

    try:
        if hasattr(sqlite_db, "get_user_interests"):
            interests = sqlite_db.get_user_interests()
        else:
            interests = {}
    except Exception:
        interests = {}

    def score_article(art: Dict[str, Any]) -> float:
        cat = art.get("category", "")
        base_score = float(art.get("importance_score", 5.0) or 5.0)
        boost = float(interests.get(cat, 0)) * 0.5
        return base_score + boost

    return sorted(articles, key=score_article, reverse=True)


def get_recommended_articles(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve top recommended articles for the user."""
    articles = sqlite_db.get_articles(limit=limit) if hasattr(sqlite_db, "get_articles") else []
    return rank_articles_for_user(articles)[:limit]
