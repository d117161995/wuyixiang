@echo off
REM 更新场景库数据库：扫描 Sence 目录，更新 scene-db.json
REM 会保留已有的收藏夹和回收站

set SRC=Y:\tmp\WuYiXiang\XXD_AI\Asset\Sence
set OUT=%~dp0scene-db.json

where node >nul 2>nul
if %errorlevel% neq 0 (
  echo [ERROR] 未找到 Node.js
  pause
  exit /b 1
)

node "%~dp0..\..\tools\update_scene_db.mjs" --src "%SRC%" --out "%OUT%"
pause
