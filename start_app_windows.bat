@echo off
cd /d "D:\Hackathon\outbreak_backend"
start "Outbreak Backend" cmd /k "D:\Hackathon\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level info"

timeout /t 3 >nul
cd /d "D:\Hackathon\outbreak_frontend"
start "Outbreak Frontend" cmd /k "npm install && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo Backend started on: http://127.0.0.1:8000
echo Frontend started on: http://127.0.0.1:5173
pause
