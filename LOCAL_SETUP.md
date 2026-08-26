# Paper Boy — Local Setup Guide
# AI-Powered Edition with Ollama Support

Welcome! This guide helps you run Paper Boy locally on your laptop with **full AI features** enabled (article summarization, smart briefings, and more).

## Requirements
- Python 3.10 or higher
- Internet connection (for news fetching)
- 4 GB RAM minimum (8 GB recommended for AI features)

---

## Step 1 — Install Ollama (AI Engine)

Ollama lets you run AI models locally on your laptop — completely free and private.

### Windows
Download and install from: https://ollama.com/download/windows

### macOS
```bash
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

---

## Step 2 — Download an AI Model

After installing Ollama, open a terminal and run:

```bash
# Recommended: Llama 3.2 (fast, 2 GB)
ollama pull llama3.2

# OR for better quality (larger, 4.7 GB):
ollama pull llama3
```

Start the Ollama server (keep this terminal open):
```bash
ollama serve
```

---

## Step 3 — Install Python Dependencies

Open a new terminal in the Paper Boy folder and run:

```bash
# Create a virtual environment (recommended)
python -m venv .venv

# Activate it:
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install all packages including Ollama
pip install -r requirements_local.txt
```

---

## Step 4 — Run Paper Boy

```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`

---

## AI Features Available Locally

| Feature | Cloud Version | Local (with Ollama) |
|---|---|---|
| News fetching & RSS | Yes | Yes |
| Job & internship search | Yes | Yes |
| Article summarization | No | **Yes** |
| Executive briefings | Basic | **Full AI** |
| Market analysis | Basic | **Full AI** |

---

## Troubleshooting

**"Ollama not available" message in app:**
- Make sure `ollama serve` is running in a terminal
- Check it's accessible: open http://localhost:11434 in your browser — you should see `Ollama is running`

**Slow AI responses:**
- Try a smaller model: `ollama pull llama3.2:1b`
- In the app settings, select the smaller model

**Port already in use:**
```bash
streamlit run app.py --server.port 8502
```
