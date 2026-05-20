@echo off
chcp 65001 >nul
echo ============================================================
echo   TennineClaw - Intelligent Terminal Assistant
echo   Version: 1.0.0
echo ============================================================
echo.

cd /d "%~dp0"

if exist ".env" (
    echo [CONFIG] Loading non-API environment variables...
    for /f "delims=" %%a in ('findstr /r "^GRADIO_PORT=" .env') do set "%%a"
    echo [OK] Non-API env vars loaded from .env.
) else (
    echo [INFO] .env not found, using defaults.
)
echo.

echo ============================================================
echo  NOTE: API config is now managed via Web UI.
echo  Open the browser after starting, use top-right model
echo  settings to configure API Key / Base URL / Model.
echo ============================================================
echo.

echo [STARTING] TennineClaw Web API...
echo.
python -m web_api

pause
