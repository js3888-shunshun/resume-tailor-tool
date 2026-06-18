@echo off
REM ===== AI Resume Tailor - local server launcher =====
REM Double-click this file to start the web app, then open the browser.
REM Closing this black window stops the server.

cd /d "%~dp0backend"

REM Free port 8000 if a previous run is still holding it.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1

REM Open the page in the default browser (server starts a second later).
start "" http://127.0.0.1:8000/

echo Starting AI Resume Tailor at http://127.0.0.1:8000/
echo Keep this window open while you use the app. Close it to stop the server.
echo.

REM No --reload: it spawns a watcher + worker that can orphan and hold port 8000.
REM After a code change, just close this window and double-click start.bat again.
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
