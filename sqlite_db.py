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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            posted_date TEXT,
            stipend_salary TEXT DEFAULT 'Not Disclosed',
            suitability_score INTEGER DEFAULT 0,
            match_tier TEXT DEFAULT 'MEDIUM MATCH',
            matched_skills TEXT,
            missing_skills TEXT,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create Indexes for fast querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON articles(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_published ON articles(published);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarked ON articles(bookmarked);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_asset ON market_spot_prices(asset_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_range_asset ON market_forecast_ranges(asset_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_headline_asset ON market_headlines(asset_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_score ON job_listings(suitability_score);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_tier ON job_listings(match_tier);")

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

def insert_user_article(title, summary, source="User Submission", category="World", link=None, media_url="", importance_score=8.0, related_events=""):
    """
    Insert a user-submitted article directly into the SQLite database.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if not link or not link.strip():
        timestamp_slug = int(datetime.now(timezone.utc).timestamp())
        unique_hash = abs(hash(title)) % 100000
        link = f"user-sub://{timestamp_slug}_{unique_hash}"

    published = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    formatted_summary = summary.strip()
    if related_events and related_events.strip() and related_events.lower() not in formatted_summary.lower():
        formatted_summary += f"\n\n📌 Related Events Context: {related_events.strip()}"

    cursor.execute("""
        INSERT INTO articles (link, title, summary, source, category, published, media_url, importance_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(link) DO UPDATE SET
            title = excluded.title,
            summary = excluded.summary,
            source = excluded.source,
            category = excluded.category,
            published = excluded.published,
            media_url = excluded.media_url,
            importance_score = excluded.importance_score;
    """, (
        link,
        title,
        formatted_summary,
        source if source and source.strip() else "User Submission",
        category,
        published,
        media_url,
        importance_score
    ))

    conn.commit()
    conn.close()
    return link

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

def get_user_interests():
    """Retrieve category click counts from user_interests table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category, click_count FROM user_interests;")
    rows = cursor.fetchall()
    conn.close()
    return {row['category']: row['click_count'] for row in rows}


def upsert_job_listings(evaluated_jobs: list):
    """Insert or update job listings in the database."""
    conn = get_connection()
    cursor = conn.cursor()

    for job in evaluated_jobs:
        matched_str = ", ".join(job.get("matched_skills", [])) if isinstance(job.get("matched_skills"), list) else str(job.get("matched_skills", ""))
        missing_str = ", ".join(job.get("missing_skills", [])) if isinstance(job.get("missing_skills"), list) else str(job.get("missing_skills", ""))
        
        cursor.execute("""
            INSERT INTO job_listings (
                job_id, source, title, company, location, description, url, posted_date,
                stipend_salary, suitability_score, match_tier, matched_skills, missing_skills, recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                location = excluded.location,
                description = excluded.description,
                url = excluded.url,
                stipend_salary = excluded.stipend_salary,
                suitability_score = excluded.suitability_score,
                match_tier = excluded.match_tier,
                matched_skills = excluded.matched_skills,
                missing_skills = excluded.missing_skills,
                recommendation = excluded.recommendation;
        """, (
            job.get("id", job.get("job_id", f"job_{hash(job.get('title',''))}")),
            job.get("source", "Web Scraper"),
            job.get("title", job.get("job_title", "Software Intern")),
            job.get("company", "Tech Company"),
            job.get("location", "Remote"),
            job.get("description", ""),
            job.get("url", "#"),
            job.get("posted_date", "2026-08-10"),
            job.get("stipend_salary", "Not Disclosed"),
            job.get("suitability_score", 70),
            job.get("match_tier", "MEDIUM MATCH"),
            matched_str,
            missing_str,
            job.get("recommendation", "")
        ))

    conn.commit()
    conn.close()


def get_job_listings(match_tier: str = "All", min_score: int = 0, limit: int = 50) -> list:
    """Query job listings from database with optional filters."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM job_listings WHERE suitability_score >= ?"
    params = [min_score]

    if match_tier and match_tier != "All":
        query += " AND match_tier = ?"
        params.append(match_tier)

    query += " ORDER BY suitability_score DESC, created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_job_stats() -> dict:
    """Get aggregate job count and match tier breakdown."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM job_listings;")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as high_match FROM job_listings WHERE suitability_score >= 75;")
    high_match = cursor.fetchone()["high_match"]

    cursor.execute("SELECT AVG(suitability_score) as avg_score FROM job_listings;")
    avg_row = cursor.fetchone()
    avg_score = round(avg_row["avg_score"], 1) if avg_row and avg_row["avg_score"] is not None else 0.0

    conn.close()
    return {
        "total": total,
        "high_match": high_match,
        "avg_score": avg_score
    }


