@echo off
chcp 65001 >nul
echo ========================================
echo    同步修改并重新部署
echo ========================================
echo.

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

icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo 正在同步修改后的部署脚本...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no scripts\deploy\alibaba_cloud_deploy.sh %SERVER_USER%@%SERVER_IP%:/tmp/deploy.sh

if %ERRORLEVEL% neq 0 (
    echo ❌ 上传失败
    pause
    exit /b 1
)

echo ✓ 脚本同步成功
echo.

echo 正在执行部署（使用修复后的脚本）...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "chmod +x /tmp/deploy.sh && bash /tmp/deploy.sh"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 部署完成！
    echo ========================================
    echo.
    echo 现在启动服务：
    echo.
    echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
    echo.
    echo 然后执行：
    echo   cd /home/novelapp/novel-system
    echo   source venv/bin/activate
    echo   gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
    echo.
    echo 访问: http://8.163.37.124:5000
    echo.
) else (
    echo.
    echo 部署过程中出现警告，但代码已经部署完成
    echo.
    echo 可以直接启动服务：
    echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
    echo.
    echo cd /home/novelapp/novel-system
    echo source venv/bin/activate
    echo gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
)

pause