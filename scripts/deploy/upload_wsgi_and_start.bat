@echo off
chcp 65001 >nul
echo ========================================
echo    上传WSGI文件并启动服务
echo ========================================
echo.

set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo 正在上传WSGI入口文件...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no web\wsgi.py %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/

if %ERRORLEVEL% neq 0 (
    echo ❌ 上传失败
    pause
    exit /b 1
)

echo ✓ WSGI文件上传成功
echo.

echo 正在启动服务...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp/novel-system && source venv/bin/activate && nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app > /dev/null 2>&1 &"

echo.
echo ========================================
echo    ✓ 服务启动命令已执行！
echo ========================================
echo.
echo 服务正在后台启动，请稍等片刻...
echo.
echo 访问网站: http://8.163.37.124:5000
echo.
echo 查看日志:
echo   ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
echo.
echo 然后执行:
echo   tail -f /home/novelapp/novel-system/logs/*.log
echo.
pause