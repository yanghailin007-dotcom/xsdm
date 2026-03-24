@echo off
chcp 65001 >nul
echo ============================================
echo Python Environment Check
echo ============================================
echo.

python --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Python installed
    python --version
    echo.
    echo You can run start.bat
) else (
    echo [X] Python not installed
    echo.
    echo Please run start.bat to install Python
    echo Or visit https://www.python.org/downloads/
)

echo.
pause
