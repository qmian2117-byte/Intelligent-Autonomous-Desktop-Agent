@echo off
title DesktopPilot AI - Autonomous Desktop Agent
echo ====================================================
echo   Starting DesktopPilot AI Gateway (Port 8000)
echo ====================================================
cd /d "%~dp0"
start "" "http://127.0.0.1:8000/"
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
pause

