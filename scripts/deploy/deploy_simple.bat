@echo off
REM Simple Deployment Script - Use tar + SCP
REM No complex PowerShell inline commands

setlocal enabledelayedexpansion

set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set KEY_FILE=d:/work6.05/xsdm.pem
set PROJECT_DIR=/home/novelapp/novel-system
set TAR_FILE=novel_deploy_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.tar.gz
set TAR_FILE=%TAR_FILE: =0%

echo ========================================
echo   Simple Deploy Script
echo ========================================
echo.
echo This script will:
echo 1. Create deployment package (exclude large files)
echo 2. Upload to server
echo 3. Configure and start service
echo.

set /p confirm="Start deployment? (y/n): "
if /i not "%confirm%"=="y" (
    echo Deployment cancelled
    pause
    exit /b 0
)

echo.
echo ========================================
echo Step 1: Creating deployment package
echo ========================================
echo.

echo Creating tar.gz package...
tar -czf %TAR_FILE% ^
  --exclude="Chrome" ^
  --exclude=".git" ^
  --exclude=".venv" ^
  --exclude="venv" ^
  --exclude="generated_images" ^
  --exclude="logs" ^
  --exclude="temp_fanqie_upload" ^
  --exclude="chapter_failures" ^
  --exclude="__pycache__" ^
  --exclude="*.pyc" ^
  --exclude="*.pyo" ^
  --exclude=".env" ^
  --exclude="*.db" ^
  --exclude="test_*.py" ^
  --exclude="check_*.py" ^
  --exclude="diagnose_*.py" ^
  --exclude="debug_*.py" ^
  --exclude="*.log" ^
  --exclude=".vscode" ^
  --exclude=".idea" ^
  --exclude=".claude" ^
  --exclude="node_modules" ^
  --exclude="ai_enhanced_settings" ^
  --exclude="fusion_settings" ^
  --exclude="optimized_prompts" ^
  --exclude="knowledge_base" ^
  --exclude="static" ^
  --exclude="data" ^
  --exclude="tests" ^
  --exclude="tools" ^
  --exclude="*.pem" ^
  --exclude="*.key" ^
  --exclude="id_rsa*" ^
  --exclude="Chrome.rar" ^
  -C d:/work6.05 .

if %errorlevel% neq 0 (
    echo [ERROR] Failed to create package
    pause
    exit /b 1
)

echo Package created: %TAR_FILE%

for %%A in ("%TAR_FILE%") do set SIZE=%%~zA
set /a SIZE_MB=%SIZE% / 1048576
echo Package size: %SIZE_MB% MB

echo.
echo ========================================
echo Step 2: Uploading to server
echo ========================================
echo.

echo Uploading package...
scp -i %KEY_FILE% -o StrictHostKeyChecking=no %TAR_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/

if %errorlevel% neq 0 (
    echo [ERROR] Upload failed
    del %TAR_FILE%
    pause
    exit /b 1
)

echo Upload success!

echo.
echo ========================================
echo Step 3: Extract and configure on server
echo ========================================
echo.

echo Uploading startup script...
scp -i %KEY_FILE% -o StrictHostKeyChecking=no scripts/deploy/server_sync_and_start.sh %SERVER_USER%@%SERVER_IP%:/tmp/

echo Extracting and configuring...
ssh -i %KEY_FILE% -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp && mkdir -p novel-system && tar -xzf /tmp/%TAR_FILE% -C novel-system && rm /tmp/%TAR_FILE% && bash /tmp/server_sync_and_start.sh"

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Server configuration may have issues
    echo Please check manually:
    echo ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
    echo.
    del %TAR_FILE%
    pause
    exit /b 1
)

del %TAR_FILE%

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Service started, access URLs:
echo   Local: http://localhost:5000
echo   Public: http://%SERVER_IP%:5000
echo.
echo Common commands:
echo   Check status: ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl status novel-system"
echo   View logs: ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl tail -f novel-system"
echo   Restart: ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl restart novel-system"
echo.

pause