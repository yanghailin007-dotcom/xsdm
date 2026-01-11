@echo off
chcp 65001 >nul
echo ========================================
echo    服务器日志查看工具
echo ========================================
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

echo 服务器: %SERVER_IP%
echo.

if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 设置权限
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo ========================================
echo    选择要查看的日志
echo ========================================
echo.
echo 1. 应用主日志 (application.log) - 推荐首选
echo 2. Gunicorn 日志 (gunicorn.log)
echo 3. 访问日志 (access.log)
echo 4. 错误日志 (error.log)
echo 5. 所有日志 (最新的100行)
echo 6. 实时监控应用日志
echo 7. 实时监控Gunicorn日志
echo 8. 列出所有日志文件
echo.

set /p choice="请选择 (1-8): "

if "%choice%"=="1" (
    echo.
    echo ========================================
    echo    应用主日志 (最近100行)
    echo ========================================
    echo.
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -100 /home/novelapp/novel-system/logs/application.log"
)

if "%choice%"=="2" (
    echo.
    echo ========================================
    echo    Gunicorn 日志 (最近100行)
    echo ========================================
    echo.
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -100 /home/novelapp/novel-system/logs/gunicorn.log"
)

if "%choice%"=="3" (
    echo.
    echo ========================================
    echo    访问日志 (最近100行)
    echo ========================================
    echo.
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -100 /home/novelapp/novel-system/logs/access.log"
)

if "%choice%"=="4" (
    echo.
    echo ========================================
    echo    错误日志 (最近100行)
    echo ========================================
    echo.
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -100 /home/novelapp/novel-system/logs/error.log"
)

if "%choice%"=="5" (
    echo.
    echo ========================================
    echo    所有日志 (最近100行)
    echo ========================================
    echo.
    echo === 应用日志 ===
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -50 /home/novelapp/novel-system/logs/application.log"
    echo.
    echo === Gunicorn 日志 ===
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -50 /home/novelapp/novel-system/logs/gunicorn.log"
    echo.
    echo === 错误日志 ===
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -50 /home/novelapp/novel-system/logs/error.log"
)

if "%choice%"=="6" (
    echo.
    echo ========================================
    echo    实时监控应用日志
    echo ========================================
    echo.
    echo 按 Ctrl+C 退出监控
    echo.
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -f /home/novelapp/novel-system/logs/application.log"
)

if "%choice%"=="7" (
    echo.
    echo ========================================
    echo    实时监控Gunicorn日志
    echo ========================================
    echo.
    echo 按 Ctrl+C 退出监控
    echo.
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "tail -f /home/novelapp/novel-system/logs/gunicorn.log"
)

if "%choice%"=="8" (
    echo.
    echo ========================================
    echo    日志文件列表
    echo ========================================
    echo.
    ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "ls -lh /home/novelapp/novel-system/logs/"
)

echo.
pause