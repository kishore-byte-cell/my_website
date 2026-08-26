"""
importance.py
=============
Calculates an importance/urgency score for a news article.
Score is 0.0 – 10.0. Higher = more important/breaking.
"""
from __future__ import annotations
import re
from typing import Dict, Any

BREAKING_KEYWORDS = [
    "breaking", "urgent", "alert", "exclusive", "developing",
    "war", "attack", "crisis", "emergency", "disaster", "killed",
    "dead", "explosion", "crash", "collapse", "earthquake", "flood",
    "election", "resign", "arrest", "impeach", "sanction", "ban",
    "ai", "artificial intelligence", "breakthrough", "record", "first ever",
    "billion", "trillion", "inflation", "recession", "rate hike", "rate cut",
    "nasa", "isro", "space", "launch", "orbit",
]

HIGH_IMPORTANCE_SOURCES = {
    "reuters", "bbc", "ap news", "associated press", "bloomberg",
    "the guardian", "financial times", "al jazeera", "ndtv", "the hindu",
}


def calculate_importance(article: Dict[str, Any]) -> float:
    """
    Calculate an importance score (0–10) for an article dict.
    Considers title keywords, source credibility, and recency signals.
    """
    score = 5.0

    title   = (article.get("title", "") or "").lower()
    summary = (article.get("summary", "") or "").lower()
    source  = (article.get("source", "") or "").lower()
    text    = title + " " + summary

    # Keyword boost
    matched = sum(1 for kw in BREAKING_KEYWORDS if kw in text)
    score += min(matched * 0.6, 3.0)

    # Source credibility boost
    if any(s in source for s in HIGH_IMPORTANCE_SOURCES):
        score += 0.8

    # Title length heuristic — very short = clickbait, very long = niche
    words = len(title.split())
    if 6 <= words <= 14:
        score += 0.3

    # Cap
    return round(min(score, 10.0), 2)


# Alias so both call styles work
calculate_importance_score = calculate_importance
