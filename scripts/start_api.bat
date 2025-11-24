@echo off
REM Start FastAPI server for RAG system (Windows)

echo ========================================
echo Starting RAG API Server
echo ========================================

REM Navigate to project root
cd /d "%~dp0\.."
echo Project root: %CD%

REM Check if virtual environment exists
if not exist "venv\" (
    echo ERROR: Virtual environment not found!
    echo Please create a virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Make sure to set OPENAI_API_KEY and other environment variables.
)

REM Start API server
echo.
echo ========================================
echo Starting API on http://localhost:8000
echo ========================================
echo Documentation: http://localhost:8000/docs
echo ReDoc: http://localhost:8000/redoc
echo Health check: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

REM Run with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
