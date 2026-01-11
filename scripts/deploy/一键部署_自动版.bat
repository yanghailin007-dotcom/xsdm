@echo off
chcp 65001 >nul
echo ========================================
echo    小说生成系统 - 一键部署（自动版）
echo ========================================
echo.
echo 此脚本将自动完成：
echo   ✓ 同步所有代码（包括前端UI文件）
echo   ✓ 初始化日志系统
echo   ✓ 重启服务
echo   ✓ 验证部署状态
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

echo 服务器: %SERVER_IP%
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
echo ✓ SSH连接成功
echo.

REM 进入项目目录
cd /d d:\work6.05

echo ========================================
echo    步骤 1/4: 同步代码
echo ========================================
echo.

REM 检查rsync
where rsync >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo 使用rsync同步所有文件...
    echo 包括：Python代码、前端UI（CSS/JS/HTML）、配置文件等
    
    rsync -avz -e "ssh -i '%KEY_PATH%' -o StrictHostKeyChecking=no" ^
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' ^
        --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' ^
        --exclude='.env' --exclude='test_*.py' --exclude='check_*.py' --exclude='diagnose_*.py' ^
        --exclude='debug_*.py' --exclude='*.log' --exclude='.vscode' --exclude='.idea' ^
        --exclude='.claude' --exclude='node_modules' --exclude='deploy_logs/*' ^
        --exclude='小说项目/*' --exclude='Chrome/*' --exclude='knowledge_base/*' ^
        --exclude='ai_enhanced_settings/*' --exclude='fusion_settings/*' ^
        --exclude='optimized_prompts/*' --exclude='data/*.db' --exclude='tests/*' ^
        --exclude='tools/*' --exclude='*.pem' --exclude='*.key' --exclude='id_rsa*' ^
        . %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/
    
    if %ERRORLEVEL% equ 0 (
        echo ✓ 代码同步成功
    ) else (
        echo ❌ 代码同步失败
        pause
        exit /b 1
    )
) else (
    echo rsync不可用，使用scp同步关键文件...
    echo.
    echo 上传Python代码...
    scp -i "%KEY_PATH%" -r -o StrictHostKeyChecking=no web %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/
    scp -i "%KEY_PATH%" -r -o StrictHostKeyChecking=no src %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/
    
    echo.
    echo 上传前端UI文件...
    scp -i "%KEY_PATH%" -r -o StrictHostKeyChecking=no web/static %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/
    scp -i "%KEY_PATH%" -r -o StrictHostKeyChecking=no web/templates %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/
    
    echo.
    echo 上传配置文件...
    scp -i "%KEY_PATH%" -r -o StrictHostKeyChecking=no config %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/
    scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no requirements.txt %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/
    
    echo ✓ 文件上传完成
)

echo.
echo ========================================
echo    步骤 2/4: 初始化日志系统
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "mkdir -p /home/novelapp/novel-system/logs && touch /home/novelapp/novel-system/logs/application.log /home/novelapp/novel-system/logs/gunicorn.log /home/novelapp/novel-system/logs/access.log /home/novelapp/novel-system/logs/error.log && echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 日志系统初始化完成' >> /home/novelapp/novel-system/logs/application.log && echo '✓ 日志系统初始化完成'"

echo.
echo ========================================
echo    步骤 3/4: 重启服务
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
echo    步骤 4/4: 验证部署
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "if lsof -ti:5000 >/dev/null 2>&1; then echo ''; echo '========================================'; echo '   ✓ 部署成功！'; echo '========================================'; echo ''; echo '服务信息:'; echo '  端口: 5000'; echo '  PID: '$(lsof -ti:5000); echo ''; echo '访问地址: http://%SERVER_IP%:5000'; echo ''; echo '重要提示:'; echo '  1. 请强制刷新浏览器（Ctrl+F5）查看UI更新'; echo '  2. 如果UI没有更新，清除浏览器缓存后重试'; echo ''; echo '查看日志:'; echo '  运行: scripts/deploy/view_server_logs.bat'; echo '  或手动: ssh -i \"%KEY_PATH%\" %SERVER_USER%@%SERVER_IP% \"tail -f /home/novelapp/novel-system/logs/application.log\"'; echo ''; else echo ''; echo '========================================'; echo '   ❌ 部署失败'; echo '========================================'; echo ''; echo '请检查日志:'; echo '  ssh -i \"%KEY_PATH%\" %SERVER_USER%@%SERVER_IP% \"tail -50 /home/novelapp/novel-system/logs/error.log\"'; echo ''; fi"

echo.
pause