@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    智能部署 - 增量同步
echo ========================================
echo.

REM ============================================================
REM 配置区域 - 请根据实际情况修改
REM ============================================================
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem
set LOCAL_ROOT=d:\work6.05
set REMOTE_ROOT=/home/novelapp/novel-system
REM ============================================================

echo 服务器: %SERVER_IP%
echo 本地路径: %LOCAL_ROOT%
echo 远程路径: %REMOTE_ROOT%
echo.

REM 检查私钥
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 修复私钥权限
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

REM ============================================================
REM 查找rsync
REM ============================================================
echo [1/4] 查找rsync工具...

set "RSYNC="
set "GIT_BASH_RSYNC="

REM 检查常见Git Bash安装路径
if exist "C:\Program Files\Git\usr\bin\rsync.exe" (
    set "GIT_BASH_RSYNC=C:\Program Files\Git\usr\bin\rsync.exe"
) else if exist "C:\Program Files\Git\mingw64\bin\rsync.exe" (
    set "GIT_BASH_RSYNC=C:\Program Files\Git\mingw64\bin\rsync.exe"
) else if exist "C:\Program Files\Git\bin\rsync.exe" (
    set "GIT_BASH_RSYNC=C:\Program Files\Git\bin\rsync.exe"
)

REM 检查系统PATH中的rsync
where rsync >nul 2>&1
if !ERRORLEVEL! equ 0 (
    set "RSYNC=rsync"
    echo ✓ 找到系统rsync
) else if defined GIT_BASH_RSYNC (
    set "RSYNC=!GIT_BASH_RSYNC!"
    echo ✓ 找到Git Bash的rsync
) else (
    echo ❌ 未找到rsync
    echo.
    echo 请安装Git for Windows获得rsync支持:
    echo 下载地址: https://git-scm.com/download/win
    echo.
    echo 或者使用deploy_scp.bat（仅使用scp）
    pause
    exit /b 1
)

echo 使用rsync: !RSYNC!
echo.

REM ============================================================
REM 创建排除规则文件
REM ============================================================
echo [2/4] 准备同步规则...

set EXCLUDE_FILE=%TEMP%\deploy_exclude_%RANDOM%.txt
(
    echo PATTERN: __pycache__
    echo PATTERN: *.pyc
    echo PATTERN: .git
    echo PATTERN: logs/*
    echo PATTERN: generated_images/*
    echo PATTERN: temp_fanqie_upload/*
    echo PATTERN: .env
    echo PATTERN: test_*.py
    echo PATTERN: *.db
    echo PATTERN: 小说项目/*
    echo PATTERN: Chrome/*
    echo PATTERN: knowledge_base/*
    echo PATTERN: ai_enhanced_settings/*
    echo PATTERN: fusion_settings/*
    echo PATTERN: .vscode
    echo PATTERN: node_modules
    echo PATTERN: venv
    echo PATTERN: *.bat
    echo PATTERN: *.sh
    echo PATTERN: deploy_config.ini
    echo PATTERN: STABLE_DEPLOYMENT_GUIDE.md
    echo PATTERN: *.md
) > "%EXCLUDE_FILE%"

echo ✓ 排除规则已创建
echo.

REM ============================================================
REM 执行rsync增量同步
REM ============================================================
echo [3/4] 同步文件到服务器...
echo.
echo ℹ️  使用rsync增量同步 - 只传输修改过的文件
echo ℹ️  这可能需要几分钟，请耐心等待...
echo.

REM rsync参数说明:
REM -a: 归档模式，保持文件属性
REM -v: 详细输出
REM -z: 压缩传输
REM --delete: 删除目标中源没有的文件
REM --exclude-from: 排除文件列表
REM -e: 指定SSH命令
REM --progress: 显示进度
REM --stats: 显示统计信息

"%RSYNC%" -avz --delete --progress --stats ^
    --exclude-from="%EXCLUDE_FILE%" ^
    --filter="protect .git/" ^
    --filter="protect venv/" ^
    --filter="protect logs/" ^
    -e "ssh -i '%KEY_PATH%' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" ^
    "%LOCAL_ROOT%/." ^
    %SERVER_USER%@%SERVER_IP%:%REMOTE_ROOT%/.

set RSYNC_ERROR=!ERRORLEVEL!

del "%EXCLUDE_FILE%" 2>nul

echo.
if !RSYNC_ERROR! equ 0 (
    echo ✓ rsync同步成功
) else (
    echo ❌ rsync同步失败 (错误代码: !RSYNC_ERROR!)
    pause
    exit /b 1
)

echo.

REM ============================================================
REM 上传并执行服务器部署脚本
REM ============================================================
echo [4/4] 执行服务器部署...
echo.

cd /d "%LOCAL_ROOT%"

REM 上传服务器部署脚本
echo 正在上传服务器部署脚本...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no ^
    scripts/deploy/server_deploy_stable.sh ^
    %SERVER_USER%@%SERVER_IP%:%REMOTE_ROOT%/scripts/deploy/

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
    "cd %REMOTE_ROOT% && chmod +x scripts/deploy/server_deploy_stable.sh && bash scripts/deploy/server_deploy_stable.sh"

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
echo 📊 同步统计:
echo   - 使用rsync增量同步
echo   - 只传输修改过的文件
echo   - 传输更快，节省带宽
echo.
echo 🌐 访问地址: http://%SERVER_IP%:5000
echo.
echo 💡 提示:
echo   - 首次部署会传输所有文件
echo   - 后续部署只传输修改的文件
echo   - 使用deploy_quick.bat可以只重启不同步
echo.
pause