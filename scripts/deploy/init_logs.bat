@echo off
chcp 65001 >nul
echo ========================================
echo    初始化服务器日志系统
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

echo 正在上传初始化脚本...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no scripts/deploy/init_logs_on_server.sh %SERVER_USER%@%SERVER_IP%:/tmp/

if %ERRORLEVEL% neq 0 (
    echo ❌ 脚本上传失败
    pause
    exit /b 1
)

echo ✓ 脚本上传成功
echo.

echo 正在执行初始化...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash /tmp/init_logs_on_server.sh"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 日志系统初始化完成！
    echo ========================================
    echo.
    echo 现在可以使用 view_server_logs.bat 查看日志了
    echo.
) else (
    echo.
    echo ❌ 初始化失败
    echo.
)

pause