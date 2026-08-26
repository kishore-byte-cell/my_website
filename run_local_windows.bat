@echo off
echo.
echo  ====================================================
echo   Paper Boy - Local AI Edition Setup
echo  ====================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found.

:: Create virtual environment
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

:: Activate and install
echo [INFO] Installing dependencies...
call .venv\Scripts\activate
pip install -r requirements_local.txt --quiet

echo.
echo [INFO] Checking Ollama...
curl -s http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] Ollama not running. AI features will be disabled.
    echo           To enable AI: install Ollama from https://ollama.com
    echo           Then run: ollama serve  (in a separate terminal)
    echo           Then run: ollama pull llama3.2
    echo.
) else (
    echo [OK] Ollama is running - AI features enabled!
)

echo.
echo [INFO] Starting Paper Boy...
echo [INFO] Browser will open at http://localhost:8501
echo.
streamlit run app.py
pause
