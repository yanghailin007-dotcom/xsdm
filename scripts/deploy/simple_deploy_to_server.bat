@echo off
chcp 65001 >nul
echo ========================================
echo    简化部署工具
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
echo    步骤 1: 同步代码
echo ========================================
echo.

cd /d d:\work6.05

REM 使用rsync同步（如果可用）
where rsync >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo 使用rsync同步代码...
    rsync -avz -e "ssh -i '%KEY_PATH%' -o StrictHostKeyChecking=no" ^
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' ^
        --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' ^
        --exclude='.env' --exclude='test_*.py' --exclude='*.db' ^
        --exclude='小说项目/*' --exclude='Chrome/*' --exclude='knowledge_base/*' ^
        --exclude='ai_enhanced_settings/*' --exclude='fusion_settings/*' ^
        --exclude='deploy_logs/*' --exclude='node_modules' ^
        . %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/
    
    if %ERRORLEVEL% neq 0 (
        echo ❌ 同步失败
        pause
        exit /b 1
    )
    echo ✓ 同步成功
) else (
    echo rsync不可用，跳过代码同步
)

echo.
echo ========================================
echo    步骤 2: 初始化日志系统
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "mkdir -p /home/novelapp/novel-system/logs && touch /home/novelapp/novel-system/logs/application.log /home/novelapp/novel-system/logs/gunicorn.log /home/novelapp/novel-system/logs/access.log /home/novelapp/novel-system/logs/error.log && echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 日志系统初始化完成' >> /home/novelapp/novel-system/logs/application.log && echo '✓ 日志系统初始化完成'"

echo.
echo ========================================
echo    步骤 3: 重启服务
echo ========================================
echo.

echo 停止旧服务...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp/novel-system && source venv/bin/activate && lsof -ti:5000 | xargs kill -9 2>/dev/null || true"

echo 等待端口释放...
timeout /t 2 /nobreak >nul

echo 启动新服务...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp/novel-system && source venv/bin/activate && nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app > logs/gunicorn.log 2>&1 &"

echo 等待服务启动...
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo    步骤 4: 验证服务状态
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "if lsof -ti:5000 >/dev/null 2>&1; then echo '✓ 服务运行成功'; echo ''; echo '服务信息:'; echo '  端口: 5000'; echo '  PID: '$(lsof -ti:5000); echo ''; echo '访问地址: http://%SERVER_IP%:5000'; echo ''; echo '查看日志:'; echo '  ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "tail -f /home/novelapp/novel-system/logs/application.log"'; else echo '❌ 服务启动失败'; echo ''; echo '请检查日志:'; echo '  ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "tail -50 /home/novelapp/novel-system/logs/error.log"'; fi"

echo.
pause