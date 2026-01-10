@echo off
REM 一键部署脚本 - 排除Chrome后全部同步

setlocal enabledelayedexpansion

set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set KEY_FILE=d:/work6.05/xsdm.pem

echo ========================================
echo   一键部署脚本 - 排除Chrome后同步
echo ========================================
echo.
echo 将要同步的目录:
echo   + src/        - 核心代码
echo   + web/        - Web界面
echo   + config/     - 配置文件
echo   + scripts/    - 脚本工具
echo   + requirements.txt
echo.
echo 排除的内容:
echo   - Chrome/     - 浏览器自动化 (1.6GB)
echo   - .git/       - Git历史 (605MB)
echo   - .venv/      - 虚拟环境
echo   - generated_images/ - 生成的图片
echo   - logs/       - 日志文件
echo   - 小说项目/    - 本地项目数据
echo.

set /p confirm="确认开始同步? (y/n): "
if /i not "%confirm%"=="y" (
    echo 取消部署
    pause
    exit /b 0
)

echo.
echo 开始同步...
echo.

REM 使用PowerShell和SCP同步文件
powershell -ExecutionPolicy Bypass -Command ^
"$ErrorActionPreference = 'Stop'; " ^
"$server = '%SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/'; " ^
"$key = '%KEY_FILE%'; " ^
"$source = 'd:\work6.05'; " ^
"$excludeDirs = @('Chrome', '.git', '.venv', 'venv', 'generated_images', 'logs', 'temp_fanqie_upload', 'chapter_failures', '__pycache__', '.vscode', '.idea', '.claude', 'node_modules'); " ^
"$excludeFiles = @('*.pyc', '*.pyo', '*.db', '*.log', '.env', 'Chrome.rar', 'test_*.py', 'check_*.py', 'diagnose_*.py', 'debug_*.py', '*.pem', '*.key', 'id_rsa*'); " ^
"Write-Host '准备文件列表...' -ForegroundColor Yellow; " ^
"$files = Get-ChildItem -Path $source -Recurse -Force | Where-Object { " ^
    " $relativePath = $_.FullName.Replace($source, ''); " ^
    " $firstDir = if ($relativePath -match '^\\+?([^\\]+)') { $matches[1] } else { '' }; " ^
    " $excludeDirs -notcontains $firstDir -and " ^
    " $excludeFiles | Where-Object { $_.Name -like $_ } | Measure-Object | Where-Object { $_.Count -eq 0 } " ^
"}; " ^
"Write-Host ('找到 ' + $files.Count + ' 个文件需要同步') -ForegroundColor Green; " ^
"$tempDir = Join-Path $env:TEMP 'novel_deploy_' + (Get-Date -Format 'yyyyMMddHHmmss'); " ^
"New-Item -ItemType Directory -Path $tempDir -Force | Out-Null; " ^
"Write-Host '创建临时目录: ' $tempDir -ForegroundColor Yellow; " ^
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
"$scpArgs = @('-i', $key, '-o', 'StrictHostKeyChecking=no', '-r', (Join-Path $tempDir '*'), $server); " ^
"$process = Start-Process -FilePath 'scp' -ArgumentList $scpArgs -Wait -PassThru -NoNewWindow; " ^
"if ($process.ExitCode -ne 0) { throw 'SCP上传失败，退出码: ' + $process.ExitCode }; " ^
"Write-Host '上传成功！' -ForegroundColor Green; " ^
"Remove-Item -Path $tempDir -Recurse -Force; " ^
"Write-Host '清理临时文件完成' -ForegroundColor Gray"

if %errorlevel% neq 0 (
    echo.
    echo [错误] 同步失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo [成功] 部署完成！
echo ========================================
echo.
echo 下一步操作:
echo 1. SSH连接到服务器:
echo    ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
echo.
echo 2. 进入项目目录并安装依赖:
echo    cd /home/novelapp/novel-system
echo    python3 -m venv venv
echo    source venv/bin/activate
echo    pip install -r requirements.txt
echo.
echo 3. 配置环境变量:
echo    cp .env.example .env
echo    vim .env
echo.
echo 4. 重启服务:
echo    sudo supervisorctl restart novel-system
echo.

pause