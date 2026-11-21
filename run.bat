@echo off
title SmartRoute BD - Local Server
echo ============================================================
echo         Starting SmartRoute BD Local Server...
echo ============================================================
echo.

set PORT=8001
set VENV_PY=%~dp0.venv\Scripts\python.exe

if not exist "%VENV_PY%" (
    echo ERROR: Virtual environment not found at %VENV_PY%
    echo Please create the environment first:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo Application URL: http://127.0.0.1:%PORT%
echo Admin Portal:    http://127.0.0.1:%PORT%/admin (admin / 12345678)
echo Swagger Docs:    http://127.0.0.1:%PORT%/docs
echo.
echo Press CTRL+C to stop the server anytime.
echo ============================================================
echo.

"%VENV_PY%" -m uvicorn src.api.main:app --host 127.0.0.1 --port %PORT% --reload
pause
