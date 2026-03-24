@echo off
chcp 65001 >nul
title 大文娱创作平台 - 环境启动器

:: 设置脚本所在目录为当前目录
cd /d "%~dp0"

echo ============================================
echo  大文娱创作平台 - 环境启动器
echo ============================================
echo.

:: 检查 chrome_launcher 目录
if not exist "chrome_launcher" (
    echo [错误] 未找到 chrome_launcher 目录
    echo 请确保解压完整包时保留了所有文件
    echo.
    pause
    exit /b 1
)

:: 检查一键启动.bat
if not exist "chrome_launcher\一键启动.bat" (
    echo [错误] 未找到 chrome_launcher\一键启动.bat
    echo.
    pause
    exit /b 1
)

echo [1/1] 正在启动 Chrome 启动器...
echo.

:: 进入 chrome_launcher 目录并运行
cd "chrome_launcher"
call "一键启动.bat"

:: 如果一键启动.bat返回，显示提示
echo.
echo ============================================
echo Chrome 启动器已退出
echo ============================================
echo.
pause
