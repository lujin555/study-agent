@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

echo [1/2] 正在检查依赖...
"%PY%" -c "import fastapi" 2>nul
if errorlevel 1 (
    echo 缺少依赖，正在安装...
    "%PY%" -m pip install -r requirements.txt
)

echo [2/2] 启动 study-agent 后端（端口 8084）...
"%PY%" app.py
if errorlevel 1 (
    echo.
    echo 启动失败！按任意键退出...
    pause >nul
)
