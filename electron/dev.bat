@echo off
chcp 65001 >nul
echo ========================================
echo 短剧工作室 - 开发模式
echo ========================================
echo.

REM 检查依赖
if not exist "node_modules" (
    echo 正在安装依赖...
    call npm install
)

echo 启动开发模式...
echo.
echo 提示:
echo - Flask服务器将在后台启动
echo - Electron窗口将自动打开
echo - 按Ctrl+C停止
echo.

call npm run dev
