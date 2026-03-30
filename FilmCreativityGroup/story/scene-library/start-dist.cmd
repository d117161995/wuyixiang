@echo off
setlocal

REM Production/shared mode: serve built dist output
set PORT=5173
set HOST=0.0.0.0
set SERVE_DIST=1
set DIR=%~dp0
set "SENCE_DIR=\\172.27.109.10\y\tmp\WuYiXiang\XXD_AI\Asset\Sence"

where node >nul 2>nul
if %errorlevel% neq 0 (
  echo [ERROR] Node.js not found.
  pause
  exit /b 1
)

if not exist "%DIR%..\..\dist" (
  echo [INFO] dist not found, building now...
  cd /d "%DIR%..\.."
  call npm run build:web
)

set "LAN_IP="
for /f "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /R /C:"IPv4.*:"') do (
  if not defined LAN_IP set "LAN_IP=%%I"
)
if defined LAN_IP set "LAN_IP=%LAN_IP: =%"

echo [INFO] Starting dist server on http://localhost:%PORT%/
if defined LAN_IP (
  echo [INFO] Team URL: http://%LAN_IP%:%PORT%/
  echo [INFO] Planning page: http://%LAN_IP%:%PORT%/%%E6%%B3%%A1%%E9%%9D%%A2%%E7%%95%%AA%%E7%%AD%%96%%E5%%88%%92%%E5%%B1%%95%%E7%%A4%%BA.html
) else (
  echo [INFO] Team URL: http://<your-ip>:%PORT%/
)

node "%DIR%server.mjs"
