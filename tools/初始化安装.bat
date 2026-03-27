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

REM 尝试使用系统 Python (优先)
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] 使用系统 Python...
    python setup.py
    goto end
)

REM 尝试用 py 启动器 (Windows 用户安装的 Python)
py --version >nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] 使用 py 启动器...
    py setup.py
    goto end
)

REM 没有找到系统 Python
cls
echo.
echo ==========================================
echo   大文娱系统 - 初始化安装
echo ==========================================
echo.
echo  [X] 未检测到 Python 环境
echo.
echo  本系统需要 Python 3.11 或更高版本才能运行。
echo.
echo  请通过以下方式安装 Python：
echo.
echo  方法一（推荐）：从 Microsoft Store 安装
echo       1. 打开 Microsoft Store
echo       2. 搜索 "Python"
echo       3. 安装 Python 3.12 或更高版本
echo.
echo  方法二：从官网下载安装包
echo       1. 访问 https://www.python.org/downloads/
echo       2. 下载 Python 3.12 或更高版本
echo       3. 安装时勾选 "Add Python to PATH"
echo.
echo  安装完成后，重新运行此脚本。
echo.
echo ==========================================
echo.

:end
echo.
pause
