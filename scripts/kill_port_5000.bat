@echo off
echo 正在查找占用5000端口的进程...
echo.

:: 查找并杀死所有监听5000端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo 发现进程 PID=%%a
    taskkill /F /PID %%a 2>nul
    if !errorlevel! == 0 (
        echo   [OK] 已杀死进程 PID=%%a
    ) else (
        echo   [FAIL] 无法杀死进程 PID=%%a
    )
)

echo.
echo 清理完成！
pause
