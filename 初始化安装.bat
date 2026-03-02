@echo off
chcp 65001 >nul 2>&1
title 大文娱系统 - 初始化安装
cls
echo.
echo ==========================================
echo   大文娱系统 - 初始化安装
echo ==========================================
echo.
echo 正在检查环境并安装依赖，请稍候...
echo.

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 尝试使用系统 Python
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] 使用系统 Python...
    python setup.py
    goto end
)

REM 检查嵌入式 Python
if exist "%SCRIPT_DIR%python-embed\python.exe" (
    echo [INFO] 使用嵌入式 Python...
    "%SCRIPT_DIR%python-embed\python.exe" setup.py
    goto end
)

REM 尝试用 py 启动器
py --version >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] 使用 py 启动器...
    py setup.py
    goto end
)

echo.
echo 错误: 未找到 Python 环境
echo 将自动下载并安装嵌入式 Python...
echo.

:end
echo.
pause
