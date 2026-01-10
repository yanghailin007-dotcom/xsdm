@echo off
REM 完整部署脚本 - 同步代码 + 自动配置启动

setlocal enabledelayedexpansion

set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set KEY_FILE=d:/work6.05/xsdm.pem
set PROJECT_DIR=/home/novelapp/novel-system

echo ========================================
echo   完整部署脚本 - 同步 + 自动配置启动
echo ========================================
echo.
echo 此脚本将:
echo 1. 同步代码到服务器 (排除大文件)
echo 2. 自动配置服务器环境
echo 3. 清理旧进程
echo 4. 安装依赖
echo 5. 启动服务
echo.

set /p confirm="确认开始部署? (y/n): "
if /i not "%confirm%"=="y" (
    echo 取消部署
    pause
    exit /b 0
)

echo.
echo ========================================
echo 第1步: 同步代码到服务器
echo ========================================
echo.

REM 使用PowerShell准备文件并同步
powershell -ExecutionPolicy Bypass -Command ^
"$ErrorActionPreference = 'Stop'; " ^
"$source = 'd:\work6.05'; " ^
"$excludeDirs = @('Chrome', '.git', '.venv', 'venv', 'generated_images', 'logs', 'temp_fanqie_upload', 'chapter_failures', '__pycache__', '.vscode', '.idea', '.claude', 'node_modules'); " ^
"$excludeFiles = @('*.pyc', '*.pyo', '*.db', '*.log', '.env', 'Chrome.rar', 'test_*.py', 'check_*.py', 'diagnose_*.py', 'debug_*.py', '*.pem', '*.key', 'id_rsa*'); " ^
"Write-Host '正在准备文件...' -ForegroundColor Yellow; " ^
"$files = Get-ChildItem -Path $source -Recurse -Force | Where-Object { " ^
    " $relativePath = $_.FullName.Replace($source, ''); " ^
    " $firstDir = if ($relativePath -match '^\\+?([^\\]+)') { $matches[1] } else { '' }; " ^
    " $excludeDirs -notcontains $firstDir " ^
"}; " ^
"Write-Host ('找到 ' + $files.Count + ' 个文件需要同步') -ForegroundColor Green; " ^
"$tempDir = Join-Path $env:TEMP 'novel_deploy_' + (Get-Date -Format 'yyyyMMddHHmmss'); " ^
"New-Item -ItemType Directory -Path $tempDir -Force | Out-Null; " ^
"$copied = 0; " ^
"foreach ($file in $files) { " ^
    " $destPath = Join-Path $tempDir $file.FullName.Replace($source, '').TrimStart('\\'); " ^
    " $destDir = Split-Path $destPath -Parent; " ^
    " if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }; " ^
    " Copy-Item $file.FullName -Destination $destPath -Force; " ^
    " $copied++; " ^
    " if ($copied % 100 -eq 0) { Write-Host ('已复制 ' + $copied + ' / ' + $files.Count + ' 个文件') -ForegroundColor Gray } " ^
"}; " ^
"Write-Host ('文件复制完成，共 ' + $copied + ' 个文件') -ForegroundColor Green; " ^
"$size = (Get-ChildItem -Path $tempDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB; " ^
"Write-Host ('临时目录大小: ' + [math]::Round($size, 2) + ' MB') -ForegroundColor Yellow; " ^
"Write-Host '开始上传到服务器...' -ForegroundColor Yellow; " ^
"$scpArgs = @('-i', '%KEY_FILE%', '-o', 'StrictHostKeyChecking=no', '-r', (Join-Path $tempDir '*'), '%SERVER_USER%@%SERVER_IP%:%PROJECT_DIR%/'); " ^
"$process = Start-Process -FilePath 'scp' -ArgumentList $scpArgs -Wait -PassThru -NoNewWindow; " ^
"if ($process.ExitCode -ne 0) { throw 'SCP上传失败，退出码: ' + $process.ExitCode }; " ^
"Write-Host '上传成功！' -ForegroundColor Green; " ^
"Remove-Item -Path $tempDir -Recurse -Force; " ^
"Write-Host '清理临时文件完成' -ForegroundColor Gray"

if %errorlevel% neq 0 (
    echo.
    echo [错误] 代码同步失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 第2步: 在服务器上配置并启动
echo ========================================
echo.

REM 上传启动脚本到服务器
scp -i %KEY_FILE% -o StrictHostKeyChecking=no scripts/deploy/server_sync_and_start.sh %SERVER_USER%@%SERVER_IP%:/tmp/

if %errorlevel% neq 0 (
    echo [错误] 启动脚本上传失败
    pause
    exit /b 1
)

REM 在服务器上执行启动脚本
echo 正在服务器上执行配置和启动脚本...
echo.

ssh -i %KEY_FILE% -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash /tmp/server_sync_and_start.sh"

if %errorlevel% neq 0 (
    echo.
    echo [警告] 服务器配置可能有问题，请检查
    echo.
    echo 手动连接服务器检查:
    echo ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 服务已启动，访问地址:
echo   本地: http://localhost:5000
echo   公网: http://%SERVER_IP%:5000
echo.
echo 常用命令:
echo   查看状态: ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl status novel-system"
echo   查看日志: ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl tail -f novel-system"
echo   重启服务: ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP% "sudo supervisorctl restart novel-system"
echo.

pause