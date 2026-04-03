@echo off
chcp 65001 >nul
title 小说自动上传工具
echo.
echo ========================================
echo   小说自动上传工具
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
if not exist "venv" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
)

echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

:: 安装依赖
echo [信息] 检查依赖...
pip install -q PyQt5

:: 运行
echo [信息] 启动程序...
echo.
python main.py

:: 退出
deactivate
