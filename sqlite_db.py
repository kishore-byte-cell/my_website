import sqlite3
import config
from datetime import datetime, timezone

def get_connection():
    """Create SQLite database connection."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables and indexes."""
    conn = get_connection()
    cursor = conn.cursor()

    # Articles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            source TEXT NOT NULL,
            category TEXT NOT NULL,
            published TEXT,
            media_url TEXT,
            importance_score REAL DEFAULT 5.0,
            bookmarked INTEGER DEFAULT 0,
            read_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # User interests / personalization table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_interests (
            category TEXT PRIMARY KEY,
            click_count INTEGER DEFAULT 0,
            last_interacted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Market intelligence schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_spot_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_name TEXT NOT NULL,
            market_month TEXT NOT NULL,
            close_price REAL NOT NULL,
            source TEXT DEFAULT 'Live spot market API',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asset_name, market_month)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_forecast_ranges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_name TEXT NOT NULL,
            forecast_month TEXT NOT NULL,
            range_low REAL,
            range_high REAL,
            source TEXT,
            headline TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asset_name, forecast_month)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_headlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_name TEXT NOT NULL,
            source TEXT NOT NULL,
            headline TEXT NOT NULL,
            summary TEXT,
            published_at TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asset_name, source, headline)
        );
    """)

    # Create Indexes for fast querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON articles(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_published ON articles(published);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarked ON articles(bookmarked);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_asset ON market_spot_prices(asset_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_range_asset ON market_forecast_ranges(asset_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_headline_asset ON market_headlines(asset_name);")

    conn.commit()
    conn.close()

def upsert_articles(articles):
    """
    Insert or update articles using link as unique key.
    Preserves bookmark status if article already exists.
    """
    conn = get_connection()
    cursor = conn.cursor()

    for article in articles:
        cursor.execute("""
            INSERT INTO articles (link, title, summary, source, category, published, media_url, importance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(link) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                media_url = excluded.media_url,
                importance_score = excluded.importance_score,
                published = excluded.published;
        """, (
            article['link'],
            article['title'],
            article.get('summary', ''),
            article.get('source', 'Unknown'),
            article.get('category', 'World'),
            article.get('published', ''),
            article.get('media_url', ''),
            article.get('importance_score', 5.0)
        ))

    conn.commit()
    conn.close()

def get_articles(category=None, search_query=None, bookmarked_only=False, limit=50, sort_by="published"):
    """Query articles from database with optional filters and sorting."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if bookmarked_only:
        query += " AND bookmarked = 1"

    if search_query:
        query += " AND (title LIKE ? OR summary LIKE ? OR source LIKE ?)"
        pattern = f"%{search_query}%"
        params.extend([pattern, pattern, pattern])

    if sort_by == "importance":
        query += " ORDER BY importance_score DESC, published DESC"
    else:
        query += " ORDER BY published DESC"

    query += " LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def toggle_bookmark(article_link):
    """Toggle bookmarked status for an article."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT bookmarked FROM articles WHERE link = ?", (article_link,))
    row = cursor.fetchone()
    if row:
        new_status = 0 if row['bookmarked'] == 1 else 1
        cursor.execute("UPDATE articles SET bookmarked = ? WHERE link = ?", (new_status, article_link))
        conn.commit()
        conn.close()
        return new_status

    conn.close()
    return 0

def increment_category_interest(category):
    """Record user interaction to boost category recommendations."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_interests (category, click_count, last_interacted)
        VALUES (?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(category) DO UPDATE SET
            click_count = click_count + 1,
            last_interacted = CURRENT_TIMESTAMP;
    """, (category,))
    conn.commit()
    conn.close()

def get_category_analytics():
    """Retrieve article counts grouped by category."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category, COUNT(*) as count FROM articles GROUP BY category ORDER BY count DESC;")
    rows = cursor.fetchall()
    conn.close()
    return {row['category']: row['count'] for row in rows}

def get_source_analytics():
    """Retrieve article counts grouped by source."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT source, COUNT(*) as count FROM articles GROUP BY source ORDER BY count DESC LIMIT 10;")
    rows = cursor.fetchall()
    conn.close()
    return {row['source']: row['count'] for row in rows}
