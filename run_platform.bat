@echo off
title APEX LABS — AI Autonomous E-Commerce Platform
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║   APEX LABS — AI-Powered Autonomous E-Commerce Platform         ║
echo  ║   7 LangGraph Agents  ^|  Gemini 3.6 Flash  ^|  112 Edge Cases   ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.

:: ── Step 1: Check if DB already seeded to avoid slow re-seed every launch ──
IF EXIST "ecom_data.db" (
    echo  [SKIP]  Database already exists — skipping seed step.
    echo          (Delete ecom_data.db to force a fresh seed)
) ELSE (
    echo  [STEP 1]  Seeding database with demo products, orders and agents...
    python scripts\seed_demo.py
    IF ERRORLEVEL 1 (
        echo  [ERROR]  Seed failed. Check Python environment.
        pause
        exit /b 1
    )
    echo  [OK]  Demo data seeded successfully.
)
echo.

:: ── Step 2: Start FastAPI backend in a new window ─────────────────────────
echo  [STEP 2]  Launching FastAPI Control Plane on http://localhost:8001 ...
start "Apex API — Port 8001" cmd /k "python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8001 --reload"
timeout /t 2 /nobreak >nul

:: ── Step 3: Start Vite frontend dev server in a new window ────────────────
echo  [STEP 3]  Launching React Dashboard on http://localhost:5173 ...
start "Apex Web Dashboard — Port 5173" cmd /k "npm --prefix apps\web run dev"
timeout /t 3 /nobreak >nul

:: ── Step 4: Open presentation deck ────────────────────────────────────────
echo  [STEP 4]  Opening presentation deck in browser...
start "" "docs\presentation.html"
timeout /t 1 /nobreak >nul

:: ── Step 5: Open the app in browser ──────────────────────────────────────
echo  [STEP 5]  Opening platform in browser...
start "" "http://localhost:5173"

echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║   ✅  Platform is starting up!                                  ║
echo  ║                                                                  ║
echo  ║   🌐  Storefront    →  http://localhost:5173                    ║
echo  ║   ⚙️   Admin HQ     →  http://localhost:5173  (click Admin)     ║
echo  ║   📡  API Docs      →  http://localhost:8001/docs               ║
echo  ║   📊  API Health    →  http://localhost:8001/api/v1/health      ║
echo  ║   🎯  Presentation  →  docs/presentation.html (15 slides)       ║
echo  ║                                                                  ║
echo  ║   Press Ctrl+C in each terminal window to stop servers.         ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
pause
