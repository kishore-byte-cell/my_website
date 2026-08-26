import streamlit as st
import pandas as pd
import base64
import io
import zipfile
from pathlib import Path
from datetime import datetime
import config
import cache
import sqlite_db
import importance
import categorizer
import recommendation
import summarize
import stock_data
import chart_engine
from fetch_news import feed_rate_limiter
import job_profile
import job_scraper
import job_evaluator
try:
    import ollama_summarizer
    OLLAMA_AVAILABLE = ollama_summarizer.is_ollama_available()
except Exception:
    ollama_summarizer = None
    OLLAMA_AVAILABLE = False

# Page Configuration
st.set_page_config(
    page_title="The Daily Intelligence | Broadsheet Dispatch",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- Download App as ZIP (for users who want local AI features) ----
_EXCLUDE_FROM_ZIP = {
    "news.db", "cache.json", "candidate_profile.json",
    ".venv", "__pycache__", ".git", ".idea",
}

def build_download_zip() -> bytes:
    """Build an in-memory ZIP of the project source files."""
    buf = io.BytesIO()
    project_root = Path(__file__).parent
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(project_root.rglob("*")):
            # Skip excluded names anywhere in the path
            if any(ex in item.parts for ex in _EXCLUDE_FROM_ZIP):
                continue
            # Skip hidden files / folders
            if any(part.startswith(".") for part in item.parts[len(project_root.parts):]):
                continue
            if item.is_file():
                arcname = item.relative_to(project_root)
                zf.write(item, arcname)
    buf.seek(0)
    return buf.read()


# Function to encode local images to Base64 data URLs
@st.cache_data(show_spinner=False)
def get_base64_data_url(image_path: str) -> str:
    p = Path(image_path)
    if not p.exists():
        return ""
    mime = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}.get(p.suffix.lower(), "jpeg")
    with open(p, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    return f"data:image/{mime};base64,{encoded}"


def hex_to_rgba(hex_color, alpha=1.0):
    color = hex_color.lstrip("#")
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def build_market_report_document(selected_market, official_history, forecast_df, market_report, ai_prediction, market_signals):
    report_lines = [
        f"{selected_market} Market Intelligence Report",
        f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "Official historical values:",
    ]

    for row in official_history.to_dict(orient="records"):
        month_value = row.get("Month")
        if hasattr(month_value, "strftime"):
            month_value = month_value.strftime("%Y-%m")
        report_lines.append(f"- {month_value}: {row.get('Official Price')}")

    report_lines.extend([
        "",
        "Analyst scenario range:",
    ])

    for row in forecast_df.to_dict(orient="records"):
        month_value = row.get("Month")
        if hasattr(month_value, "strftime"):
            month_value = month_value.strftime("%Y-%m")

        scenario_range = row.get("Scenario Range")
        if not scenario_range or str(scenario_range).strip().lower() in ["none", "nan", ""]:
            low = row.get("Range Low")
            high = row.get("Range High")
            if low is not None and high is not None:
                fmt_low = f"${float(low):,.0f}" if float(low) >= 100 else f"${float(low):,.2f}"
                fmt_high = f"${float(high):,.0f}" if float(high) >= 100 else f"${float(high):,.2f}"
                scenario_range = f"{fmt_low} - {fmt_high}"
            else:
                scenario_range = "$N/A"

        report_lines.append(
            f"- {month_value}: Scenario Range {scenario_range} | Source: {row.get('Source')} | Headline: {row.get('Headline')} | Summary: {row.get('Summary')}"
        )

    report_lines.extend([
        "",
        "What the graph says:",
        market_report,
        "",
        "AI multi-source summary report:",
    ])

    for bullet in ai_prediction:
        report_lines.append(f"- {bullet}")

    report_lines.extend([
        "",
        "Source commentary:",
    ])

    for signal in market_signals:
        report_lines.append(
            f"- {signal['source']} | {signal['headline']} | {signal['signal']} | {signal['note']}"
        )

    report_lines.extend([
        "",
        "Disclaimer:",
        "We are not responsible for any price misleading or price errors in the document or on the website. We only show information gathered from trusted third-party websites and reports. Any remaining errors, omissions, or misleading interpretations are the responsibility of the original source publishers and not this website.",
    ])

    return "\n".join(report_lines)


# Load Assets
assets_dir = Path(__file__).parent / "assets"
bg_path = assets_dir / "earth_galaxy_space.jpg"
if not bg_path.exists():
    bg_path = assets_dir / "background.jpg"
if not bg_path.exists():
    bg_path = Path(__file__).parent / "background.jpg"
bg_data_url = get_base64_data_url(str(bg_path))
logo_data_url = get_base64_data_url(str(assets_dir / "paperboy_logo.jpg"))
logo_b64 = logo_data_url.split(",", 1)[1] if logo_data_url else ""

logo_html_header = f'<img src="data:image/jpeg;base64,{logo_b64}" class="header-logo" alt="Paper Boy Logo"/>' if logo_b64 else ''
logo_html_sidebar = f'<img src="data:image/jpeg;base64,{logo_b64}" class="sidebar-logo" alt="Paper Boy Logo"/>' if logo_b64 else ''

# Initialize Database
sqlite_db.init_db()

# Session State Initializations
if 'articles' not in st.session_state:
    st.session_state.articles = []
if 'last_fetched' not in st.session_state:
    st.session_state.last_fetched = None

if "primary_color" not in st.session_state:
    st.session_state.primary_color = "#FFD700"
if "secondary_color" not in st.session_state:
    st.session_state.secondary_color = "#00AEEF"

# Read colors from session_state so they're available before the Settings expander
primary_color   = st.session_state.primary_color
secondary_color = st.session_state.secondary_color

# ---- SIDEBAR: Logo header (always visible) ----
# Use spans with display:block instead of nested divs — Streamlit markdown
# eats inner <div> tags but correctly renders <span> elements.
st.sidebar.markdown(f"""
<div style="margin-bottom: 0.75rem; padding: 0.25rem 0;">
    <span style="font-family: 'Cinzel', serif; font-size: 1.6rem; font-weight: 900;
                 line-height: 1.2; color: {primary_color}; display: block;">PAPER BOY</span>
    <span style="font-size: 0.75rem; color: {secondary_color}; letter-spacing: 0.5px;
                 display: block; margin-top: 3px;">Global News Dispatch</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

# ---- SIDEBAR: Dispatch button (prominent, always visible) ----
if st.sidebar.button("Dispatch Latest News", use_container_width=True):
    if not feed_rate_limiter.is_allowed():
        wait_secs = int(feed_rate_limiter.seconds_until_reset()) + 1
        st.sidebar.error(f"Rate limit: wait {wait_secs}s before refreshing.")
    else:
        with st.spinner("Fetching global RSS dispatches..."):
            raw_articles, is_fresh = cache.get_news_with_cache(force_refresh=True)
            for a in raw_articles:
                a['importance_score'] = importance.calculate_importance_score(a)
                if 'category' not in a or not a['category']:
                    primary_cat, _ = categorizer.categorize_article(a['title'], a['summary'])
                    a['category'] = primary_cat
            sqlite_db.upsert_articles(raw_articles)
            st.session_state.articles = raw_articles
            st.session_state.last_fetched = datetime.now().strftime("%H:%M:%S")
            st.toast("Fresh news dispatches received!")

st.sidebar.markdown("---")

# ---- SIDEBAR: All settings in one collapsible expander ----
with st.sidebar.expander("Settings", expanded=False):
    st.markdown("**Category Filter**")
    selected_category = st.selectbox(
        "Edition / Category",
        ["All"] + config.CATEGORIES,
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("**Sort Order**")
    sort_option = st.radio(
        "Order By",
        ["Published Date (Newest)", "Importance Score (Breaking News)"],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("**Dispatches per View**")
    items_per_page = st.slider(
        "Dispatches per View",
        min_value=6, max_value=48, value=18, step=6,
        label_visibility="collapsed"
    )

    st.markdown("**Accent Colors**")
    col_p, col_s = st.columns(2)
    with col_p:
        primary_color = st.color_picker(
            "Primary", value=st.session_state.primary_color,
            help="Titles, badges, highlights"
        )
    with col_s:
        secondary_color = st.color_picker(
            "Secondary", value=st.session_state.secondary_color,
            help="Cards, sidebar, accents"
        )
    st.session_state.primary_color = primary_color
    st.session_state.secondary_color = secondary_color

    st.markdown("**Cache**")
    if st.button("Clear Cache", help="Remove persisted cache and rebuild on next refresh.", use_container_width=True):
        cache.clear_cache()
        st.success("Cache cleared. Next refresh rebuilds content.")

    if st.session_state.last_fetched:
        st.caption(f"Last fetched: {st.session_state.last_fetched}")

    st.markdown("---")
    st.markdown("**Download App (Local AI Edition)**")
    st.caption("Run Paper Boy on your laptop with full Ollama AI features — summarization, briefings, and more.")
    if st.button("Build Download Package", use_container_width=True, help="Creates a ZIP of all source files"):
        with st.spinner("Packaging source files..."):
            zip_bytes = build_download_zip()
        st.download_button(
            label="Download paper_boy_local.zip",
            data=zip_bytes,
            file_name="paper_boy_local.zip",
            mime="application/zip",
            use_container_width=True,
        )
    with st.expander("Setup instructions (after download)"):
        st.markdown("""
**1. Install Ollama** — [ollama.com/download](https://ollama.com/download)

**2. Pull a model** (run in terminal):
```
ollama pull llama3.2
ollama serve
```

**3. Install Python packages**:
```
pip install -r requirements_local.txt
```

**4. Run the app**:
```
streamlit run app.py
```
Or simply double-click `run_local_windows.bat` on Windows.
""")


# Apply Cosmic Space Mode CSS
bg_css = f"""
    background: url("{bg_data_url}") no-repeat center center fixed !important;
    background-size: cover !important;
    image-rendering: -webkit-optimize-contrast !important;
    filter: none !important;
    -webkit-filter: none !important;
""" if bg_data_url else "background: linear-gradient(135deg, #0a0a0a 0%, #1a1a0a 100%);"

p = primary_color
s = secondary_color
glass_border = "rgba(255, 255, 255, 0.22)"
glass_blur = "blur(28px) saturate(165%)"
glass_shadow = "0 12px 40px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.18)"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700;800;900&family=Inter:wght@400;500;600;700&display=swap');

    .stApp {{
        {bg_css}
        color: #ffffff;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }}

    section[data-testid="stSidebar"] {{
        background: {hex_to_rgba(s, 0.5)} !important;
        backdrop-filter: {glass_blur};
        -webkit-backdrop-filter: {glass_blur};
        border-right: 1px solid {glass_border};
        box-shadow: {glass_shadow};
    }}

    .hero-container {{
        padding: 2rem 2.5rem;
        background: {hex_to_rgba(s, 0.5)};
        backdrop-filter: {glass_blur};
        -webkit-backdrop-filter: {glass_blur};
        border: 1px solid {glass_border};
        border-radius: 22px;
        margin-bottom: 2rem;
        box-shadow: {glass_shadow}, 0 0 40px {hex_to_rgba(p, 0.18)};
    }}

    .hero-title {{
        font-family: 'Cinzel', serif;
        font-size: 3.2rem;
        font-weight: 900;
        letter-spacing: 3px;
        color: {p};
        background: linear-gradient(90deg, {p} 0%, #ffffff 45%, {p} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        text-transform: uppercase;
        filter: drop-shadow(0 0 12px {hex_to_rgba(p, 0.75)});
        display: inline-block;
    }}

    .hero-subtitle {{
        color: rgba(255, 255, 255, 0.92);
        font-size: 1.15rem;
        margin-top: 0.4rem;
        letter-spacing: 0.8px;
        text-shadow: 0 1px 12px rgba(0, 0, 0, 0.35);
    }}

    .news-card {{
        background: {hex_to_rgba(s, 0.5)};
        backdrop-filter: {glass_blur};
        -webkit-backdrop-filter: {glass_blur};
        border: 1px solid {glass_border};
        border-radius: 20px;
        padding: 1.4rem;
        margin-bottom: 1.4rem;
        transition: all 0.35s ease;
        box-shadow: {glass_shadow};
    }}
    .news-card:hover {{
        border-color: {hex_to_rgba(p, 0.65)};
        transform: translateY(-4px);
        background: {hex_to_rgba(s, 0.58)};
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28), 0 0 36px {hex_to_rgba(p, 0.28)}, inset 0 1px 0 rgba(255, 255, 255, 0.22);
    }}

    .news-img-container {{
        width: 100%;
        height: 195px;
        border-radius: 14px;
        overflow: hidden;
        margin-bottom: 1rem;
        background-color: {hex_to_rgba(s, 0.35)};
        border: 1px solid {hex_to_rgba(p, 0.35)};
        box-shadow: inset 0 0 24px rgba(0, 0, 0, 0.18);
    }}
    .news-img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}

    .badge {{
        display: inline-block;
        padding: 0.3rem 0.7rem;
        border-radius: 9999px;
        font-size: 0.73rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-right: 0.35rem;
        margin-bottom: 0.55rem;
    }}
    .badge-category {{
        background: {hex_to_rgba(p, 0.22)};
        color: {p};
        border: 1px solid {hex_to_rgba(p, 0.55)};
        backdrop-filter: blur(8px);
    }}
    .badge-source {{
        background: {hex_to_rgba(s, 0.28)};
        color: #ffffff;
        border: 1px solid {glass_border};
        backdrop-filter: blur(8px);
    }}
    .badge-importance {{
        background: {hex_to_rgba(p, 0.22)};
        color: {p};
        border: 1px solid {hex_to_rgba(p, 0.55)};
        backdrop-filter: blur(8px);
    }}

    .article-title {{
        font-size: 1.22rem;
        font-weight: 700;
        color: #ffffff;
        text-decoration: none;
        line-height: 1.45;
        margin-top: 0.35rem;
        margin-bottom: 0.6rem;
        display: block;
        text-shadow: 0 1px 8px rgba(0, 0, 0, 0.35);
    }}
    .article-title:hover {{
        color: {p};
    }}
    .article-snippet {{
        color: rgba(255, 255, 255, 0.88);
        font-size: 0.94rem;
        line-height: 1.6;
        margin-bottom: 0.85rem;
    }}
    .article-meta {{
        color: rgba(255, 255, 255, 0.72);
        font-size: 0.82rem;
    }}

    .summary-box {{
        background: {hex_to_rgba(s, 0.5)};
        backdrop-filter: {glass_blur};
        -webkit-backdrop-filter: {glass_blur};
        border: 1px solid {glass_border};
        border-left: 4px solid {p};
        padding: 1.1rem 1.35rem;
        border-radius: 14px;
        margin-top: 0.9rem;
        font-size: 0.93rem;
        box-shadow: {glass_shadow};
    }}
    .summary-bullet {{
        margin-bottom: 0.5rem;
        color: #ffffff;
    }}
    .summary-title {{
        font-weight: 800;
        color: {p};
        margin-bottom: 0.55rem;
    }}

    /* Buttons — all types, all pages */
    div.stButton > button,
    div.stDownloadButton > button,
    div.stFormSubmitButton > button,
    button[kind="primary"],
    button[kind="secondary"],
    button[kind="tertiary"],
    .stSidebar div.stButton > button,
    .stSidebar div.stDownloadButton > button,
    div[data-testid="stSidebar"] button:not([data-baseweb="tab"]):not([aria-label*="close"]) {{
        background: {hex_to_rgba(s, 0.45)} !important;
        backdrop-filter: blur(16px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(16px) saturate(150%) !important;
        color: #ffffff !important;
        border: 1px solid {glass_border} !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 6px 18px rgba(0, 0, 0, 0.18) !important;
        transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    }}
    div.stButton > button:hover,
    div.stButton > button:focus,
    div.stDownloadButton > button:hover,
    div.stDownloadButton > button:focus,
    div.stFormSubmitButton > button:hover,
    div.stFormSubmitButton > button:focus,
    button[kind="primary"]:hover,
    button[kind="secondary"]:hover,
    button[kind="tertiary"]:hover,
    .stSidebar div.stButton > button:hover,
    .stSidebar div.stDownloadButton > button:hover,
    div[data-testid="stSidebar"] button:not([data-baseweb="tab"]):not([aria-label*="close"]):hover {{
        background: {hex_to_rgba(p, 0.55)} !important;
        color: #ffffff !important;
        border-color: {hex_to_rgba(p, 0.7)} !important;
        box-shadow: 0 10px 28px {hex_to_rgba(p, 0.28)}, inset 0 1px 0 rgba(255, 255, 255, 0.22) !important;
    }}
    div.stButton > button:hover *,
    div.stButton > button:focus *,
    div.stDownloadButton > button:hover *,
    div.stFormSubmitButton > button:hover *,
    .stSidebar div.stButton > button:hover *,
    div[data-testid="stSidebar"] button:not([data-baseweb="tab"]):hover * {{
        color: #ffffff !important;
    }}

    .stExpander {{
        background: {hex_to_rgba(s, 0.5)} !important;
        backdrop-filter: {glass_blur};
        -webkit-backdrop-filter: {glass_blur};
        border: 1px solid {glass_border} !important;
        border-radius: 16px !important;
        box-shadow: {glass_shadow};
    }}
    button[data-baseweb="tab"] {{
        background: {hex_to_rgba(s, 0.42)} !important;
        backdrop-filter: blur(14px);
        border: 1px solid {glass_border} !important;
    }}
    button[aria-selected="true"] {{
        background: {hex_to_rgba(p, 0.45)} !important;
        border-color: {hex_to_rgba(p, 0.65)} !important;
    }}

    /* =====================================================
       MOBILE RESPONSIVE STYLES
       ===================================================== */

    /* Tablet (≤900px) */
    @media (max-width: 900px) {{
        .hero-title {{
            font-size: 2.8rem !important;
            letter-spacing: 6px !important;
        }}
        .hero-container {{
            padding: 1.8rem 1rem 1.2rem 1rem !important;
        }}
        /* Article cards: 2 columns on tablet */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            min-width: 48% !important;
        }}
    }}

    /* Mobile (≤640px) */
    @media (max-width: 640px) {{
        /* Hero */
        .hero-title {{
            font-size: 2rem !important;
            letter-spacing: 3px !important;
        }}
        .hero-subtitle {{
            font-size: 0.78rem !important;
            padding: 0 0.5rem !important;
        }}
        .hero-container {{
            padding: 1.2rem 0.5rem 0.8rem 0.5rem !important;
            margin-bottom: 0.8rem !important;
        }}

        /* Stats bar: stack vertically */
        .stats-bar {{
            flex-direction: column !important;
            gap: 0.4rem !important;
            font-size: 0.75rem !important;
            text-align: center !important;
        }}

        /* Article cards: single column on mobile */
        [data-testid="stHorizontalBlock"] {{
            flex-direction: column !important;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }}

        /* Tabs: scrollable on mobile */
        [data-testid="stTabs"] > div:first-child {{
            overflow-x: auto !important;
            white-space: nowrap !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: none !important;
        }}
        [data-testid="stTabs"] > div:first-child::-webkit-scrollbar {{
            display: none !important;
        }}
        button[data-baseweb="tab"] {{
            font-size: 0.78rem !important;
            padding: 0.5rem 0.8rem !important;
            min-width: auto !important;
        }}

        /* Buttons: touch-friendly */
        div.stButton > button,
        div.stDownloadButton > button,
        div.stFormSubmitButton > button {{
            min-height: 48px !important;
            font-size: 0.9rem !important;
        }}

        /* Reduce main padding */
        .main .block-container {{
            padding: 0.5rem 0.75rem 2rem 0.75rem !important;
            max-width: 100% !important;
        }}

        /* Search input: full width, larger touch target */
        div[data-testid="stTextInput"] input {{
            font-size: 16px !important;  /* Prevents iOS zoom on focus */
            height: 3rem !important;
        }}

        /* Expander headers: larger touch target */
        .streamlit-expanderHeader {{
            min-height: 48px !important;
            font-size: 0.95rem !important;
        }}

        /* Metric cards: smaller text */
        [data-testid="stMetric"] {{
            padding: 0.5rem !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 1.2rem !important;
        }}

        /* Hide sidebar toggle label on small screens */
        [data-testid="stSidebarCollapseButton"] {{
            top: 0.5rem !important;
        }}
    }}

    /* Small mobile (≤380px — older/smaller phones) */
    @media (max-width: 380px) {{
        .hero-title {{
            font-size: 1.6rem !important;
            letter-spacing: 2px !important;
        }}
        .main .block-container {{
            padding: 0.25rem 0.5rem 2rem 0.5rem !important;
        }}
    }}
</style>
""", unsafe_allow_html=True)


# ---- SEARCH BAR CSS (wide, YouTube-style) ----
st.markdown(f"""
<style>
    /* Wide search bar styling */
    .search-bar-wrapper {{
        width: 100%;
        max-width: 860px;
        margin: 0 auto 1.6rem auto;
        position: relative;
    }}
    .search-icon {{
        position: absolute;
        left: 1.1rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 1.15rem;
        color: rgba(255,255,255,0.5);
        pointer-events: none;
        z-index: 2;
    }}
    /* Override Streamlit input inside search wrapper */
    .search-bar-wrapper div[data-testid="stTextInput"] input {{
        background: {hex_to_rgba(s, 0.38)} !important;
        backdrop-filter: blur(22px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(160%) !important;
        border: 1.5px solid {glass_border} !important;
        border-radius: 50px !important;
        color: #ffffff !important;
        font-size: 1.05rem !important;
        font-weight: 500 !important;
        padding: 0.85rem 1.4rem 0.85rem 3rem !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.12) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        height: 3.2rem !important;
    }}
    .search-bar-wrapper div[data-testid="stTextInput"] input:focus {{
        border-color: {hex_to_rgba(p, 0.7)} !important;
        box-shadow: 0 0 0 3px {hex_to_rgba(p, 0.18)}, 0 8px 32px rgba(0,0,0,0.22) !important;
        outline: none !important;
    }}
    .search-bar-wrapper div[data-testid="stTextInput"] input::placeholder {{
        color: rgba(255,255,255,0.4) !important;
    }}
    /* Hide the label */
    .search-bar-wrapper div[data-testid="stTextInput"] label {{
        display: none !important;
    }}
    /* Live stats bar */
    .stats-bar {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 2rem;
        margin-bottom: 1.2rem;
        font-size: 0.82rem;
        color: rgba(255,255,255,0.6);
        letter-spacing: 0.5px;
    }}
    .stats-bar span {{
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }}
    .stats-dot {{
        width: 6px; height: 6px;
        border-radius: 50%;
        background: {p};
        display: inline-block;
        box-shadow: 0 0 6px {hex_to_rgba(p, 0.8)};
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.4; transform: scale(0.7); }}
    }}
</style>
""", unsafe_allow_html=True)

# ---- HERO HEADER ----
# Use span+p instead of nested divs — Streamlit markdown eats inner block elements.
st.markdown(f"""
<div class="hero-container" style="text-align: center;">
    <span class="hero-title">PAPER BOY</span>
    <p class="hero-subtitle">Premium Global News Dispatch &amp; Executive Intelligence Engine</p>
</div>
""", unsafe_allow_html=True)

# ---- STATS BAR ----
article_count = len(st.session_state.articles)
last_fetch_display = st.session_state.last_fetched or "Not yet fetched"
st.markdown(f"""
<div class="stats-bar">
    <span><span class="stats-dot"></span> LIVE</span>
    <span>{article_count:,} Articles Indexed</span>
    <span>Last Fetch: {last_fetch_display}</span>
    <span>{datetime.now().strftime("%d %b %Y, %I:%M %p")}</span>
</div>
""", unsafe_allow_html=True)

# ---- WIDE SEARCH BAR (YouTube-style) ----
# Note: don't split HTML across multiple st.markdown calls — Streamlit renders
# each as a separate component, so unclosed tags don't carry over.
search_query = st.text_input(
    "Search",
    placeholder="  Search articles, topics, sources... e.g. AI, Space, Markets, India",
    label_visibility="collapsed",
    key="main_search"
)


# Load initial articles if empty
if not st.session_state.articles:
    with st.spinner("Loading dispatches from archive..."):
        raw_articles, is_fresh = cache.get_news_with_cache(force_refresh=False)
        for a in raw_articles:
            a['importance_score'] = importance.calculate_importance_score(a)
        sqlite_db.upsert_articles(raw_articles)
        st.session_state.articles = raw_articles
        st.session_state.last_fetched = datetime.now().strftime("%H:%M:%S")

# Fetch Articles from Database with Filters
@st.cache_data(ttl=30, show_spinner=False)
def _get_articles_cached(category, search_query, bookmarked_only, limit, sort_by):
    return sqlite_db.get_articles(
        category=category,
        search_query=search_query,
        bookmarked_only=bookmarked_only,
        limit=limit,
        sort_by=sort_by
    )

sort_key = "importance" if "Importance" in sort_option else "published"
db_articles = _get_articles_cached(
    category=selected_category,
    search_query=search_query,
    bookmarked_only=False,
    limit=items_per_page,
    sort_by=sort_key
)

# Apply Personalization Ranking
personalized_articles = recommendation.rank_articles_for_user(db_articles)

# Layout Tabs
tab_feed, tab_briefing, tab_analytics, tab_jobs, tab_bookmarks = st.tabs([
    "Front Page News",
    "Executive Briefings",
    "Global Analytics",
    "Job & Internship Radar",
    "Saved Edition"
])

# -------------------------------------------------------------
# TAB 1: FRONT PAGE NEWS FEED
# -------------------------------------------------------------
with tab_feed:
    with st.expander("AI Publishing Studio & Writing Box (SQL Data Entry)", expanded=False):
        st.markdown(
            "<p style='font-size: 0.9rem; color: #94a3b8; margin-bottom: 1rem;'>"
            "Publish custom news dispatches directly to the database. Use the <b>Ollama AI Writing Assistant</b> "
            "to generate drafts, fetch background context on recent famous events, or polish your writing."
            "</p>",
            unsafe_allow_html=True
        )

        # Initialize Session State for Writing Box & Tips
        if "wb_content" not in st.session_state:
            st.session_state.wb_content = ""
        if "wb_ai_tips" not in st.session_state:
            st.session_state.wb_ai_tips = ""

        # Step 1: Publishing Metadata & Event Linkage
        col_meta1, col_meta2 = st.columns([2, 1])
        with col_meta1:
            pub_title = st.text_input("1. Article Headline / Title *", key="pub_title", placeholder="e.g., Breakthrough in Commercial Fusion Energy")
            pub_author = st.text_input("2. Author / Publishing Name *", key="pub_author", value="User Submission", placeholder="e.g. Kishore, Senior Desk Analyst")
        with col_meta2:
            pub_category = st.selectbox("3. Article Category *", ["World", "Business", "Technology", "Science", "Markets", "General"], key="pub_category")
            pub_importance = st.slider("4. Importance Rating", min_value=1.0, max_value=10.0, value=8.0, step=0.5, key="pub_importance")

        pub_events = st.text_input(
            "5. Related Recent & Famous Events / Context Tags",
            key="pub_events",
            placeholder="e.g., Global Climate Summit 2026, Federal Reserve Interest Rate Cut, AI Governance Act"
        )
        pub_media = st.text_input("Optional Cover Image URL", key="pub_media", placeholder="https://example.com/image.jpg")

        st.divider()

        # Step 2: AI Assistance Toolbar
        st.markdown("##### Ollama AI Writing Toolbar")
        ai_col1, ai_col2, ai_col3 = st.columns(3)

        with ai_col1:
            if st.button("AI Generate Draft", use_container_width=True, help="Use Ollama to write a 3-paragraph draft based on headline and related events"):
                if not pub_title.strip():
                    st.warning("Please enter an Article Headline first!")
                else:
                    with st.spinner("Ollama is drafting your article..."):
                        draft = ollama_summarizer.generate_article_draft_with_ollama(
                            title=pub_title,
                            category=pub_category,
                            related_events=pub_events,
                            author_name=pub_author
                        )
                        st.session_state.wb_content = draft
                        st.rerun()

        with ai_col2:
            if st.button("AI Research & Event Tips", use_container_width=True, help="Fetch key background facts and talking points on recent events"):
                if not pub_title.strip() and not pub_events.strip():
                    st.warning("Please enter a Headline or Related Events!")
                else:
                    with st.spinner("Gathering event background tips..."):
                        tips = ollama_summarizer.get_event_research_tips_with_ollama(
                            title=pub_title,
                            category=pub_category,
                            related_events=pub_events
                        )
                        st.session_state.wb_ai_tips = tips
                        st.rerun()

        with ai_col3:
            if st.button("AI Polish & Enhance", use_container_width=True, help="Edit & refine existing writing box text for professional flow"):
                current_text = st.session_state.wb_content
                if not current_text or not current_text.strip():
                    st.warning("Please write or generate text in the Writing Box first!")
                else:
                    with st.spinner("Polishing article text with Ollama..."):
                        enhanced = ollama_summarizer.enhance_article_text_with_ollama(
                            draft_text=current_text,
                            category=pub_category
                        )
                        st.session_state.wb_content = enhanced
                        st.rerun()

        # Display AI Research Tips if generated
        if st.session_state.wb_ai_tips:
            st.info(st.session_state.wb_ai_tips)

        # Step 3: Interactive Writing Box
        st.markdown("##### Writing Box (Manual or AI-Assisted)")
        writing_box_text = st.text_area(
            "Draft your article content below (or use AI toolbar above to auto-generate):",
            value=st.session_state.wb_content,
            height=200,
            key="wb_text_area",
            placeholder="Type your story manually or click 'AI Generate Draft' to draft with Ollama..."
        )
        # Keep session state updated with text area edits
        st.session_state.wb_content = writing_box_text

        # Step 4: Publish Action Button
        st.markdown(" ")
        if st.button("Publish Article to SQL Database", type="primary", use_container_width=True):
            if not pub_title.strip():
                st.error("Headline is required before publishing.")
            elif not writing_box_text.strip():
                st.error("Article content inside the Writing Box cannot be empty.")
            else:
                new_link = sqlite_db.insert_user_article(
                    title=pub_title.strip(),
                    summary=writing_box_text.strip(),
                    source=pub_author.strip() or "User Submission",
                    category=pub_category,
                    media_url=pub_media.strip(),
                    importance_score=pub_importance,
                    related_events=pub_events.strip()
                )
                st.cache_data.clear()
                st.session_state.wb_content = ""
                st.session_state.wb_ai_tips = ""
                st.success(f"Article '{pub_title}' successfully published to SQL database! Reloading news dispatch...")
                st.rerun()

    col_info1, col_info2 = st.columns([3, 1])
    with col_info1:
        st.subheader(f"Front Page: {len(personalized_articles)} Articles ({selected_category})")
    with col_info2:
        if st.session_state.last_fetched:
            st.caption(f"Last dispatch: {st.session_state.last_fetched}")

    if not personalized_articles:
        st.info("No news dispatches match your current search query or edition filter.")
    else:
        # Render grid of 3 columns per row
        cols_per_row = 3
        for i in range(0, len(personalized_articles), cols_per_row):
            row_articles = personalized_articles[i:i + cols_per_row]
            cols = st.columns(cols_per_row)
            for idx, article in enumerate(row_articles):
                with cols[idx]:
                    st.markdown(f"""
                    <div class="news-card">
                        <div class="news-img-container">
                            <img class="news-img" src="{article['media_url']}" onerror="this.src='{config.CATEGORY_PLACEHOLDER_IMAGES['General']}'" alt="News thumbnail"/>
                        </div>
                        <div>
                            <span class="badge badge-category">{article['category']}</span>
                            <span class="badge badge-source">{article['source']}</span>
                            <span class="badge badge-importance">Score: {article['importance_score']}/10</span>
                        </div>
                        <a href="{article['link']}" target="_blank" class="article-title">{article['title']}</a>
                        <div class="article-snippet">{article['summary'][:160]}...</div>
                        <div class="article-meta"> {article['published'][:16].replace('T', ' ')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Interactive Card Action Buttons
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("Summarize", key=f"sum_{article['link']}", use_container_width=True):
                            sqlite_db.increment_category_interest(article['category'])
                            summary_res = summarize.get_article_summary(article['title'], article['summary'])
                            st.session_state[f"summary_data_{article['link']}"] = summary_res

                    with btn_col2:
                        is_bm = article.get('bookmarked', 0) == 1
                        bm_label = "Saved" if is_bm else "Save"
                        if st.button(bm_label, key=f"bm_{article['link']}", use_container_width=True):
                            new_status = sqlite_db.toggle_bookmark(article['link'])
                            st.rerun()

                    # Display Summary if triggered
                    if f"summary_data_{article['link']}" in st.session_state:
                        sdata = st.session_state[f"summary_data_{article['link']}"]
                        bullets = sdata['bullets']
                        mode = sdata['mode']
                        bullet_html = "".join([f"<div class='summary-bullet'>• {b}</div>" for b in bullets])
                        st.markdown(f"""
                        <div class="summary-box">
                            <div class="summary-title">Executive Takeaways ({mode}):</div>
                            {bullet_html}
                        </div>
                        """, unsafe_allow_html=True)


# -------------------------------------------------------------
# TAB 2: AI EXECUTIVE BRIEFINGS
# -------------------------------------------------------------
with tab_briefing:
    st.subheader("Executive News Intelligence Briefings")
    st.markdown("Automated executive briefings for top-rated breaking stories across global feeds.")

    top_news = sqlite_db.get_articles(limit=5, sort_by="importance")
    for article in top_news:
        with st.expander(f"[{article['importance_score']}/10] {article['title']} ({article['source']})", expanded=True):
            b_col1, b_col2 = st.columns([1, 3])
            with b_col1:
                st.image(article['media_url'], use_container_width=True)
            with b_col2:
                st.write(f"**Category:** {article['category']} | **Source:** {article['source']} | **Published:** {article['published'][:16].replace('T', ' ')}")
                st.write(article['summary'])
                
                # Generate Briefing Summary
                summary_data = summarize.get_article_summary(article['title'], article['summary'])
                st.markdown("**Key Takeaways:**")
                for bullet in summary_data['bullets']:
                    st.markdown(f"- {bullet}")

                st.markdown(f"[ Read Full Dispatch on {article['source']}]({article['link']})")


# -------------------------------------------------------------
# TAB 3: GLOBAL ANALYTICS
# -------------------------------------------------------------
with tab_analytics:
    st.subheader("Global News Intelligence Analytics")

    cat_data = sqlite_db.get_category_analytics()
    source_data = sqlite_db.get_source_analytics()

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("#### Edition Category Breakdown")
        if cat_data:
            df_cat = pd.DataFrame(list(cat_data.items()), columns=['Category', 'Articles'])
            st.bar_chart(df_cat.set_index('Category'))
        else:
            st.info("No analytics data available yet.")

    with col_chart2:
        st.markdown("#### Top News Publishers")
        if source_data:
            df_source = pd.DataFrame(list(source_data.items()), columns=['Publisher', 'Dispatches'])
            st.bar_chart(df_source.set_index('Publisher'))
        else:
            st.info("No source data available yet.")

    st.markdown("---")
    st.markdown("###  Global Market Pulse & RSS Intelligence")
    st.caption("Past rates and future expected target corridors powered by trusted RSS resources in rss_sources/. Paper summaries generated by internal Ollama AI.")

    # Graph Settings & Controls Container
    with st.container():
        st.markdown("####  Graph Settings & Forecast Source Controls")
        col_asset, col_source = st.columns([1, 1])

        with col_asset:
            selected_market = st.selectbox(
                "Choose Asset Class / Company",
                options=stock_data.get_market_assets(),
                index=0,
            )

        with col_source:
            selected_source = st.selectbox(
                "Select Institutional Forecast Source (BBC, Reuters, WSJ, CNBC, etc.)",
                options=stock_data.get_market_sources(),
                index=0,
            )

        st.markdown(
            "Blue Line: Past Original Rate (Official Spot History) | "
            "Red Line: Expected Past Rate (Historical Forecast) | "
            "Orange Line & Band: Future Expected Rate (Forward Target)"
        )

    market_df = stock_data.get_market_chart_data(selected_market)
    market_df = stock_data.normalize_market_chart_frame(market_df)
    expected_past_df = stock_data.get_expected_past_dataframe(selected_market, selected_source)
    forecast_df = stock_data.get_market_forecast_dataframe(selected_market, selected_source)
    market_signals = stock_data.get_market_signals(selected_market)
    market_report = stock_data.get_market_report(selected_market)
    ai_prediction = stock_data.get_market_prediction(selected_market)
    official_history = stock_data.get_market_history_dataframe(selected_market)
    market_snapshot = stock_data.get_market_snapshot(selected_market)

    # Fetch RSS papers and run internal Ollama summarizer
    rss_papers = stock_data.get_market_rss_papers_with_ollama(selected_market)

    report_text = build_market_report_document(
        selected_market,
        official_history,
        forecast_df,
        market_report,
        ai_prediction,
        market_signals,
    )

    download_file_name = f"{selected_market.lower().replace('/', '-').replace(' ', '_')}_market_report.txt"
    encoded_report = base64.b64encode(report_text.encode("utf-8")).decode("ascii")
    st.markdown(
        f"""
        <div style="position: fixed; right: 20px; bottom: 20px; z-index: 9999;">
            <a href="data:text/plain;base64,{encoded_report}" download="{download_file_name}" style="display: inline-block; padding: 12px 18px; background: #0d6efd; color: white; text-decoration: none; border-radius: 999px; font-weight: 700; box-shadow: 0 6px 18px rgba(0,0,0,0.2);">Download report</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"#### {selected_market} — Multi-Source Rate Analysis ({selected_source})")
    st.caption("Blue: Past Original Spot Rate | Red: Expected Past Rate | Orange: Future Expected Target Corridor")

    with st.container():
        st.subheader("Market Snapshot")
        col_price, col_high, col_low, col_change = st.columns(4)
        c_price = market_snapshot.get('current_price')
        d_high = market_snapshot.get('day_high')
        d_low = market_snapshot.get('day_low')
        chg = market_snapshot.get('change_percent')

        with col_price:
            st.metric("Current Spot Rate", f"${c_price:,.2f}" if c_price is not None else "N/A")
        with col_high:
            st.metric("Day High Rate", f"${d_high:,.2f}" if d_high is not None else "N/A")
        with col_low:
            st.metric("Day Low Rate", f"${d_low:,.2f}" if d_low is not None else "N/A")
        with col_change:
            st.metric("Expected Trend", f"{chg or 'Stable'}")

    # Render modern vibrant Plotly chart with 3 distinct color series
    with st.container():
        chart_engine.render_market_chart(
            selected_market,
            market_df,
            expected_past_df,
            forecast_df,
            selected_source,
        )

    st.markdown("#####  Internal Ollama Summaries for RSS Market Papers")
    st.caption("AI-generated synthesis of latest research papers and dispatches posted across trusted RSS channels.")

    for paper in rss_papers:
        with st.expander(f"{paper['headline']} — ({paper['source']})", expanded=True):
            st.markdown(f"**Source RSS Channel**: {paper['source']}")
            if paper.get("published"):
                st.caption(f"Published: {paper['published']}")
            st.markdown("---")
            st.markdown("#####  Internal Ollama Executive Summary:")
            st.markdown(paper["ollama_summary"])
            st.markdown("---")
            st.markdown(f"**Original Abstract**: {paper['raw_summary']}")
            if paper.get("url"):
                st.markdown(f"[Read Full Paper Dispatch]({paper['url']})")

    st.markdown("#####  Historical Past Rates & Future Expected Table")
    col_hist, col_fc = st.columns(2)
    with col_hist:
        st.markdown("**Past Official Spot Values**")
        st.dataframe(official_history, use_container_width=True)
    with col_fc:
        st.markdown("**Future Expected Target Corridor**")
        st.dataframe(forecast_df, use_container_width=True)

    st.markdown("#####  Market Synthesis & Signal Sources")
    st.write(market_report)
    for signal in market_signals:
        with st.container():
            st.markdown(f"**{signal['source']}**")
            st.markdown(f"- **Headline**: {signal['headline']}")
            st.markdown(f"- **Signal**: {signal['signal']}")
            st.caption(f"Note: {signal['note']}")

    st.warning(
        "Disclaimer: We are not responsible for any price misleading or price errors in the document or on the website. We only show information gathered from external trusted RSS websites and institutional reports."
    )

    st.markdown("---")


# -------------------------------------------------------------
# TAB 4: INTERNSHIP & JOB RADAR
# -------------------------------------------------------------
with tab_jobs:
    cand_data = job_profile.load_candidate_profile()
    profile = cand_data.get("candidate_profile", {})

    st.subheader("Internship & Job Search Engine (Daily Intelligence Pipeline)")
    st.caption("AI-powered multi-source career opportunity aggregation & candidate specification matching engine.")

    # Candidate Specification & Profile Editor Expander
    with st.expander("View / Edit Candidate Resume & Profile Specification", expanded=False):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            c_name = st.text_input("Full Name", profile.get("full_name", "Kishore"))
            c_email = st.text_input("Contact Email", profile.get("contact_email", "kishore@example.com"))
        with col_p2:
            c_age = st.number_input("Age", min_value=16, max_value=80, value=int(profile.get("age", 21)))
            c_degree = st.text_input("Present Degree", profile.get("present_degree", "B.Tech Computer Science (Final Year)"))
        with col_p3:
            c_loc = st.text_input("Location / Region", profile.get("location", "India / Remote"))
            c_exp = st.text_input("Experience Level", profile.get("experience_level", "Fresher / 0-1 Years"))

        st.markdown("####  Educational Qualifications &  Interested Fields")
        c_edu_str = st.text_area(
            "Educational Qualifications (one per line)",
            "\n".join(profile.get("educational_qualifications", []))
        )
        c_fields_str = st.text_input(
            "Interested Fields (comma-separated)",
            ", ".join(profile.get("interested_fields", []))
        )

        st.markdown("####  Target Roles & Core Skills")
        c_roles_str = st.text_area(
            "Target Roles (comma-separated)",
            ", ".join(profile.get("target_roles", []))
        )
        c_skills_dict = profile.get("core_skills", {})
        col_sk1, col_sk2, col_sk3 = st.columns(3)
        with col_sk1:
            c_prog_str = st.text_input("Programming Skills", ", ".join(c_skills_dict.get("programming", [])))
        with col_sk2:
            c_tools_str = st.text_input("Tools & Frameworks", ", ".join(c_skills_dict.get("tools_frameworks", [])))
        with col_sk3:
            c_domain_str = st.text_input("Domain Knowledge", ", ".join(c_skills_dict.get("domain_knowledge", [])))

        st.markdown("####  Key Projects")
        existing_projects = profile.get("projects", [])
        p1_name = existing_projects[0].get("name", "") if len(existing_projects) > 0 else ""
        p1_desc = existing_projects[0].get("description", "") if len(existing_projects) > 0 else ""
        p2_name = existing_projects[1].get("name", "") if len(existing_projects) > 1 else ""
        p2_desc = existing_projects[1].get("description", "") if len(existing_projects) > 1 else ""

        col_pr1, col_pr2 = st.columns(2)
        with col_pr1:
            st.markdown("**Project 1:**")
            c_p1_name = st.text_input("Project 1 Title", p1_name)
            c_p1_desc = st.text_area("Project 1 Description / Tech Stack", p1_desc)
        with col_pr2:
            st.markdown("**Project 2:**")
            c_p2_name = st.text_input("Project 2 Title", p2_name)
            c_p2_desc = st.text_area("Project 2 Description / Tech Stack", p2_desc)

        st.markdown("####  Portfolio Links & Exclusions")
        port_urls = profile.get("portfolio_urls", {})
        col_url1, col_url2, col_url3 = st.columns(3)
        with col_url1:
            c_gh_url = st.text_input("GitHub URL", port_urls.get("github", "https://github.com/"))
        with col_url2:
            c_li_url = st.text_input("LinkedIn URL", port_urls.get("linkedin", "https://linkedin.com/in/"))
        with col_url3:
            c_site_url = st.text_input("Portfolio Website", port_urls.get("portfolio", "https://example.com"))

        c_locs_str = st.text_input("Preferred Locations", ", ".join(profile.get("preferred_platforms_and_locations", {}).get("preferred_locations", [])))
        c_excl_str = st.text_input("Excluded Keywords", ", ".join(profile.get("preferred_platforms_and_locations", {}).get("excluded_keywords", [])))

        if st.button("Save Profile Specification"):
            cand_data["candidate_profile"]["full_name"] = c_name
            cand_data["candidate_profile"]["contact_email"] = c_email
            cand_data["candidate_profile"]["age"] = int(c_age)
            cand_data["candidate_profile"]["present_degree"] = c_degree
            cand_data["candidate_profile"]["location"] = c_loc
            cand_data["candidate_profile"]["experience_level"] = c_exp
            cand_data["candidate_profile"]["educational_qualifications"] = [q.strip() for q in c_edu_str.split("\n") if q.strip()]
            cand_data["candidate_profile"]["interested_fields"] = [f.strip() for f in c_fields_str.split(",") if f.strip()]
            cand_data["candidate_profile"]["target_roles"] = [r.strip() for r in c_roles_str.split(",") if r.strip()]
            cand_data["candidate_profile"]["core_skills"]["programming"] = [s.strip() for s in c_prog_str.split(",") if s.strip()]
            cand_data["candidate_profile"]["core_skills"]["tools_frameworks"] = [s.strip() for s in c_tools_str.split(",") if s.strip()]
            cand_data["candidate_profile"]["core_skills"]["domain_knowledge"] = [s.strip() for s in c_domain_str.split(",") if s.strip()]

            projects_list = []
            if c_p1_name.strip():
                projects_list.append({"name": c_p1_name.strip(), "description": c_p1_desc.strip()})
            if c_p2_name.strip():
                projects_list.append({"name": c_p2_name.strip(), "description": c_p2_desc.strip()})
            cand_data["candidate_profile"]["projects"] = projects_list

            cand_data["candidate_profile"]["portfolio_urls"] = {
                "github": c_gh_url.strip(),
                "linkedin": c_li_url.strip(),
                "portfolio": c_site_url.strip()
            }
            cand_data["candidate_profile"]["preferred_platforms_and_locations"] = {
                "preferred_locations": [l.strip() for l in c_locs_str.split(",") if l.strip()],
                "excluded_keywords": [e.strip() for e in c_excl_str.split(",") if e.strip()]
            }

            job_profile.save_candidate_profile(cand_data)
            st.success("Expanded Candidate Profile Specification saved successfully!")
            st.rerun()

    # Execution Action Bar
    col_run, col_status = st.columns([2, 1])
    with col_run:
        if st.button("Run Daily Job Search & AI Matching Engine", use_container_width=True, type="primary"):
            with st.spinner("Scanning LinkedIn, Internshala, GitHub Careers, & Web sources..."):
                target_roles = profile.get("target_roles", ["Python Developer"])
                locations = profile.get("preferred_platforms_and_locations", {}).get("preferred_locations", ["Remote", "India"])
                
                raw_jobs = job_scraper.run_job_scraper_sync(target_roles, locations)
                evaluated_jobs = []
                for job in raw_jobs:
                    eval_result = job_evaluator.match_job_with_ollama(cand_data, job)
                    merged = {**job, **eval_result}
                    evaluated_jobs.append(merged)
                
                sqlite_db.upsert_job_listings(evaluated_jobs)
                st.toast(f"Scanned & evaluated {len(evaluated_jobs)} career dispatches!", )
                st.rerun()

    with col_status:
        ollama_on = job_evaluator.is_ollama_active()
        if ollama_on:
            st.success("Local Ollama AI Engine Active")
        else:
            st.info("Intelligent Fallback Matcher Active")

    # Metrics Summary Row
    stats = sqlite_db.get_job_stats()
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Listings Scanned", stats.get("total", 0))
    with m2:
        st.metric("High Match (Score ≥ 75)", stats.get("high_match", 0))
    with m3:
        st.metric("Avg Suitability Score", f"{stats.get('avg_score', 0)}/100")
    with m4:
        st.metric("Candidate Target Roles", len(profile.get("target_roles", [])))

    st.markdown("---")

    # Filter Controls
    f_col1, f_col2 = st.columns([1, 2])
    with f_col1:
        match_tier_filter = st.selectbox(
            "Filter by Match Tier",
            ["All", "HIGH MATCH", "MEDIUM MATCH", "LOW MATCH"],
            index=0
        )
    with f_col2:
        min_score_filter = st.slider("Minimum Suitability Score", min_value=0, max_value=90, value=0, step=5)

    job_records = sqlite_db.get_job_listings(match_tier=match_tier_filter, min_score=min_score_filter, limit=50)

    if not job_records:
        st.info("No matching job dispatches found. Click ' Run Daily Job Search Engine' to fetch and evaluate latest opportunities.")
    else:
        # Table of Top Opportunities
        st.markdown("###  Top Recommended Opportunities (Scored by Ollama)")
        table_rows = []
        for idx, job in enumerate(job_records, 1):
            score = job.get("suitability_score", 70)
            badge = f" {score}/100" if score >= 75 else f" {score}/100"
            table_rows.append({
                "Rank": f"#{idx}",
                "Suitability Score": badge,
                "Role Title": job.get("title"),
                "Company": job.get("company"),
                "Location": job.get("location"),
                "Source": job.get("source"),
                "Stipend / Salary": job.get("stipend_salary", "Not Disclosed"),
                "Application Link": f"[Apply Here]({job.get('url')})"
            })

        st.dataframe(
            pd.DataFrame(table_rows),
            use_container_width=True,
            column_config={
                "Application Link": st.column_config.LinkColumn("Application Link")
            }
        )

        st.markdown("---")
        st.markdown("###  Detailed Match Breakdowns")

        for job in job_records:
            score = job.get("suitability_score", 70)
            tier = job.get("match_tier", "MEDIUM MATCH")
            color = "#10b981" if score >= 75 else ("#f59e0b" if score >= 50 else "#6b7280")

            with st.container():
                c_head1, c_head2 = st.columns([3, 1])
                with c_head1:
                    st.markdown(f"#### [{job.get('title')}]({job.get('url')}) — **{job.get('company')}**")
                    st.caption(f"Location: {job.get('location')} | Source: {job.get('source')} | {job.get('stipend_salary', 'Not Disclosed')} | Posted: {job.get('posted_date', 'Today')}")
                with c_head2:
                    st.markdown(
                        f"""
                        <div style="background: {color}; color: white; padding: 8px 14px; border-radius: 12px; text-align: center; font-weight: 700;">
                            {score}/100 ({tier})
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                st.markdown(f"**Job Description Summary**: {job.get('description')}")
                
                # Skills Overlap Pill Badges
                m_skills = job.get("matched_skills", "")
                m_list = [s.strip() for s in m_skills.split(",") if s.strip()] if isinstance(m_skills, str) else m_skills
                missing_skills = job.get("missing_skills", "")
                missing_list = [s.strip() for s in missing_skills.split(",") if s.strip()] if isinstance(missing_skills, str) else missing_skills

                col_sk1, col_sk2 = st.columns(2)
                with col_sk1:
                    st.markdown("** Key Skill Overlap:**")
                    if m_list:
                        badges_html = " ".join([f'<span style="background: rgba(16,185,129,0.2); color: #10b981; border: 1px solid #10b981; padding: 3px 8px; border-radius: 8px; font-size: 0.85rem;">{s}</span>' for s in m_list])
                        st.markdown(badges_html, unsafe_allow_html=True)
                    else:
                        st.write("General core skills")
                with col_sk2:
                    st.markdown("** Gaps / Prerequisites:**")
                    if missing_list:
                        missing_html = " ".join([f'<span style="background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid #ef4444; padding: 3px 8px; border-radius: 8px; font-size: 0.85rem;">{s}</span>' for s in missing_list])
                        st.markdown(missing_html, unsafe_allow_html=True)
                    else:
                        st.write("None identified")

                st.markdown(f"** AI Recommendation Rationale**: {job.get('recommendation')}")
                st.markdown(f" [Direct Application Link]({job.get('url')})")
                st.markdown("---")

        # Daily Application Action List
        st.markdown("###  Daily Application Action List")
        top_high = [j for j in job_records if j.get("suitability_score", 0) >= 75]
        if top_high:
            top1 = top_high[0]
            st.markdown(f"1. **Prepare tailored resume** for **{top1.get('title')} at {top1.get('company')}** highlighting `{top1.get('matched_skills')}`.")
            if len(top_high) > 1:
                top2 = top_high[1]
                st.markdown(f"2. **Submit application** for **{top2.get('title')} at {top2.get('company')}** via `{top2.get('source')}`.")
            st.markdown("3. **Review gap skills** (e.g. Docker / Cloud basics) to prepare for candidate interview rounds.")
        else:
            st.markdown("1. Run a fresh search scan using the button above.")
            st.markdown("2. Update candidate target roles and core skills in the Profile Specification form above.")
            st.markdown("3. Review medium-match listings and adjust resume keywords.")

    st.markdown("---")


# -------------------------------------------------------------
# TAB 5: SAVED BOOKMARKS
# -------------------------------------------------------------
with tab_bookmarks:
    st.subheader("Your Saved Dispatches")
    bookmarked_articles = sqlite_db.get_articles(bookmarked_only=True, limit=50)

    if not bookmarked_articles:
        st.info("You haven't saved any dispatches to your reading list yet. Click ' Save' on any news card to bookmark it.")
    else:
        for article in bookmarked_articles:
            with st.container():
                bm_c1, bm_c2 = st.columns([1, 4])
                with bm_c1:
                    st.image(article['media_url'], use_container_width=True)
                with bm_c2:
                    st.markdown(f"### [{article['title']}]({article['link']})")
                    st.caption(f"Category: {article['category']} | Source: {article['source']} | Saved: {article['published'][:10]}")
                    st.write(article['summary'])
                    if st.button("Remove Dispatch", key=f"del_bm_{article['link']}", use_container_width=True):
                        sqlite_db.toggle_bookmark(article['link'])
                        st.rerun()
                st.markdown("---")
