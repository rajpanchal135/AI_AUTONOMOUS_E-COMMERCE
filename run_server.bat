@echo off
echo ===================================================================
echo   Starting Autonomous E-Commerce Platform on Port 8001
echo ===================================================================

echo [1/2] Checking and freeing Port 8001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do (
    if not "%%a"=="" (
        echo Killing lingering process on port 8001: PID %%a
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo [2/2] Launching FastAPI Control Plane & Dual-Sided Web Portal...
echo -------------------------------------------------------------------
echo  Open in your browser: http://localhost:8001/
echo  Interactive API Docs: http://localhost:8001/docs
echo -------------------------------------------------------------------
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8001 --reload
pause
