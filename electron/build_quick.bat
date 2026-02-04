@echo off
chcp 65001 >nul
echo ========================================
echo 短剧工作室 - 快速测试打包（开发版）
echo ========================================
echo.
echo 此版本不打包Python后端，适合快速测试
echo.

cd /d "%~dp0"

echo [1/2] 检查Node.js依赖...
if not exist "node_modules" (
    echo 正在安装依赖...
    call npm install
    if errorlevel 1 (
        echo [错误] npm install 失败
        pause
        exit /b 1
    )
)

echo.
echo [2/2] 打包Electron应用（开发模式）...
call npm run build:dir
if errorlevel 1 (
    echo [错误] Electron打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo.
echo 输出目录: dist\win-unpacked
echo.
echo 运行方式:
echo 1. 进入 dist\win-unpacked 目录
echo 2. 双击 "短剧工作室.exe"
echo 3. 确保项目根目录的Python环境可用
echo ========================================
pause
