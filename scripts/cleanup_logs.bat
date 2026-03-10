@echo off
chcp 65001 >nul
echo ===========================================
echo  清理调试日志文件 (保留最近3天)
echo ===========================================

set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%cleanup_debug_logs.py

:: 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请确保 Python 已添加到 PATH
    exit /b 1
)

:: 运行清理脚本
python "%PYTHON_SCRIPT%" --keep-days 3

if errorlevel 1 (
    echo [WARNING] 清理过程出现错误
) else (
    echo [OK] 清理完成
)

echo.
pause
