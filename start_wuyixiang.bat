@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "NGINX_DIR=%ROOT%nginx-1.26.2"

echo ============================================
echo   WuYiXiang 服务启动脚本
echo ============================================
echo.

:: -------- 1. 停止已有 Nginx 进程（避免端口冲突） --------
tasklist /FI "IMAGENAME eq nginx.exe" 2>nul | find /I "nginx.exe" >nul
if %ERRORLEVEL%==0 (
    echo [Nginx] 检测到已运行的 nginx，先停止...
    "%NGINX_DIR%\nginx.exe" -p "%NGINX_DIR%" -s stop >nul 2>&1
    timeout /t 2 /nobreak >nul
)

:: -------- 2. 启动 Nginx --------
echo [Nginx] 启动中... 端口 8080
start "" "%NGINX_DIR%\nginx.exe" -p "%NGINX_DIR%"
timeout /t 1 /nobreak >nul

tasklist /FI "IMAGENAME eq nginx.exe" 2>nul | find /I "nginx.exe" >nul
if %ERRORLEVEL%==0 (
    echo [Nginx] 启动成功
) else (
    echo [Nginx] 启动失败，请检查 nginx-1.26.2\logs\error.log
)

:: -------- 3. 启动 Vite 开发服务器（Seedance Studio API） --------
echo [Vite ] 启动中... 端口 8095
start "WuYiXiang - Vite:8095" cmd /k "cd /d "%ROOT%" && node start-vite.js"

:: -------- 4. 启动 open_folder_service.py --------
echo [Python] 启动 open_folder_service... 端口 8081
start "WuYiXiang - FolderService:8081" cmd /k "cd /d "%ROOT%" && python open_folder_service.py"

echo.
echo ============================================
echo   所有服务已启动
echo   主页: http://127.0.0.1:8080
echo   Vite: http://127.0.0.1:8095  (Seedance Studio)
echo ============================================
echo.
pause
