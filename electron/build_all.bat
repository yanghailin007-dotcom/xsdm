@echo off
chcp 65001 >nul
echo ========================================
echo 短剧工作室 - Windows桌面版打包工具
echo ========================================
echo.

REM 检查Node.js
where node >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到Node.js，请先安装Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

REM 检查Python
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python
    echo 下载地址: https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] 安装Electron依赖...
cd /d "%~dp0"
if not exist "node_modules" (
    call npm install
    if errorlevel 1 (
        echo [错误] npm install 失败
        pause
        exit /b 1
    )
)

echo.
echo [2/4] 打包Python后端...
call build_backend.bat
if errorlevel 1 (
    echo [错误] 后端打包失败
    pause
    exit /b 1
)

echo.
echo [3/4] 检查图标文件...
if not exist "icon.ico" (
    echo [警告] 未找到icon.ico，将使用默认图标
)
if not exist "icon.png" (
    echo [警告] 未找到icon.png，将使用默认图标
)

echo.
echo [4/4] 打包Electron应用...
call npm run build:win
if errorlevel 1 (
    echo [错误] Electron打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo.
echo 安装包位置: dist\短剧工作室-Setup-1.0.0.exe
echo.
echo 你可以将此安装包分发给用户使用
echo ========================================
pause
