@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"

where node >nul 2>nul
if errorlevel 1 (
    echo 未检测到 Node.js，请先安装 Node.js ^(https://nodejs.org^)
    pause
    exit /b
)

if not exist "node_modules" (
    echo [1/2] 首次运行，正在安装前端依赖...
    call npm install
)

echo [2/2] 启动 study-agent 前端（端口 5173）...
call npm run dev
if errorlevel 1 (
    echo.
    echo 启动失败！按任意键退出...
    pause >nul
)
