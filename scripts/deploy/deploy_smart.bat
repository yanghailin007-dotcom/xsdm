@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    智能部署系统 - 增量同步 + 重启
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

REM 读取配置
for /f "tokens=1,2,3,4" %%a in ('python -c "import configparser; c=configparser.ConfigParser(); c.read(r'%CONFIG_FILE%'); print(c['server']['ip'], c['server']['user'], c['server']['key_path'], c['server']['remote_project_path'])"') do (
    set SERVER_IP=%%a
    set SERVER_USER=%%b
    set KEY_PATH=%%c
    set REMOTE_PATH=%%d
)

echo 服务器: %SERVER_IP%
echo 本地路径: %PROJECT_ROOT%
echo 远程路径: %REMOTE_PATH%
echo.

REM 检查私钥文件
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 修复私钥权限
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo ========================================
echo 步骤 1/3: 检测同步工具
echo ========================================
echo.

REM 检查是否有Git Bash的rsync
set "RSYNC_PATH="
if exist "C:\Program Files\Git\usr\bin\rsync.exe" (
    set "RSYNC_PATH=C:\Program Files\Git\usr\bin\rsync.exe"
    echo ✓ 找到Git Bash的rsync
) else if exist "C:\Program Files\Git\mingw64\bin\rsync.exe" (
    set "RSYNC_PATH=C:\Program Files\Git\mingw64\bin\rsync.exe"
    echo ✓ 找到Git Bash的rsync
) else (
    where rsync >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        set "RSYNC_PATH=rsync"
        echo ✓ 找到系统rsync
    ) else (
        echo ⚠️  未找到rsync，将使用scp同步
        echo.
        echo 提示: 安装Git for Windows可以获得rsync支持
        echo 下载: https://git-scm.com/download/win
        echo.
    )
)

echo.
echo ========================================
echo 步骤 2/3: 同步文件到服务器
echo ========================================
echo.

if defined RSYNC_PATH (
    echo 使用rsync增量同步（只传输修改的文件）...
    echo.
    
    REM 创建临时排除文件
    set EXCLUDE_FILE=%TEMP%\rsync_exclude.txt
    (
        echo - __pycache__
        echo - *.pyc
        echo - .git
        echo - logs/*
        echo - generated_images/*
        echo - temp_fanqie_upload/*
        echo - .env
        echo - test_*.py
        echo - *.db
        echo - 小说项目/*
        echo - Chrome/*
        echo - knowledge_base/*
        echo - ai_enhanced_settings/*
        echo - fusion_settings/*
        echo - .vscode
        echo - node_modules
        echo - venv
        echo - *.bat
        echo - deploy_config.ini
        echo - STABLE_DEPLOYMENT_GUIDE.md
    ) > "%EXCLUDE_FILE%"
    
    REM 使用rsync同步
    "%RSYNC_PATH%" -avz --delete --exclude-from="%EXCLUDE_FILE%" ^
        -e "ssh -i '%KEY_PATH%' -o StrictHostKeyChecking=no" ^
        "%PROJECT_ROOT%/." ^
        %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/.
    
    del "%EXCLUDE_FILE%" 2>nul
    
    if !ERRORLEVEL! equ 0 (
        echo ✓ rsync同步成功
    ) else (
        echo ⚠️ rsync同步失败，尝试使用scp...
        goto :use_scp
    )
) else (
    :use_scp
    echo 使用scp同步文件...
    echo.
    
    REM 只同步核心目录和文件
    echo 正在上传核心目录...
    
    REM 上传源代码
    scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no -r ^
        "%PROJECT_ROOT%/src" ^
        %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/
    
    REM 上传Web文件
    scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no -r ^
        "%PROJECT_ROOT%/web" ^
        %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/
    
    REM 上传配置和脚本
    scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no -r ^
        "%PROJECT_ROOT%/config" ^
        "%PROJECT_ROOT%/scripts" ^
        %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/
    
    REM 上传重要文件
    scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no ^
        "%PROJECT_ROOT%/requirements.txt" ^
        "%PROJECT_ROOT%/web/wsgi.py" ^
        "%PROJECT_ROOT%/scripts/start_app.py" ^
        %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/
    
    if !ERRORLEVEL! neq 0 (
        echo ❌ 文件同步失败
        pause
        exit /b 1
    )
    echo ✓ scp同步完成
)

echo.

echo ========================================
echo 步骤 3/3: 上传部署脚本并执行
echo ========================================
echo.

REM 上传服务器端部署脚本
echo 正在上传服务器部署脚本...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no ^
    "%SCRIPT_DIR%server_deploy_stable.sh" ^
    %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/scripts/deploy/

if !ERRORLEVEL! neq 0 (
    echo ❌ 上传部署脚本失败
    pause
    exit /b 1
)

echo ✓ 部署脚本已上传
echo.

echo 正在执行服务器部署...
echo.
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% ^
    "cd %REMOTE_PATH% && chmod +x scripts/deploy/server_deploy_stable.sh && bash scripts/deploy/server_deploy_stable.sh"

if !ERRORLEVEL! neq 0 (
    echo ❌ 服务器部署失败
    pause
    exit /b 1
)

echo.

echo ========================================
echo    ✓ 部署完成！
echo ========================================
echo.
echo 访问地址: http://%SERVER_IP%:5000
echo.
echo 管理命令:
echo   查看日志: ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "tail -f %REMOTE_PATH%/logs/gunicorn.log"
echo   停止服务: ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "kill \$(cat %REMOTE_PATH%/logs/gunicorn.pid)"
echo   重启服务: 运行 restart_server.bat 或本脚本
echo.

pause