@echo off
chcp 65001 >nul
title 大文娱系统 - 初始化安装
echo.
echo ==========================================
echo   大文娱系统 - 初始化安装
echo ==========================================
echo.
echo 正在检查环境并安装依赖，请稍候...
echo.

REM 尝试使用系统 Python
python --version >nul 2>&1
if %errorlevel% == 0 (
    python setup.py
    goto end
)

REM 检查嵌入式 Python
if exist "%~dp0python-embed\python.exe" (
    "%~dp0python-embed\python.exe" setup.py
    goto end
)

REM 都没有，尝试用 py 启动器
py --version >nul 2>&1
if %errorlevel% == 0 (
    py setup.py
    goto end
)

echo 错误: 未找到 Python 环境
echo 将使用嵌入式 Python 自动安装...
echo.
pause

:end
echo.
echo 按任意键退出...
pause >nul
