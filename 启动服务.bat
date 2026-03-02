@echo off
chcp 65001 >nul
title 大文娱系统 - 启动服务
echo.
echo ==========================================
echo   大文娱系统 - 启动服务
echo ==========================================
echo.

REM 尝试使用嵌入式 Python（优先）
if exist "%~dp0python-embed\python.exe" (
    "%~dp0python-embed\python.exe" start.py
    goto end
)

REM 尝试使用系统 Python
python --version >nul 2>&1
if %errorlevel% == 0 (
    python start.py
    goto end
)

REM 尝试用 py 启动器
py --version >nul 2>&1
if %errorlevel% == 0 (
    py start.py
    goto end
)

echo.
echo ==========================================
echo  错误: 未找到 Python 环境
echo ==========================================
echo.
echo 请先运行 [初始化安装.bat] 进行环境配置
echo.
pause
exit /b 1

:end
echo.
echo 服务已停止
echo.
pause
