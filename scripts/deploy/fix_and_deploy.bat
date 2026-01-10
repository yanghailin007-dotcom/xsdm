@echo off
chcp 65001 >nul
echo ========================================
echo    修复依赖并部署
echo ========================================
echo.

set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

echo 服务器: %SERVER_IP%
echo.

echo 正在上传修复脚本...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no scripts\deploy\fix_dependencies.sh %SERVER_USER%@%SERVER_IP%:/tmp/fix.sh

if %ERRORLEVEL% neq 0 (
    echo ❌ 上传失败
    pause
    exit /b 1
)

echo ✓ 脚本上传成功
echo.

echo 正在执行修复...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "chmod +x /tmp/fix.sh && bash /tmp/fix.sh"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 修复成功！
    echo ========================================
    echo.
    echo 现在可以启动服务了：
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
    echo ❌ 修复失败
    echo.
    echo 可能需要升级Python版本
    echo 请连接到服务器查看详细错误：
    echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
)

pause