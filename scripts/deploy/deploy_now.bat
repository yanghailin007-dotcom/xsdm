@echo off
REM FINAL DEPLOYMENT SCRIPT - Fixed Version
REM Creates tar in temp directory to avoid self-inclusion

setlocal enabledelayedexpansion

set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set KEY_FILE=d:\work6.05\xsdm.pem
set TEMP_DIR=%TEMP%\novel_deploy
set TAR_FILE=%TEMP_DIR%\novel_deploy.tar.gz

echo ========================================
echo   Deployment Script - Fixed Version
echo ========================================
echo.
echo This will:
echo 1. Create tar.gz package (~30MB)
echo 2. Upload to server
echo 3. Extract and configure
echo 4. Start service
echo.

REM Check if key file exists
if not exist "%KEY_FILE%" (
    echo ERROR: SSH key file not found: %KEY_FILE%
    echo Please check the key file path.
    pause
    exit /b 1
)

echo Using SSH key: %KEY_FILE%
echo.

set /p confirm="Start deployment? (y/n): "
if /i not "%confirm%"=="y" (
    echo Cancelled
    pause
    exit /b 0
)

cd /d d:\work6.05

echo.
echo [Step 1/4] Creating deployment package...
echo.

REM Create temp directory
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

if exist "%TAR_FILE%" del "%TAR_FILE%"

REM Create tar.gz with exclusions
tar -czf "%TAR_FILE%" ^
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
  .

if not exist "%TAR_FILE%" (
    echo ERROR: Failed to create package
    rmdir /s /q "%TEMP_DIR%"
    pause
    exit /b 1
)

for %%A in ("%TAR_FILE%") do set SIZE=%%~zA
set /a SIZE_MB=%SIZE% / 1048576
echo Package created: %SIZE_MB% MB

echo.
echo [Step 2/4] Uploading to server...
echo.

scp -i "%KEY_FILE%" -o StrictHostKeyChecking=no "%TAR_FILE%" %SERVER_USER%@%SERVER_IP%:/tmp/

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Upload failed - SSH connection issue
    echo.
    echo Troubleshooting:
    echo 1. Check if key file exists: %KEY_FILE%
    echo 2. Try manual test: ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
    echo 3. Check key permissions on server
    echo.
    rmdir /s /q "%TEMP_DIR%"
    pause
    exit /b 1
)

echo Upload complete

echo.
echo [Step 3/4] Uploading startup script...
echo.

scp -i "%KEY_FILE%" -o StrictHostKeyChecking=no scripts/deploy/server_sync_and_start.sh %SERVER_USER%@%SERVER_IP%:/tmp/

if %errorlevel% neq 0 (
    echo ERROR: Startup script upload failed
    rmdir /s /q "%TEMP_DIR%"
    pause
    exit /b 1
)

echo.
echo [Step 4/4] Extracting and configuring on server...
echo.

ssh -i "%KEY_FILE%" -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "cd /home/novelapp && mkdir -p novel-system && tar -xzf /tmp/novel_deploy.tar.gz -C novel-system && rm /tmp/novel_deploy.tar.gz && bash /tmp/server_sync_and_start.sh"

if %errorlevel% neq 0 (
    echo.
    echo WARNING: Server configuration may have issues
    echo Please check manually:
    echo ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
    echo.
    rmdir /s /q "%TEMP_DIR%"
    pause
    exit /b 1
)

REM Cleanup
rmdir /s /q "%TEMP_DIR%"

echo.
echo ========================================
echo DEPLOYMENT SUCCESSFUL!
echo ========================================
echo.
echo Service is running at:
echo   http://%SERVER_IP%:5000
echo.
echo Management commands:
echo   Status: ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl status novel-system"
echo   Logs:   ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl tail -f novel-system"
echo   Restart:ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl restart novel-system"
echo.

pause