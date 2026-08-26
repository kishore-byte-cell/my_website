def categorize_article(title, summary=""):
    title_lower = title.lower()
    if any(k in title_lower for k in ["gold", "rate", "dollar", "inr", "stock", "market"]):
        return "Market & Economy"
    return "Global News"
