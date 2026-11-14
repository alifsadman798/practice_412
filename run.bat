@echo off
title SmartRoute BD - Local Server
echo ============================================================
echo         Starting SmartRoute BD Local Server...
echo ============================================================
echo.
echo Application URL: http://localhost:8080
echo Admin Portal:    http://localhost:8080/admin (admin / 12345678)
echo Swagger Docs:    http://localhost:8080/docs
echo.
echo Press CTRL+C to stop the server anytime.
echo ============================================================
echo.
"%~dp0.venv\Scripts\python.exe" -m uvicorn src.api.main:app --host 127.0.0.1 --port 8080 --reload
pause
