"""
news_sources.py
===============
Official RSS feed registry for Paper Boy.
All feeds are from the publisher's own official RSS endpoints — verified,
trustworthy, and free to read.

Categories: World, Technology, Business, Markets, Science, India, Health, Sports
"""
from __future__ import annotations
from typing import Dict, List

# ------------------------------------------------------------------
# OFFICIAL NEWS RSS FEEDS
# Grouped by category. Each entry: (label, url)
# ------------------------------------------------------------------

FEEDS: Dict[str, List[tuple[str, str]]] = {

    "World": [
        # Global wire services & broadcasters
        ("BBC World News",           "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Reuters World",            "https://feeds.reuters.com/reuters/worldNews"),
        ("AP Top News",              "https://rsshub.app/apnews/topics/ap-top-news"),
        ("Al Jazeera English",       "https://www.aljazeera.com/xml/rss/all.xml"),
        ("The Guardian World",       "https://www.theguardian.com/world/rss"),
        ("France 24 (English)",      "https://www.france24.com/en/rss"),
        ("DW World News",            "https://rss.dw.com/rdf/rss-en-all"),
        ("VOA News",                 "https://www.voanews.com/api/zktgmtr-rss.xml"),
        ("NPR World",                "https://feeds.npr.org/1004/rss.xml"),
        ("ABC News Top Stories",     "https://feeds.abcnews.com/abcnews/topstories"),
    ],

    "Technology": [
        # Major tech publications
        ("TechCrunch",               "https://techcrunch.com/feed/"),
        ("The Verge",                "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica",             "https://feeds.arstechnica.com/arstechnica/index"),
        ("Wired",                    "https://www.wired.com/feed/rss"),
        ("MIT Technology Review",    "https://www.technologyreview.com/feed/"),
        ("BBC Technology",           "https://feeds.bbci.co.uk/news/technology/rss.xml"),
        ("Reuters Technology",       "https://feeds.reuters.com/reuters/technologyNews"),
        ("Hacker News (Top)",        "https://hnrss.org/frontpage"),
        ("VentureBeat AI",           "https://venturebeat.com/category/ai/feed/"),
        ("IEEE Spectrum",            "https://spectrum.ieee.org/feeds/feed.rss"),
        ("Google Blog",              "https://blog.google/rss/"),
        ("GitHub Blog",              "https://github.blog/feed/"),
    ],

    "Business": [
        # Finance & business outlets
        ("Reuters Business",         "https://feeds.reuters.com/reuters/businessNews"),
        ("BBC Business",             "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("The Guardian Business",    "https://www.theguardian.com/business/rss"),
        ("Financial Times (Free)",   "https://www.ft.com/rss/home/uk"),
        ("Bloomberg Markets",        "https://feeds.bloomberg.com/markets/news.rss"),
        ("Forbes Business",          "https://www.forbes.com/business/feed/"),
        ("Inc. Magazine",            "https://www.inc.com/rss/"),
        ("Fast Company",             "https://www.fastcompany.com/latest/rss?x=1"),
        ("Harvard Business Review",  "https://feeds.hbr.org/harvardbusiness"),
    ],

    "Markets": [
        # Financial market feeds
        ("Reuters Markets",          "https://feeds.reuters.com/reuters/UKmarkets"),
        ("Bloomberg Economy",        "https://feeds.bloomberg.com/economics/news.rss"),
        ("Yahoo Finance",            "https://finance.yahoo.com/news/rssindex"),
        ("Investing.com News",       "https://www.investing.com/rss/news.rss"),
        ("Seeking Alpha",            "https://seekingalpha.com/market-news/index.xml"),
        ("CNBC Finance",             "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
        ("MarketWatch",              "https://feeds.marketwatch.com/marketwatch/topstories/"),
        ("The Economist",            "https://www.economist.com/finance-and-economics/rss.xml"),
    ],

    "Science": [
        # Official science publishers
        ("NASA Breaking News",       "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
        ("NASA Image of the Day",    "https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss"),
        ("ScienceDaily Top",         "https://www.sciencedaily.com/rss/top.xml"),
        ("ScienceDaily Tech",        "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml"),
        ("Nature Latest",            "https://www.nature.com/nature.rss"),
        ("Science Magazine",         "https://www.sciencemag.org/rss/news_current.xml"),
        ("New Scientist",            "https://www.newscientist.com/feed/home/"),
        ("BBC Science",              "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
        ("Scientific American",      "https://rss.sciam.com/ScientificAmerican-Global"),
        ("ESA Space News",           "https://www.esa.int/rssfeed/Our_Activities/Space_Science"),
        ("SpaceX (Official Blog)",   "https://www.spacex.com/updates/index.xml"),
    ],

    "India": [
        # Indian national news
        ("NDTV India Top Stories",   "https://feeds.feedburner.com/ndtvnews-top-stories"),
        ("The Hindu National",       "https://www.thehindu.com/feeder/default.rss"),
        ("Times of India",           "https://timesofindia.indiatimes.com/rssfeedmostread.cms"),
        ("Economic Times",           "https://economictimes.indiatimes.com/rssfeedsdefault.cms"),
        ("Indian Express",           "https://indianexpress.com/feed/"),
        ("Hindustan Times",          "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"),
        ("Mint (Business India)",    "https://www.livemint.com/rss/news"),
        ("Business Standard",        "https://www.business-standard.com/rss/home_page_top_stories.rss"),
        ("Press Trust of India",     "https://feeds.feedburner.com/PTI-Story"),
    ],

    "Health": [
        ("WHO News",                 "https://www.who.int/rss-feeds/news-english.xml"),
        ("CDC Newsroom",             "https://tools.cdc.gov/api/v2/resources/media/403372.rss"),
        ("WebMD Health News",        "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC"),
        ("Reuters Health",           "https://feeds.reuters.com/reuters/healthNews"),
        ("BBC Health",               "https://feeds.bbci.co.uk/news/health/rss.xml"),
        ("Medical News Today",       "https://www.medicalnewstoday.com/rss"),
    ],

    "Sports": [
        ("ESPN Top Headlines",       "https://www.espn.com/espn/rss/news"),
        ("BBC Sport",                "https://feeds.bbci.co.uk/sport/rss.xml"),
        ("Reuters Sport",            "https://feeds.reuters.com/reuters/sportsNews"),
        ("Cricket (Cricbuzz)",       "https://www.cricbuzz.com/cricbuzz-ads-free-rss-feed"),
        ("NDTV Sports",              "https://feeds.feedburner.com/ndtvsports-latest"),
    ],

    "General": [
        ("Reuters Top News",         "https://feeds.reuters.com/reuters/topNews"),
        ("BBC Top Stories",          "https://feeds.bbci.co.uk/news/rss.xml"),
        ("NPR News",                 "https://feeds.npr.org/1001/rss.xml"),
        ("The Guardian",             "https://www.theguardian.com/international/rss"),
        ("Axios",                    "https://api.axios.com/feed/"),
        ("Politico",                 "https://www.politico.com/rss/politicopicks.xml"),
    ],
}


def get_all_feeds() -> List[tuple[str, str, str]]:
    """Return flat list of (category, label, url) for all feeds."""
    result = []
    for category, entries in FEEDS.items():
        for label, url in entries:
            result.append((category, label, url))
    return result


def get_feeds_for_category(category: str) -> List[tuple[str, str]]:
    """Return (label, url) list for a specific category."""
    return FEEDS.get(category, FEEDS.get("General", []))


def get_all_urls() -> List[str]:
    """Return just the URLs for all feeds."""
    return [url for entries in FEEDS.values() for _, url in entries]


# Total count helper
def feed_count() -> int:
    return sum(len(v) for v in FEEDS.values())
