@echo off
chcp 65001 >nul
echo ========================================
echo    同步代码到服务器
echo ========================================
echo.

set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

echo 服务器: %SERVER_IP%
echo 本地目录: d:\work6.05
echo 远程目录: /home/novelapp/novel-system
echo.

if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo 正在同步文件（只同步修改过的文件）...
echo.

REM 使用rsync同步文件（如果可用）
where rsync >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo 使用rsync同步（更快，只传输修改的文件）...
    rsync -avz -e "ssh -i '%KEY_PATH%' -o StrictHostKeyChecking=no" ^
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' ^
        --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' ^
        --exclude='.env' --exclude='test_*.py' --exclude='*.db' ^
        --exclude='小说项目/*' --exclude='Chrome/*' --exclude='knowledge_base/*' ^
        --exclude='ai_enhanced_settings/*' --exclude='fusion_settings/*' ^
        . %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/
    
    if %ERRORLEVEL% equ 0 (
        echo ✓ 同步成功
        echo.
        
        echo 重启服务器上的服务...
        ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp/novel-system && source venv/bin/activate && lsof -ti:5000 | xargs kill -9 2>/dev/null; nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app > logs/gunicorn.log 2>&1 &"
        
        echo.
        echo ========================================
        echo    ✓ 同步并重启完成！
        echo ========================================
        echo.
        echo 访问网站: http://8.163.37.124:5000
        echo 查看日志:
        echo   ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "tail -f /home/novelapp/novel-system/logs/gunicorn.log"
        echo.
        pause
        exit /b 0
    else
        echo ❌ rsync同步失败，尝试使用scp...
    )
)

echo rsync不可用，使用scp上传关键文件...
echo.
echo 正在上传核心文件...

REM 上传WSGI入口文件（如果有修改）
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no web\wsgi.py %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/

REM 上传启动脚本
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no scripts\start_app.py %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/scripts/

echo ✓ 文件上传完成
echo.

echo 需要手动重启服务器上的服务：
echo.
echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
echo.
echo 然后执行：
echo   cd /home/novelapp/novel-system
echo   source venv/bin/activate
echo   python scripts/start_app.py
echo.

pause