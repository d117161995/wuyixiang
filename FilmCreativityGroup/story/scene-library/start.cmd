@echo off
setlocal

REM 场景库一键启动（Windows CMD 版）
REM - 启动本地静态服务器（http://localhost）并打开浏览器

set PORT=5173
set DIR=%~dp0

REM --- 配置图片路径 ---
REM 如果别人的电脑上路径不同，请修改下面这一行：
set "SENCE_DIR=\\172.27.109.10\y\tmp\WuYiXiang\XXD_AI\Asset\Sence"
REM --------------------

REM 尝试关闭旧的 Node 进程（防止端口占用）
taskkill /F /IM node.exe >nul 2>nul

REM 使用 Node 自带 server.mjs（可同时服务图片目录 /sence/*）
where node >nul 2>nul
if %errorlevel%==0 (
  set "PORT=%PORT%"
  REM 将 SENCE_DIR 传递给 Node 进程
  set "SENCE_DIR=%SENCE_DIR%"
  echo Starting server on port %PORT%...
  echo Images dir: %SENCE_DIR%
  echo Server URL: http://localhost:%PORT%/
  node "%DIR%server.mjs"
  if %errorlevel% neq 0 (
    echo Server crashed or failed to start.
    pause
  )
  exit /b %errorlevel%
)

echo [ERROR] 未找到 Python 或 Node(npx)，无法启动本地服务器。
echo 请先安装 Node.js 后重试。
exit /b 1

