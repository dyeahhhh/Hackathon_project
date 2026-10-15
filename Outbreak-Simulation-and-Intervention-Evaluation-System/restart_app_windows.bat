@echo off
setlocal enabledelayedexpansion

REM Kill any stale process using port 8000
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8000') do (
    echo Closing PID %%P already using port 8000
    taskkill /F /PID %%P >nul 2>&1
)

REM Start backend from the actual project folder
cd /d "D:\Hackathon\outbreak_backend"
start "Outbreak Backend" cmd /k "D:\Hackathon\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level info"

timeout /t 4 >nul

REM Start frontend
cd /d "D:\Hackathon\outbreak_frontend"
start "Outbreak Frontend" cmd /k "npm install && npm run dev -- --host 127.0.0.1 --port 4173"

echo.
echo Backend: http://127.0.0.1:8000
 echo Frontend: http://127.0.0.1:4173
pause
