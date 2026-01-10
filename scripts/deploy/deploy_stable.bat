@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    稳定部署系统 - 一键部署
echo ========================================
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..

REM 配置文件路径
set CONFIG_FILE=%SCRIPT_DIR%deploy_config.ini

REM 检查配置文件
if not exist "%CONFIG_FILE%" (
    echo ❌ 配置文件不存在: %CONFIG_FILE%
    pause
    exit /b 1
)

REM 读取配置（使用临时Python脚本）
set PYTHON_SCRIPT=%TEMP%\read_config.py

echo import configparser > "%PYTHON_SCRIPT%"
echo import sys >> "%PYTHON_SCRIPT%"
echo config = configparser.ConfigParser() >> "%PYTHON_SCRIPT%"
echo config.read(r'%CONFIG_FILE%') >> "%PYTHON_SCRIPT%"
echo print(config['server']['ip']) >> "%PYTHON_SCRIPT%"
echo print(config['server']['user']) >> "%PYTHON_SCRIPT%"
echo print(config['server']['key_path']) >> "%PYTHON_SCRIPT%"
echo print(config['server']['remote_project_path']) >> "%PYTHON_SCRIPT%"

for /f "tokens=1,2,3,4" %%a in ('python "%PYTHON_SCRIPT%"') do (
    set SERVER_IP=%%a
    set SERVER_USER=%%b
    set KEY_PATH=%%c
    set REMOTE_PATH=%%d
)

del "%PYTHON_SCRIPT%"

echo 服务器信息:
echo   IP: %SERVER_IP%
echo   用户: %SERVER_USER%
echo   项目路径: %REMOTE_PATH%
echo.

REM 检查私钥文件
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 修复私钥权限
echo 修复私钥文件权限...
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1
echo ✓ 权限已修复
echo.

echo ========================================
echo 步骤 1/4: 上传服务器部署脚本
echo ========================================
echo.

scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no ^
    "%SCRIPT_DIR%server_deploy_stable.sh" ^
    %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/scripts/deploy/

if %ERRORLEVEL% neq 0 (
    echo ❌ 上传部署脚本失败
    pause
    exit /b 1
)

echo ✓ 部署脚本已上传
echo.

echo ========================================
echo 步骤 2/4: 同步核心文件
echo ========================================
echo.

REM 创建临时排除文件
set EXCLUDE_FILE=%TEMP%\rsync_exclude.txt
echo __pycache__ > "%EXCLUDE_FILE%"
echo *.pyc >> "%EXCLUDE_FILE%"
echo .git >> "%EXCLUDE_FILE%"
echo logs/ >> "%EXCLUDE_FILE%"
echo generated_images/ >> "%EXCLUDE_FILE%"
echo temp_fanqie_upload/ >> "%EXCLUDE_FILE%"
echo .env >> "%EXCLUDE_FILE%"
echo test_*.py >> "%EXCLUDE_FILE%"
echo *.db >> "%EXCLUDE_FILE%"
echo 小说项目/ >> "%EXCLUDE_FILE%"
echo Chrome/ >> "%EXCLUDE_FILE%"
echo knowledge_base/ >> "%EXCLUDE_FILE%"
echo ai_enhanced_settings/ >> "%EXCLUDE_FILE%"
echo fusion_settings/ >> "%EXCLUDE_FILE%"
echo *.bat >> "%EXCLUDE_FILE%"
echo deploy_config.ini >> "%EXCLUDE_FILE%"

REM 检查是否使用rsync
where rsync >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo 使用rsync同步文件...
    rsync -avz --delete --exclude-from="%EXCLUDE_FILE%" ^
        -e "ssh -i '%KEY_PATH%' -o StrictHostKeyChecking=no" ^
        "%PROJECT_ROOT%/" ^
        %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/,
    
    if %ERRORLEVEL% equ 0 (
        echo ✓ 文件同步成功
    ) else (
        echo ⚠️ rsync同步失败，尝试使用scp...
        goto :use_scp
    )
) else (
    :use_scp
    echo rsync不可用，使用scp同步关键文件...
    
    REM 上传核心目录
    scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no -r ^
        "%PROJECT_ROOT%/src" ^
        "%PROJECT_ROOT%/web" ^
        "%PROJECT_ROOT%/config" ^
        "%PROJECT_ROOT%/scripts" ^
        %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/
    
    REM 上传重要文件
    scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no ^
        "%PROJECT_ROOT%/requirements.txt" ^
        "%PROJECT_ROOT%/web/wsgi.py" ^
        "%PROJECT_ROOT%/scripts/start_app.py" ^
        %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/
    
    if %ERRORLEVEL% neq 0 (
        echo ❌ 文件同步失败
        del "%EXCLUDE_FILE%" 2>nul
        pause
        exit /b 1
    )
    echo ✓ 文件同步完成
)

del "%EXCLUDE_FILE%" 2>nul
echo.

echo ========================================
echo 步骤 3/4: 执行服务器部署
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% ^
    "cd %REMOTE_PATH% && chmod +x scripts/deploy/server_deploy_stable.sh && bash scripts/deploy/server_deploy_stable.sh"

if %ERRORLEVEL% neq 0 (
    echo ❌ 服务器部署失败
    pause
    exit /b 1
)

echo.

echo ========================================
echo 步骤 4/4: 验证部署结果
echo ========================================
echo.

echo 等待服务启动...
timeout /t 5 /nobreak >nul

echo 检查服务状态...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% ^
    "cd %REMOTE_PATH% && if [ -f logs/gunicorn.pid ]; then pid=\$(cat logs/gunicorn.pid); if ps -p \$pid > /dev/null 2>&1; then echo '✓ 服务运行正常 (PID: '\$pid')'; else echo '❌ 服务未运行'; fi; else echo '❌ PID文件不存在'; fi"

echo.

echo ========================================
echo    ✓ 部署完成！
echo ========================================
echo.
echo 访问地址: http://%SERVER_IP%:5000
echo.
echo 管理命令:
echo   查看日志: 
echo     ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
echo     tail -f %REMOTE_PATH%/logs/gunicorn.log
echo.
echo   停止服务:
echo     ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
echo     kill \$(cat %REMOTE_PATH%/logs/gunicorn.pid)
echo.
echo   重启服务:
echo     重新运行本脚本
echo.

pause