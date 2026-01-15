@echo off
REM Restart the Flask server

echo Finding and stopping existing server...
for /f "tokens=2" %%a in ('netstat -ano ^| findstr :5000') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)

timeout /t 2 /nobreak >nul

echo Starting server...
python scripts/start_server.py

pause