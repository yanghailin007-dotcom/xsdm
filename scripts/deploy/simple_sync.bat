@echo off
REM 简单同步脚本 - 使用SCP和PowerShell，无需rsync

setlocal enabledelayedexpansion

set SERVER_IP=8.163.37.124
set SERVER_USER=novelapp
set KEY_FILE=d:/work6.05/xsdm.pem
set TEMP_DIR=%TEMP%\novel_deploy_temp

echo ========================================
echo   简单部署脚本 - 排除大文件后同步
echo ========================================
echo.

REM 创建临时目录
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

echo [1/4] 正在准备文件...
echo.

REM 使用PowerShell复制文件（排除不需要的）
powershell -Command ^
"$source = 'd:\work6.05';" ^
"$dest = '%TEMP_DIR%';" ^
"$exclude = @('Chrome', '.git', '.venv', 'venv', 'generated_images', 'logs', 'temp_fanqie_upload', 'chapter_failures', '小说项目', '视频项目', '__pycache__', '.vscode', '.idea', '.claude', 'node_modules', 'ai_enhanced_settings', 'fusion_settings', 'optimized_prompts', 'knowledge_base', 'static', 'data', 'tests', 'tools');" ^
"Get-ChildItem -Path $source -Recurse -Force | Where-Object { " ^
    " $path = $_.FullName.Replace($source, ''); " ^
    " $dir = ($path -split '\\')[1]; " ^
    " $exclude -notcontains $dir -and " ^
    " $_.Name -notmatch '\.(pyc|pyo|db|log)$' -and " ^
    " $_.Name -notmatch 'test_|check_|diagnose_|debug_' -and " ^
    " $_.Name -ne '.env' -and " ^
    " $_.Name -ne 'Chrome.rar' " ^
"} | ForEach-Object { " ^
    " $targetPath = Join-Path $dest $_.FullName.Replace($source, ''); " ^
    " $targetDir = Split-Path $targetPath -Parent; " ^
    " if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }; " ^
    " Copy-Item $_.FullName -Destination $targetPath -Force " ^
"}"

if %errorlevel% neq 0 (
    echo [错误] 文件准备失败
    pause
    exit /b 1
)

echo [2/4] 计算文件大小...
for /f %%a in ('powershell -Command "Get-ChildItem -Path %TEMP_DIR% -Recurse | Measure-Object -Property Length -Sum | Select-Object -ExpandProperty Sum"') do set SIZE=%%a
set /a SIZE_MB=%SIZE% / 1048576
echo 准备同步的文件大小: %SIZE_MB% MB
echo.

echo [3/4] 正在上传到服务器...
echo.

REM 上传到服务器
scp -i %KEY_FILE% -o StrictHostKeyChecking=no -r %TEMP_DIR%/* %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/

if %errorlevel% neq 0 (
    echo [错误] 上传失败
    rmdir /s /q "%TEMP_DIR%"
    pause
    exit /b 1
)

echo [4/4] 清理临时文件...
rmdir /s /q "%TEMP_DIR%"

echo.
echo ========================================
echo [成功] 部署完成！
echo ========================================
echo.
echo 下一步操作:
echo 1. SSH连接到服务器:
echo    ssh -i %KEY_FILE% %SERVER_USER%@%SERVER_IP%
echo.
echo 2. 进入项目目录:
echo    cd /home/novelapp/novel-system
echo.
echo 3. 创建虚拟环境并安装依赖:
echo    python3 -m venv venv
echo    source venv/bin/activate
echo    pip install -r requirements.txt
echo.
echo 4. 配置环境变量:
echo    cp .env.example .env
echo    vim .env
echo.
echo 5. 重启服务:
echo    sudo supervisorctl restart novel-system
echo.

pause