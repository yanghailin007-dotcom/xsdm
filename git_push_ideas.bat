@echo off
chcp 65001 >nul
echo ==========================================
echo   推送创意更新到 GitHub
echo ==========================================
echo.

cd /d "%~dp0"

set "GIT_EXE=C:\Program Files\Git\bin\git.exe"

echo 正在推送...
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
