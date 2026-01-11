@echo off
echo ========================================
echo 正在清理Python缓存并重启服务器...
echo ========================================

REM 1. 停止所有Python进程
echo.
echo [1/4] 停止所有Python进程...
taskkill /F /IM python.exe /T 2>nul

REM 2. 清除所有Python缓存
echo.
echo [2/4] 清除Python缓存...
del /s /q d:\work6.05\__pycache__ 2>nul
del /s /q d:\work6.05\*.pyc 2>nul
del /s /q d:\work6.05\**\__pycache__ 2>nul
del /s /q d:\work6.05\**\*.pyc 2>nul

REM 3. 等待文件释放
echo.
echo [3/4] 等待文件释放...
timeout /t 2 /nobreak >nul

REM 4. 重新启动服务器
echo.
echo [4/4] 重新启动服务器...
echo.
cd /d "d:\work6.05"
start "" python scripts/start_server.py

echo.
echo ========================================
echo 服务器已重启！
echo ========================================
pause