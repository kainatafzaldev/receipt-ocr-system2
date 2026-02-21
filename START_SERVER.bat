@echo off
REM ========================================================================
REM OCR Receipt Processor - Startup Script for Windows
REM ========================================================================
REM This script starts the Flask backend server for the OCR Receipt Processor
REM ========================================================================

echo.
echo ========================================================================
echo             OCR RECEIPT PROCESSOR - BACKEND STARTUP
echo ========================================================================
echo.

REM Set working directory to backend folder
cd /d %~dp0backend

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.7+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
    echo.
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required packages...
    pip install -r ../requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install packages
        pause
        exit /b 1
    )
    echo [OK] Packages installed successfully
    echo.
)

REM Check .env file
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo [INFO] You need to create .env file with Novita API key
    echo.
    echo Create backend\.env with:
    echo    NOVITA_API_KEY=your_api_key_here
    echo    PORT=5000
    echo    DEBUG=True
    echo.
    echo Get your API key from: https://novita.ai/
    echo.
    pause
)

REM Start Flask server
echo.
echo ========================================================================
echo                     STARTING FLASK SERVER
echo ========================================================================
echo.
echo [INFO] Backend will be available at: http://localhost:5000
echo [INFO] Frontend interface at: http://localhost:5000/
echo.
echo [INFO] Press Ctrl+C to stop the server
echo.
echo ========================================================================
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Flask server exited with error
    echo.
    pause
)
