@echo off
setlocal

cd /d "%~dp0.."
set PATH=%USERPROFILE%\.cargo\bin;%PATH%

echo Starting LocalMind Backend...
start "LocalMind Backend" /B python -m backend.app

echo Starting LocalMind UI (Web Mode)...
cd desktop
echo Opening Browser...
start http://localhost:1420
call npm run dev

endlocal
