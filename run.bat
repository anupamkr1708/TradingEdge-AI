@echo off
REM TradeMind AI - Local Development Startup Script

echo Starting TradeMind AI...
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet
echo.

REM Check if .env exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and configure it.
    echo.
    pause
    exit /b 1
)

REM Start application
echo Starting FastAPI server...
echo Access API at: http://localhost:8001
echo Health check: http://localhost:8001/health
echo Metrics: http://localhost:8001/metrics
echo.
echo Press Ctrl+C to stop
echo.

uvicorn app.main:app --reload --port 8001 --host 0.0.0.0
