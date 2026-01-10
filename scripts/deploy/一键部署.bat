@echo off
chcp 65001 >nul
echo ========================================
echo    小说生成系统 - 一键部署工具
echo ========================================
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

echo 服务器信息:
echo   IP: %SERVER_IP%
echo   用户: %SERVER_USER%
echo   私钥: %KEY_PATH%
echo.

REM 检查私钥
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 设置权限
echo 正在设置私钥权限...
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

REM 测试连接
echo 测试SSH连接...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo '连接成功'" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ SSH连接失败
    pause
    exit /b 1
)
echo ✓ SSH连接成功
echo.

REM 检查Git Bash
set GIT_BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %GIT_BASH% (
    echo ❌ 未找到Git Bash，请先安装Git for Windows
    echo 下载地址: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo.
echo ========================================
echo    步骤 1/3: 创建压缩包
echo ========================================
echo.

set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set ZIP_FILE=novel_system_%TIMESTAMP%.tar.gz

cd /d d:\work6.05

echo 正在创建tar.gz压缩包...
echo 排除的目录: Chrome, .git, logs, generated_images等
echo.

%GIT_BASH% -c "tar -czf %ZIP_FILE% --exclude='Chrome/Chrome' --exclude='.git' --exclude='.venv' --exclude='venv' --exclude='generated_images' --exclude='logs' --exclude='temp_fanqie_upload' --exclude='chapter_failures' --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' --exclude='.env' --exclude='*.db' --exclude='test_*.py' --exclude='check_*.py' --exclude='diagnose_*.py' --exclude='debug_*.py' --exclude='*.log' --exclude='.vscode' --exclude='.idea' --exclude='.claude' --exclude='node_modules' --exclude='ai_enhanced_settings' --exclude='fusion_settings' --exclude='optimized_prompts' --exclude='knowledge_base' --exclude='static' --exclude='data' --exclude='tests' --exclude='tools' --exclude='*.pem' --exclude='*.key' --exclude='id_rsa*' --exclude='Chrome.rar' ."

if not exist %ZIP_FILE% (
    echo ❌ 压缩包创建失败
    pause
    exit /b 1
)

echo ✓ 压缩包创建成功
for %%F in (%ZIP_FILE%) do echo 大小: %%~zF 字节
echo.

echo.
echo ========================================
echo    步骤 2/3: 上传到服务器
echo ========================================
echo.

echo 正在上传压缩包到服务器...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no %ZIP_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/

if %ERRORLEVEL% neq 0 (
    echo ❌ 上传失败
    del %ZIP_FILE%
    pause
    exit /b 1
)

echo ✓ 上传成功
echo.

REM 删除本地压缩包
del %ZIP_FILE%

echo.
echo ========================================
echo    步骤 3/3: 服务器端配置和启动
echo ========================================
echo.

echo 上传服务器端部署脚本...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no scripts/deploy/server_deploy_and_start.sh %SERVER_USER%@%SERVER_IP%:/tmp/

if %ERRORLEVEL% neq 0 (
    echo ❌ 脚本上传失败
    pause
    exit /b 1
)

echo ✓ 脚本上传成功
echo.

echo 执行服务器端部署...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash /tmp/server_deploy_and_start.sh"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 所有步骤完成！
    echo ========================================
    echo.
    echo 部署成功！服务已在服务器上运行。
    echo.
) else (
    echo.
    echo ❌ 部署过程中出现错误
    echo.
    echo 请连接到服务器检查:
    echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
    echo.
)

pause