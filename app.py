import streamlit as st
import pandas as pd
import base64
from pathlib import Path
from datetime import datetime
import config
import cache
import sqlite_db
import importance
import categorizer
import recommendation
import summarize
import market_intelligence
from fetch_news import feed_rate_limiter

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - optional dependency
    go = None

# Page Configuration
st.set_page_config(
    page_title="Paper Boy | Global News Dispatch",
    page_icon="🚴‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Function to encode local images to Base64 data URLs
def get_base64_data_url(image_path):
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


MARKET_CHART_COLORS = {
    "Gold": "#f0c419",
    "USD/INR": "#5cc8ff",
    "US Dollar Index": "#8bf08b",
    "NVIDIA": "#ff8a5b",
    "Apple": "#b8a8ff",
    "Microsoft": "#7ad7f0",
}


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
        report_lines.append(
            f"- {month_value}: Scenario Range {row.get('Scenario Range')} | Source: {row.get('Source')} | Headline: {row.get('Headline')} | Summary: {row.get('Summary')}"
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
bg_data_url = get_base64_data_url(assets_dir / "earth_galaxy_space.png")
logo_data_url = get_base64_data_url(assets_dir / "paperboy_logo.jpg")
logo_b64 = logo_data_url.split(",", 1)[1] if logo_data_url else ""

logo_html_header = f'<img src="data:image/jpeg;base64,{logo_b64}" class="header-logo" alt="Paper Boy Logo"/>' if logo_b64 else '🚴‍♂️'
logo_html_sidebar = f'<img src="data:image/jpeg;base64,{logo_b64}" class="sidebar-logo" alt="Paper Boy Logo"/>' if logo_b64 else '🚴‍♂️'

# Initialize Database
sqlite_db.init_db()

# Session State Initializations
if 'articles' not in st.session_state:
    st.session_state.articles = []
if 'last_fetched' not in st.session_state:
    st.session_state.last_fetched = None

# Theme Mode Selector in Sidebar
theme_mode = st.sidebar.radio(
    "🎨 Display Theme Mode",
    ["🌌 Cosmic Space Mode", "📰 90's Vintage Paper Mode"],
    index=0
)

is_vintage = "Vintage" in theme_mode

if "primary_color" not in st.session_state:
    st.session_state.primary_color = "#FFD700"
if "secondary_color" not in st.session_state:
    st.session_state.secondary_color = "#00AEEF"

if not is_vintage:
    st.sidebar.markdown("**🎨 Accent Colors**")
    primary_color = st.sidebar.color_picker(
        "Primary Color",
        value=st.session_state.primary_color,
        help="Titles, badges, buttons, and highlights",
    )
    secondary_color = st.sidebar.color_picker(
        "Secondary Color",
        value=st.session_state.secondary_color,
        help="Sidebar accents, cards, and supporting elements",
    )
    st.session_state.primary_color = primary_color
    st.session_state.secondary_color = secondary_color
else:
    primary_color = st.session_state.primary_color
    secondary_color = st.session_state.secondary_color

# Sidebar Header with Custom Bicycle Logo
st.sidebar.markdown(f"""
<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 0.5rem;">
    {logo_html_sidebar}
    <div>
        <div style="font-family: 'Cinzel', serif; font-size: 1.6rem; font-weight: 900; line-height: 1; color: {primary_color if not is_vintage else '#111111'};">PAPER BOY</div>
        <div style="font-size: 0.75rem; color: {secondary_color if not is_vintage else '#333333'}; letter-spacing: 0.5px;">Global News Dispatch</div>
    </div>
</div>
<style>
    .sidebar-logo {{
        width: 48px;
        height: 48px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid {primary_color if not is_vintage else '#111111'};
        box-shadow: 0 0 10px {hex_to_rgba(primary_color, 0.4) if not is_vintage else 'rgba(17, 17, 17, 0.4)'};
    }}
    .header-logo {{
        width: 64px;
        height: 64px;
        border-radius: 50%;
        object-fit: cover;
        border: 2.5px solid {primary_color if not is_vintage else '#111111'};
        box-shadow: 0 0 16px {hex_to_rgba(primary_color, 0.6) if not is_vintage else 'rgba(17, 17, 17, 0.6)'};
        vertical-align: middle;
        margin-right: 12px;
    }}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

if st.sidebar.button("Clear cached news safely", help="Remove the persisted cache file and rebuild it on the next refresh."):
    cache.clear_cache()
    st.sidebar.success("Cache cleared safely. The next refresh will rebuild fresh content.")

# Apply Dynamic CSS based on Selected Theme Mode
if is_vintage:
    # 📰 90's VINTAGE NEWSPAPER MODE CSS (ALL TEXT HIGH CONTRAST & FULLY VISIBLE)
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&family=Courier+Prime:wght@400;700&display=swap');

        /* Aged Dirty White Newsprint Background */
        .stApp {
            background-color: #f3efe6 !important;
            background-image: radial-gradient(#dfd9cd 1px, transparent 0) !important;
            background-size: 20px 20px !important;
            color: #111111 !important;
            font-family: 'Old Standard TT', Georgia, serif !important;
        }

        /* FORCE ALL STREAMLIT NATIVE TEXT & LABELS TO DARK SOLID BLACK */
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp div, .stApp li, .stApp button, .stApp input, .stApp textarea, .stMarkdown {
            color: #111111 !important;
        }
        
        /* Captions and Meta Text */
        div[data-testid="stCaptionContainer"] p, .stCaption {
            color: #333333 !important;
            font-weight: 600 !important;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #eae5da !important;
            border-right: 3px double #111111 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #111111 !important;
        }

        /* Tabs Styling */
        button[data-baseweb="tab"] {
            background: #e4dfd3 !important;
            border: 1px solid #111111 !important;
            border-radius: 0px !important;
            margin-right: 4px !important;
        }
        button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {
            color: #111111 !important;
            font-weight: 800 !important;
            font-family: 'Courier Prime', monospace !important;
        }
        button[aria-selected="true"] {
            background: #111111 !important;
            border: 1px solid #111111 !important;
        }
        button[aria-selected="true"] p, button[aria-selected="true"] span {
            color: #ffffff !important;
        }

        /* Expander Headers & Content */
        .stExpander {
            background: #f7f4ee !important;
            border: 2px solid #111111 !important;
            border-radius: 0px !important;
        }
        .stExpander summary p, .stExpander summary span {
            color: #111111 !important;
            font-weight: 800 !important;
            font-family: 'Playfair Display', serif !important;
            font-size: 1.15rem !important;
        }

        /* Vintage Paper Hero Container */
        .hero-container {
            padding: 2.2rem 2.5rem;
            background: #f9f6f0 !important;
            border: 4px double #111111 !important;
            border-radius: 0px !important;
            margin-bottom: 2rem;
            box-shadow: 6px 6px 0px #111111 !important;
            text-align: center;
        }
        
        .hero-title {
            font-family: 'Playfair Display', serif !important;
            font-size: 3.8rem !important;
            font-weight: 900 !important;
            letter-spacing: -1px !important;
            color: #111111 !important;
            background: none !important;
            -webkit-text-fill-color: #111111 !important;
            margin: 0 !important;
            text-transform: uppercase !important;
            text-shadow: none !important;
            filter: none !important;
            border-bottom: 3px double #111111;
            padding-bottom: 0.5rem;
            display: inline-block;
        }
        
        .hero-subtitle {
            color: #222222 !important;
            font-family: 'Courier Prime', monospace !important;
            font-size: 1.15rem !important;
            margin-top: 0.75rem !important;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 700;
        }

        /* 90's Newspaper Article Cards */
        .news-card {
            background: #fcfbfa !important;
            border: 2px solid #111111 !important;
            border-radius: 0px !important;
            padding: 1.5rem !important;
            margin-bottom: 1.5rem !important;
            box-shadow: 4px 4px 0px #111111 !important;
        }
        .news-card:hover {
            box-shadow: 7px 7px 0px #111111 !important;
            transform: translate(-2px, -2px) !important;
            background: #ffffff !important;
        }

        .news-img-container {
            width: 100%;
            height: 195px;
            border-radius: 0px !important;
            overflow: hidden;
            margin-bottom: 1rem;
            background-color: #e5e1d7;
            border: 1px solid #111111 !important;
            filter: grayscale(85%) contrast(120%);
        }
        .news-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        /* Vintage Monochromatic Badges */
        .badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 0px !important;
            font-family: 'Courier Prime', monospace !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            margin-right: 0.35rem;
            margin-bottom: 0.55rem;
        }
        .badge-category {
            background: #111111 !important;
            color: #ffffff !important;
            border: 1px solid #111111 !important;
        }
        .badge-source {
            background: #e2ded4 !important;
            color: #111111 !important;
            border: 1px solid #111111 !important;
        }
        .badge-importance {
            background: #d8d3c5 !important;
            color: #111111 !important;
            border: 1px solid #111111 !important;
        }

        .article-title {
            font-family: 'Playfair Display', serif !important;
            font-size: 1.45rem !important;
            font-weight: 900 !important;
            color: #000000 !important;
            text-decoration: none !important;
            line-height: 1.3 !important;
            margin-top: 0.4rem !important;
            margin-bottom: 0.6rem !important;
            display: block !important;
        }
        .article-title:hover {
            text-decoration: underline !important;
            color: #333333 !important;
        }
        .article-snippet {
            color: #222222 !important;
            font-size: 0.95rem !important;
            line-height: 1.6 !important;
            margin-bottom: 0.85rem !important;
        }
        .article-meta {
            color: #333333 !important;
            font-family: 'Courier Prime', monospace !important;
            font-size: 0.82rem !important;
            border-top: 1px dashed #111111;
            padding-top: 0.4rem;
        }

        /* Summary Box */
        .summary-box {
            background: #eae6dc !important;
            border: 2px solid #111111 !important;
            border-left: 6px solid #111111 !important;
            padding: 1.1rem 1.35rem !important;
            border-radius: 0px !important;
            margin-top: 0.9rem !important;
            font-size: 0.95rem !important;
            box-shadow: 3px 3px 0px #111111 !important;
        }
        .summary-bullet {
            margin-bottom: 0.5rem !important;
            color: #111111 !important;
            line-height: 1.55 !important;
        }
        .summary-title {
            font-family: 'Playfair Display', serif !important;
            font-weight: 900 !important;
            color: #000000 !important;
            margin-bottom: 0.55rem !important;
            font-size: 1.1rem !important;
            text-transform: uppercase;
        }

        /* Custom Vintage Buttons */
        div.stButton > button {
            background: #f7f4ee !important;
            color: #111111 !important;
            border: 2px solid #111111 !important;
            border-radius: 0px !important;
            font-family: 'Courier Prime', monospace !important;
            font-weight: 700 !important;
            box-shadow: 2px 2px 0px #111111 !important;
            text-transform: uppercase !important;
        }
        div.stButton > button:hover {
            background: #111111 !important;
            color: #ffffff !important;
            box-shadow: 4px 4px 0px #111111 !important;
        }
    </style>
    """, unsafe_allow_html=True)

else:
    # 🌌 COSMIC SPACE MODE CSS — bright wallpaper, frosted glass panels
    bg_css = f"""
        background:
            linear-gradient({hex_to_rgba('#ffffff', 0.06)}, {hex_to_rgba('#000000', 0.14)}),
            url("{bg_data_url}");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
        background-repeat: no-repeat;
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

        div.stButton > button {{
            background: {hex_to_rgba(s, 0.45)} !important;
            backdrop-filter: blur(16px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(16px) saturate(150%) !important;
            color: #ffffff !important;
            border: 1px solid {glass_border} !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 6px 18px rgba(0, 0, 0, 0.18) !important;
        }}
        div.stButton > button:hover {{
            background: {hex_to_rgba(p, 0.55)} !important;
            color: #ffffff !important;
            border-color: {hex_to_rgba(p, 0.7)} !important;
            box-shadow: 0 10px 28px {hex_to_rgba(p, 0.28)}, inset 0 1px 0 rgba(255, 255, 255, 0.22) !important;
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
    </style>
    """, unsafe_allow_html=True)


# Refresh Button with Rate Limiting
if st.sidebar.button("🔄 Dispatch Latest News", use_container_width=True):
    if not feed_rate_limiter.is_allowed():
        wait_secs = int(feed_rate_limiter.seconds_until_reset()) + 1
        st.sidebar.error(f"⏳ Rate limit reached. Please wait {wait_secs}s before refreshing again.")
    else:
        with st.spinner("Fetching global RSS dispatches..."):
            raw_articles, is_fresh = cache.get_news_with_cache(force_refresh=True)
            for a in raw_articles:
                a['importance_score'] = importance.calculate_importance_score(a)
                if 'category' not in a or not a['category']:
                    primary, _ = categorizer.categorize_article(a['title'], a['summary'])
                    a['category'] = primary

            sqlite_db.upsert_articles(raw_articles)
            st.session_state.articles = raw_articles
            st.session_state.last_fetched = datetime.now().strftime("%H:%M:%S")
            st.toast("Fresh news dispatches received!", icon="📰")

# Load initial articles if empty
if not st.session_state.articles:
    raw_articles, is_fresh = cache.get_news_with_cache(force_refresh=False)
    for a in raw_articles:
        a['importance_score'] = importance.calculate_importance_score(a)
    sqlite_db.upsert_articles(raw_articles)
    st.session_state.articles = raw_articles
    st.session_state.last_fetched = datetime.now().strftime("%H:%M:%S")

# Category Filter
selected_category = st.sidebar.selectbox(
    "📌 Filter Edition / Category",
    ["All"] + config.CATEGORIES,
    index=0
)

# Search Query Input
search_query = st.sidebar.text_input("🔍 Search Archive", placeholder="e.g. AI, Stocks, Space...")

# Sorting Options
sort_option = st.sidebar.radio(
    "⚙️ Order By",
    ["Published Date (Newest)", "Importance Score (Breaking News)"],
    index=0
)

# Display Options
items_per_page = st.sidebar.slider("Dispatches per View", min_value=6, max_value=48, value=18, step=6)

# Main Hero Header with Custom Bicycle Logo
st.markdown(f"""
<div class="hero-container">
    <div style="display: flex; align-items: center; justify-content: center;">
        {logo_html_header}
        <span class="hero-title">PAPER BOY</span>
    </div>
    <div class="hero-subtitle">Premium Global News Dispatch & Executive Intelligence Engine</div>
</div>
""", unsafe_allow_html=True)

# Fetch Articles from Database with Filters
sort_key = "importance" if "Importance" in sort_option else "published"
db_articles = sqlite_db.get_articles(
    category=selected_category,
    search_query=search_query,
    bookmarked_only=False,
    limit=items_per_page,
    sort_by=sort_key
)

# Apply Personalization Ranking
personalized_articles = recommendation.rank_articles_for_user(db_articles)

# Layout Tabs
tab_feed, tab_briefing, tab_analytics, tab_bookmarks = st.tabs([
    "📰 Today's Front Page",
    "⚡ Executive Briefings",
    "📊 Global Analytics",
    "🔖 Saved Edition"
])

# -------------------------------------------------------------
# TAB 1: FRONT PAGE NEWS FEED
# -------------------------------------------------------------
with tab_feed:
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
                        <div class="article-meta">🕒 {article['published'][:16].replace('T', ' ')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Interactive Card Action Buttons
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("⚡ Summarize", key=f"sum_{article['link']}", use_container_width=True):
                            sqlite_db.increment_category_interest(article['category'])
                            summary_res = summarize.get_article_summary(article['title'], article['summary'])
                            st.session_state[f"summary_data_{article['link']}"] = summary_res

                    with btn_col2:
                        is_bm = article.get('bookmarked', 0) == 1
                        bm_label = "❤️ Saved" if is_bm else "🔖 Save"
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
    st.subheader("⚡ Breaking News Intelligence Briefings")
    st.markdown("Automated executive briefings for top-rated breaking stories across global feeds.")

    top_news = sqlite_db.get_articles(limit=5, sort_by="importance")
    for article in top_news:
        with st.expander(f"🔴 [{article['importance_score']}/10] {article['title']} ({article['source']})", expanded=True):
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

                st.markdown(f"[🔗 Read Full Dispatch on {article['source']}]({article['link']})")


# -------------------------------------------------------------
# TAB 3: GLOBAL ANALYTICS
# -------------------------------------------------------------
with tab_analytics:
    st.subheader("📊 Global News Intelligence Analytics")

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
    st.markdown("### 📈 Global Market Pulse")
    st.caption("Historical trending chart for trusted asset classes and major companies. The interface presents multi-source outlook commentary without calculating a forward forecast on its own.")

    if not hasattr(market_intelligence, "get_market_chart_data"):
        market_intelligence.get_market_chart_data = market_intelligence.get_market_history

    if not hasattr(market_intelligence, "get_market_history_dataframe"):
        market_intelligence.get_market_history_dataframe = market_intelligence.get_market_history

    if not hasattr(market_intelligence, "get_market_forecast_dataframe"):
        market_intelligence.get_market_forecast_dataframe = market_intelligence.get_market_forecast

    selected_market = st.selectbox(
        "Choose a market asset to inspect",
        options=market_intelligence.get_market_assets(),
        index=0,
    )

    market_df = market_intelligence.get_market_chart_data(selected_market)
    market_df = market_intelligence.normalize_market_chart_frame(market_df)
    forecast_df = market_intelligence.get_market_forecast_dataframe(selected_market)
    market_signals = market_intelligence.get_market_signals(selected_market)
    market_report = market_intelligence.get_market_report(selected_market)
    ai_prediction = market_intelligence.get_market_prediction(selected_market)
    official_history = market_intelligence.get_market_history_dataframe(selected_market)

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

    st.markdown(f"#### {selected_market} — official spot history + analyst scenario range")
    st.caption("Solid line: live official spot market price. Dotted line: source-backed institutional scenario corridor only.")

    chart_color = MARKET_CHART_COLORS.get(selected_market, "#4F8EF7")
    if go is not None:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=market_df["Month"],
                y=market_df["Official Price"],
                mode="lines+markers",
                name="Official Spot Price",
                line=dict(color=chart_color, width=3),
                marker=dict(size=4, color=chart_color),
            )
        )

        if not forecast_df.empty:
            forecast_df = forecast_df.sort_values("Month").reset_index(drop=True)
            fig.add_trace(
                go.Scatter(
                    x=forecast_df["Month"],
                    y=forecast_df["Range Low"],
                    mode="lines",
                    name="Scenario Low",
                    line=dict(color=chart_color, width=2, dash="dot"),
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=forecast_df["Month"],
                    y=forecast_df["Range High"],
                    mode="lines",
                    name="Scenario High",
                    line=dict(color=chart_color, width=2, dash="dot"),
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=list(forecast_df["Month"]) + list(forecast_df["Month"])[::-1],
                    y=list(forecast_df["Range High"]) + list(forecast_df["Range Low"])[::-1],
                    fill="toself",
                    mode="lines",
                    name="Scenario Corridor",
                    line=dict(color=chart_color, width=0),
                    fillcolor=f"{chart_color}33",
                    showlegend=True,
                )
            )

        fig.update_layout(
            title=f"{selected_market} — official spot history and scenario corridor",
            xaxis_title="Month",
            yaxis_title="Price",
            legend_title="Series",
            template="plotly_dark",
            margin=dict(l=20, r=20, t=60, b=20),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.line_chart(market_df.set_index("Month"), use_container_width=True)

    st.markdown("##### Official historical values")
    st.dataframe(official_history, use_container_width=True)

    st.markdown("##### Analyst scenario range")
    st.dataframe(forecast_df, use_container_width=True)

    st.markdown("##### What the graph says")
    st.write(market_report)

    st.markdown("##### AI multi-source market summary report")
    for bullet in ai_prediction:
        st.markdown(f"- {bullet}")

    st.markdown("##### Where the information comes from")
    for signal in market_signals:
        with st.container():
            st.markdown(f"**{signal['source']}**")
            st.markdown(f"- {signal['headline']}")
            st.markdown(f"- {signal['signal']}")
            st.caption(signal['note'])

    st.warning(
        "Disclaimer: We are not responsible for any price misleading or price errors in the document or on the website. We only show information gathered from other websites and reports. We do not take responsibility for other errors or misleading content here; this page only presents the information we obtained from those external sources."
    )

    st.markdown("---")


# -------------------------------------------------------------
# TAB 4: SAVED BOOKMARKS
# -------------------------------------------------------------
with tab_bookmarks:
    st.subheader("🔖 Your Saved Dispatches")
    bookmarked_articles = sqlite_db.get_articles(bookmarked_only=True, limit=50)

    if not bookmarked_articles:
        st.info("You haven't saved any dispatches to your reading list yet. Click '🔖 Save' on any news card to bookmark it.")
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
