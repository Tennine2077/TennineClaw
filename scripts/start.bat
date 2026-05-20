@echo off
chcp 65001 >nul
echo ============================================================
echo   TennineClaw v1.0.0 - Intelligent Terminal Assistant
echo ============================================================
echo.

cd /d "%~dp0\.."

echo ============================================================
echo  NOTE: API config is now managed via Web UI.
echo  No .env file is required. Configure API Key, Base URL,
echo  and Model from the browser interface after startup.
echo ============================================================
echo.

python -m src.web_api

pause
