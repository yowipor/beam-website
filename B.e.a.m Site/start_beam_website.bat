@echo off
title B.E.A.M Website Launcher

echo Starting B.E.A.M Website...
echo.

REM Start the Flask app in a new window
start cmd /k py app.py

REM Wait a few seconds for server to boot
timeout /t 5 >nul

echo Starting Cloudflare Tunnel...
echo.

cloudflared tunnel --url http://localhost:5000

pause
