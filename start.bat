@echo off
cd /d %~dp0
echo =========================================
echo 🤖 Starting Recruiter AI Agent System...
echo =========================================

echo Starting FastAPI Backend (Port 8000)...
start cmd /k "call venv\Scripts\activate.bat && uvicorn main:app --reload"

echo Starting Next.js Frontend (Port 3000)...
start cmd /k "cd frontend && npm run dev"

echo.
echo Servers are booting up in separate windows!
echo Please wait about 10-15 seconds for the servers to fully start.
echo Frontend will be available at: http://localhost:3000
echo Backend API will be at: http://localhost:8000

:: Wait a few seconds for servers to start, then open the browser
timeout /t 5 /nobreak >nul
start http://localhost:3000

pause
