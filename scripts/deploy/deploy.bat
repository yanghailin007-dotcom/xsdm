@echo off
REM Full Deployment Script - Sync and Auto Configure
REM No Chinese characters to avoid encoding issues

setlocal enabledelayedexpansion

set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set KEY_FILE=d:/work6.05/xsdm.pem
set PROJECT_DIR=/home/novelapp/novel-system

echo ========================================
echo   Full Deploy Script - Sync + Configure
echo ========================================
echo.
echo This script will:
echo 1. Sync code to server (exclude large files)
echo 2. Auto configure server environment
echo 3. Clean old processes
echo 4. Install dependencies
echo 5. Start service
echo.

set /p confirm="Start deployment? (y/n): "
if /i not "%confirm%"=="y" (
    echo Deployment cancelled
    pause
    exit /b 0
)

echo.
echo ========================================
echo Step 1: Syncing code to server
echo ========================================
echo.

echo Preparing files...
powershell -ExecutionPolicy Bypass -Command ^
"$ErrorActionPreference = 'Stop'; " ^
"$source = 'd:\work6.05'; " ^
"$excludeDirs = @('Chrome', '.git', '.venv', 'venv', 'generated_images', 'logs', 'temp_fanqie_upload', 'chapter_failures', '__pycache__', '.vscode', '.idea', '.claude', 'node_modules'); " ^
"Write-Host 'Scanning files...' -ForegroundColor Yellow; " ^
"$files = Get-ChildItem -Path $source -Recurse -Force | Where-Object { " ^
    " $relativePath = $_.FullName.Replace($source, ''); " ^
    " $firstDir = if ($relativePath -match '^\\+?([^\\]+)') { $matches[1] } else { '' }; " ^
    " $excludeDirs -notcontains $firstDir " ^
"}; " ^
"Write-Host ('Found ' + $files.Count + ' files to sync') -ForegroundColor Green; " ^
"$tempDir = Join-Path $env:TEMP 'novel_deploy_' + (Get-Date -Format 'yyyyMMddHHmmss'); " ^
"New-Item -ItemType Directory -Path $tempDir -Force | Out-Null; " ^
"$copied = 0; " ^
"foreach ($file in $files) { " ^
    " $destPath = Join-Path $tempDir $file.FullName.Replace($source, '').TrimStart('\\'); " ^
    " $destDir = Split-Path $destPath -Parent; " ^
    " if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }; " ^
    " Copy-Item $file.FullName -Destination $destPath -Force; " ^
    " $copied++; " ^
    " if ($copied %% 100 -eq 0) { Write-Host ('Copied ' + $copied + ' / ' + $files.Count + ' files') -ForegroundColor Gray } " ^
"}; " ^
"Write-Host ('Files ready: ' + $copied + ' files') -ForegroundColor Green; " ^
"$size = (Get-ChildItem -Path $tempDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB; " ^
"Write-Host ('Temp size: ' + [math]::Round($size, 2) + ' MB') -ForegroundColor Yellow; " ^
"Write-Host 'Uploading to server...' -ForegroundColor Yellow; " ^
"$scpArgs = @('-i', '%KEY_FILE%', '-o', 'StrictHostKeyChecking=no', '-r', (Join-Path $tempDir '*'), '%SERVER_USER%@%SERVER_IP%:%PROJECT_DIR%/'); " ^
"$process = Start-Process -FilePath 'scp' -ArgumentList $scpArgs -Wait -PassThru -NoNewWindow; " ^
"if ($process.ExitCode -ne 0) { throw 'SCP upload failed, exit code: ' + $process.ExitCode }; " ^
"Write-Host 'Upload success!' -ForegroundColor Green; " ^
"Remove-Item -Path $tempDir -Recurse -Force; " ^
"Write-Host 'Temp files cleaned' -ForegroundColor Gray"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Code sync failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Step 2: Configure and start on server
echo ========================================
echo.

echo Uploading startup script...
scp -i %KEY_FILE% -o StrictHostKeyChecking=no scripts/deploy/server_sync_and_start.sh %SERVER_USER%@%SERVER_IP%:/tmp/

if %errorlevel% neq 0 (
    echo [ERROR] Startup script upload failed
    pause
    exit /b 1
)

echo Executing configuration and startup script on server...
echo.

ssh -i %KEY_FILE% -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash /tmp/server_sync_and_start.sh"

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Server configuration may have issues, please check
    echo.
    echo Manual connection:
    echo ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
    echo.
    pause
    exit /b 1
)

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