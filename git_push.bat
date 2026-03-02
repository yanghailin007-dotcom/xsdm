@echo off
chcp 65001 >nul
echo ==========================================
echo   Git 推送脚本
echo ==========================================
echo.

set "GIT_EXE=C:\Program Files\Git\bin\git.exe"

if not exist "%GIT_EXE%" (
    echo 错误：找不到 Git！
    echo 请确保 Git 已安装。
    pause
    exit /b 1
)

cd /d "%~dp0"

echo 当前目录: %CD%
echo.

echo [1/3] 检查 Git 状态...
"%GIT_EXE%" status
echo.

echo [2/3] 查看提交历史...
"%GIT_EXE%" log --oneline -3
echo.

echo [3/3] 推送到远程仓库...
echo 正在推送，请稍候...
"%GIT_EXE%" push origin main

if %errorlevel% == 0 (
    echo.
    echo ==========================================
    echo   推送成功！
    echo ==========================================
) else (
    echo.
    echo ==========================================
    echo   推送失败，请检查网络连接
    echo ==========================================
)

pause
