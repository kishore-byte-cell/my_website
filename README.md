Daily Intelligence
Daily Intelligence is a Python-based news and market intelligence dashboard built with Streamlit. It collects, categorizes, scores, stores, and summarizes global news content from multiple trusted RSS feeds while also presenting a market analytics view for major assets and companies.

Features
Real-time RSS news ingestion from global sources
Automatic categorization across major topics
Importance and recency scoring for breaking stories
SQLite-backed storage and search
Local Ollama and extractive summarization support
Market analytics panel for official history and scenario-range reporting
Downloadable report export for users
Source-grounded summary workflow for market interpretation
Tech Stack
Python
Streamlit
SQLite
Pandas
Requests
yfinance
Ollama
Plotly
Project Structure
app.py – main Streamlit dashboard
market_intelligence.py – market history and scenario-range logic
fetch_news.py – news extraction and feed handling
categorizer.py – category classification
importance.py – importance scoring
sqlite_db.py – database storage and analytics queries
summarize.py – summarization backend
cache.py – cache management
requirements.txt – dependencies


Run Locally
pip install -r requirements.txt
streamlit run app.py
