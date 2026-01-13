@echo off
chcp 65001 >nul
echo ========================================
echo    部署状态检查
echo ========================================
echo.

set SERVER_IP=8.163.37.124
set KEY_PATH=d:\work6.05\xsdm.pem

echo 1. 检查服务器连接...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@%SERVER_IP% "echo '✓ 连接成功'" 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ 连接失败
    goto :end
)
echo.

echo 2. 检查Web服务端口...
ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no root@%SERVER_IP% "lsof -ti:8080 && echo '✓ 端口8080已启动' || echo '❌ 端口8080未启动'" 2>nul
echo.

echo 3. 检查最近的部署日志...
ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no root@%SERVER_IP% "tail -20 /home/novelapp/novel-system/logs/application.log 2>/dev/null || echo '日志文件不存在'" 2>nul
echo.

echo 4. 检查web目录更新时间...
ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no root@%SERVER_IP% "ls -lh /home/novelapp/novel-system/web/static/js/ 2>/dev/null | head -5" 2>nul
echo.

:end
pause