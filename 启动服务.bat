@echo off
chcp 65001 >nul 2>&1
title 大文娱系统 - 启动服务
cls
echo.
echo ==========================================
echo   大文娱系统 - 启动服务
echo ==========================================
echo.

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 尝试使用嵌入式 Python（优先）
if exist "%SCRIPT_DIR%python-embed\python.exe" (
    echo [INFO] 使用嵌入式 Python...
    "%SCRIPT_DIR%python-embed\python.exe" "%SCRIPT_DIR%start.py"
    goto end
)

REM 尝试使用系统 Python
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] 使用系统 Python...
    python start.py
    goto end
)

REM 尝试用 py 启动器
py --version >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] 使用 py 启动器...
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
echo ==========================================
echo  服务已停止
echo ==========================================
echo.
pause
