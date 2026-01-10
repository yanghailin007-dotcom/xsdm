@echo off
chcp 65001 >nul
echo ========================================
echo    Linux服务器部署工具
echo ========================================
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

echo 服务器信息:
echo   IP: %SERVER_IP%
echo   用户: %SERVER_USER%
echo.

REM 检查私钥
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 设置权限
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

REM 测试连接
echo 测试SSH连接...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo '连接成功'" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ SSH连接失败
    pause
    exit /b 1
)
echo ✓ 连接成功
echo.

REM 上传通用部署脚本
echo 步骤 1/2: 上传通用部署脚本...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no scripts\deploy\universal_deploy.sh %SERVER_USER%@%SERVER_IP%:/tmp/deploy.sh
if %ERRORLEVEL% neq 0 (
    echo ❌ 脚本上传失败
    pause
    exit /b 1
)
echo ✓ 脚本上传成功
echo.

REM 执行部署
echo 步骤 2/2: 执行服务器端部署...
echo.
echo ========================================
echo "正在服务器上执行部署..."
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "chmod +x /tmp/deploy.sh && bash /tmp/deploy.sh"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 部署完成！
    echo ========================================
    echo.
    echo 连接到服务器启动服务：
    echo.
    echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
    echo.
    echo 然后执行：
    echo   cd /home/novelapp/novel-system
    echo   source venv/bin/activate
    echo   gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
    echo.
) else (
    echo.
    echo ❌ 部署失败
    echo.
    echo 请检查服务器环境
    echo 连接到服务器查看详细错误：
    echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
)

pause