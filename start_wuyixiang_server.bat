@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"

echo ============================================
echo   WuYiXiang 服务启动（服务器模式）
echo   Nginx 由 ImageSplitter 统一管理，此处不启动
echo ============================================
echo.

:: -------- 1. 启动 Vite 开发服务器（Seedance Studio API） --------
echo [Vite  ] 启动中... 端口 9097
start "WuYiXiang - Vite:9097" cmd /k "cd /d "%ROOT%" && node start-vite.js"

:: -------- 2. 启动 open_folder_service.py --------
echo [Python] 启动 open_folder_service... 端口 8081
start "WuYiXiang - FolderService:8081" cmd /k "cd /d "%ROOT%" && python open_folder_service.py"

echo.
echo ============================================
echo   服务已启动
echo   Vite API : http://127.0.0.1:9097
echo   主页入口 : http://127.0.0.1:8080  (由 Nginx 提供)
echo ============================================
echo.
pause
