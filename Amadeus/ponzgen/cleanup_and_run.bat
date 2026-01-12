@echo off
echo 🔥 KILLING ALL PROCESSES (Aggressive Mode)...
taskkill /F /IM python.exe /T
taskkill /F /IM node.exe /T
taskkill /F /IM mcp-proxy.exe /T
taskkill /F /IM uvicorn.exe /T

echo 🧹 Cleaning up network ports...
netstat -ano | findstr :10396 > nul
if %errorlevel%==0 (
    echo Port 10396 is still in use! Trying to force kill PID...
    for /f "tokens=5" %%a in ('netstat -aon ^| find ":10396"') do taskkill /f /pid %%a
)

echo ⏳ Waiting 10 seconds for full release...
timeout /t 10

echo 🚀 Starting Application Cleanly...
python app.py
pause
