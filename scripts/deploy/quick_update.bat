@echo off
REM 快速更新脚本 - 只同步代码并重启服务（不重新配置）

setlocal enabledelayedexpansion

set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set KEY_FILE=d:/work6.05/xsdm.pem
set PROJECT_DIR=/home/novelapp/novel-system

echo ========================================
echo   快速更新脚本 - 同步代码并重启
echo ========================================
echo.
echo 此脚本将:
echo 1. 同步最新代码到服务器
echo 2. 重启服务（不清理环境）
echo.
echo 适用场景: 代码更新，环境配置不变
echo.

set /p confirm="确认开始更新? (y/n): "
if /i not "%confirm%"=="y" (
    echo 取消更新
    pause
    exit /b 0
)

echo.
echo ========================================
echo 第1步: 同步代码
echo ========================================
echo.

REM 快速同步代码
powershell -ExecutionPolicy Bypass -Command ^
"$ErrorActionPreference = 'Stop'; " ^
"$source = 'd:\work6.05'; " ^
"$excludeDirs = @('Chrome', '.git', '.venv', 'venv', 'generated_images', 'logs', 'temp_fanqie_upload', 'chapter_failures', '__pycache__', '.vscode', '.idea', '.claude', 'node_modules'); " ^
"Write-Host '正在准备文件...' -ForegroundColor Yellow; " ^
"$files = Get-ChildItem -Path $source -Recurse -Force | Where-Object { " ^
    " $relativePath = $_.FullName.Replace($source, ''); " ^
    " $firstDir = if ($relativePath -match '^\\+?([^\\]+)') { $matches[1] } else { '' }; " ^
    " $excludeDirs -notcontains $firstDir " ^
"}; " ^
"Write-Host ('找到 ' + $files.Count + ' 个文件需要同步') -ForegroundColor Green; " ^
"$tempDir = Join-Path $env:TEMP 'novel_update_' + (Get-Date -Format 'yyyyMMddHHmmss'); " ^
"New-Item -ItemType Directory -Path $tempDir -Force | Out-Null; " ^
"$copied = 0; " ^
"foreach ($file in $files) { " ^
    " $destPath = Join-Path $tempDir $file.FullName.Replace($source, '').TrimStart('\\'); " ^
    " $destDir = Split-Path $destPath -Parent; " ^
    " if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }; " ^
    " Copy-Item $file.FullName -Destination $destPath -Force; " ^
    " $copied++; " ^
    " if ($copied %% 100 -eq 0) { Write-Host ('已复制 ' + $copied + ' / ' + $files.Count + ' 个文件') -ForegroundColor Gray } " ^
"}; " ^
"Write-Host ('文件准备完成，共 ' + $copied + ' 个文件') -ForegroundColor Green; " ^
"$size = (Get-ChildItem -Path $tempDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB; " ^
"Write-Host ('大小: ' + [math]::Round($size, 2) + ' MB') -ForegroundColor Yellow; " ^
"Write-Host '开始上传...' -ForegroundColor Yellow; " ^
"$scpArgs = @('-i', '%KEY_FILE%', '-o', 'StrictHostKeyChecking=no', '-r', (Join-Path $tempDir '*'), '%SERVER_USER%@%SERVER_IP%:%PROJECT_DIR%/'); " ^
"$process = Start-Process -FilePath 'scp' -ArgumentList $scpArgs -Wait -PassThru -NoNewWindow; " ^
"if ($process.ExitCode -ne 0) { throw 'SCP上传失败，退出码: ' + $process.ExitCode }; " ^
"Write-Host '上传成功！' -ForegroundColor Green; " ^
"Remove-Item -Path $tempDir -Recurse -Force"

if %errorlevel% neq 0 (
    echo.
    echo [错误] 代码同步失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 第2步: 重启服务
echo ========================================
echo.

echo 正在重启服务...
ssh -i %KEY_FILE% -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "sudo supervisorctl restart novel-system"

if %errorlevel% neq 0 (
    echo.
    echo [错误] 服务重启失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 更新完成！
echo ========================================
echo.
echo 服务已重启，访问地址:
echo   http://%SERVER_IP%:5000
echo.
echo 如有新依赖需要安装，请手动执行:
echo   ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
echo   cd %PROJECT_DIR%
echo   source venv/bin/activate
echo   pip install -r requirements.txt
echo.

timeout /t 3 >nul