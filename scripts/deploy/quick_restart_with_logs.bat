@echo off
chcp 65001 >nul
echo ========================================
echo    快速重启服务 (带日志)
echo ========================================
echo.
echo 说明: 此脚本用于代码已同步，只需重启服务的场景
echo.

REM 设置日志
set LOG_DIR=deploy_logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_FILE=%LOG_DIR%\restart_%TIMESTAMP%.log

echo 日志文件: %LOG_FILE%
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

echo 服务器: %SERVER_IP%
echo.

if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH% >> %LOG_FILE%
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 设置权限
echo [%TIME%] 设置私钥权限... >> %LOG_FILE%
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo ========================================
echo    步骤 1/2: 同步代码
echo ========================================
echo.

echo [%TIME%] 开始同步代码... >> %LOG_FILE%
cd /d d:\work6.05

REM 使用rsync同步（如果可用）
where rsync >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo 使用rsync同步... >> %LOG_FILE%
    echo 使用rsync同步（更快）...
    
    rsync -avz -e "ssh -i '%KEY_PATH%' -o StrictHostKeyChecking=no" ^
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' ^
        --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' ^
        --exclude='.env' --exclude='test_*.py' --exclude='*.db' ^
        --exclude='小说项目/*' --exclude='Chrome/*' --exclude='knowledge_base/*' ^
        --exclude='ai_enhanced_settings/*' --exclude='fusion_settings/*' ^
        --exclude='deploy_logs/*' ^
        . %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/ 2>> %LOG_FILE%
    
    if %ERRORLEVEL% equ 0 (
        echo ✓ 代码同步成功 >> %LOG_FILE%
        echo ✓ 代码同步成功
    ) else (
        echo ❌ rsync同步失败 >> %LOG_FILE%
        echo ❌ 同步失败，查看日志: %LOG_FILE%
        pause
        exit /b 1
    )
) else (
    echo rsync不可用，跳过代码同步... >> %LOG_FILE%
    echo rsync不可用，跳过代码同步步骤
)

echo.
echo ========================================
echo    步骤 2/2: 重启服务
echo ========================================
echo.

echo [%TIME%] 开始重启服务... >> %LOG_FILE%
echo 重启服务器上的服务...

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp/novel-system && source venv/bin/activate && lsof -ti:5000 | xargs kill -9 2>/dev/null; echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 服务已停止' >> logs/application.log; nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log --log-level info web.wsgi:app > logs/gunicorn.log 2>&1 & sleep 3; if lsof -ti:5000 >/dev/null 2>&1; then echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] ✓ 服务重启成功' >> logs/application.log && echo '✓ 服务重启成功'; else echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] ❌ 服务重启失败' >> logs/application.log && echo '❌ 服务重启失败'; fi" >> %LOG_FILE% 2>&1

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 重启完成！
    echo ========================================
    echo.
    echo 服务已重启并运行在服务器上。
    echo.
    echo 访问网站: http://%SERVER_IP%:5000
    echo.
    echo 查看日志:
    echo   本地: %LOG_FILE%
    echo   服务器: /home/novelapp/novel-system/logs/application.log
    echo.
    echo 快速查看服务器日志命令:
    echo   scripts\deploy\view_server_logs.bat
    echo.
) else (
    echo.
    echo ❌ 重启过程中出现错误
    echo.
    echo 请查看日志: %LOG_FILE%
    echo.
)

pause