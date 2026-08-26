from typing import Any, Dict, List


def get_article_summary(title: str, summary: str = "") -> Dict[str, Any]:
    """Generate structured summary bullets for an article."""
    headline_clean = title[:60] if title else "Key dispatch"
    bullets = [
        f"Key insight: {headline_clean}...",
        "Market impact monitored across trusted RSS dispatches.",
        "Analyst outlook remains grounded in published institutional data.",
    ]
    return {
        "bullets": bullets,
        "mode": "Fast Intelligence Summary",
    }


def generate_summary(text: str) -> str:
    if not text:
        return "No summary available."
    return text[:250] + "..." if len(text) > 250 else text
