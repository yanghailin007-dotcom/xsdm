@echo off
chcp 65001 >nul
title 清理缓存并启动服务器
echo ========================================
echo   🧹 清理缓存并启动服务器
echo ========================================
echo.

REM 1. 清理 Python 缓存
echo 🔍 清理 Python 缓存...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
for /r . %%f in (*.pyc *.pyo) do @if exist "%%f" del /f /q "%%f" 2>nul
echo ✅ Python 缓存已清理
echo.

REM 2. 清理运行时文件
echo 🔍 清理运行时文件...
if exist .server.pid del /f /q .server.pid 2>nul
echo ✅ 运行时文件已清理
echo.

REM 3. 确保日志目录存在
echo 🔍 确保日志目录存在...
if not exist logs mkdir logs
echo ✅ 日志目录已确认
echo.

REM 4. 启动服务器
echo 🚀 启动服务器...
echo ========================================

REM 激活虚拟环境并启动
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    python web\web_server_refactored.py
) else (
    echo ❌ 未找到虚拟环境，请先运行安装脚本
    pause
    exit /b 1
)

pause
