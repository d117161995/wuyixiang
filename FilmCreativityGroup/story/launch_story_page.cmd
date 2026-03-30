@echo off
setlocal
title Launch Story Page

set "DIR=%~dp0scene-library"
set "START_CMD=%DIR%\start.cmd"
set "URL=http://127.0.0.1:5173/"

if not exist "%START_CMD%" (
  echo [ERROR] Missing: %START_CMD%
  pause
  exit /b 1
)

echo [INFO] Starting server process...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/k \"\"%START_CMD%\"\"' -WindowStyle Normal"

echo [INFO] Waiting for server...
timeout /t 8 /nobreak >nul

echo [INFO] Opening page: %URL%
explorer.exe "%URL%"
echo [INFO] If browser did not open, copy this URL manually:
echo %URL%
exit /b 0
