@echo off
chcp 65001 >nul
echo ========================================
echo    简化代码上传工具
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

REM 设置权限（静默）
echo 正在设置私钥权限...
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

REM 测试连接
echo 测试SSH连接...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo '连接成功'" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ SSH连接失败
    echo.
    echo 请检查：
    echo 1. 服务器IP是否正确: %SERVER_IP%
    echo 2. 私钥文件是否正确: %KEY_PATH%
    echo 3. 安全组是否开放22端口
    pause
    exit /b 1
)
echo ✓ SSH连接成功
echo.

REM 检查Git Bash
set GIT_BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %GIT_BASH% (
    echo ❌ 未找到Git Bash
    echo 请安装: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM 创建压缩包
echo 正在创建压缩包...
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set ZIP_FILE=novel_system_%TIMESTAMP%.tar.gz

cd /d d:\work6.05
%GIT_BASH% -c "tar -czf %ZIP_FILE% --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' --exclude='.env' --exclude='test_*.py' --exclude='*.db' ."

if not exist %ZIP_FILE% (
    echo ❌ 压缩包创建失败
    echo.
    echo 尝试查看详细错误：
    %GIT_BASH% -c "tar -czf test.tar.gz . 2>&1"
    pause
    exit /b 1
)

echo ✓ 压缩包创建成功: %ZIP_FILE%
echo 大小：
for %%F in (%ZIP_FILE%) do echo %%~zF 字节
echo.

REM 上传
echo 正在上传到服务器...
echo 目标: %SERVER_USER%@%SERVER_IP%:/tmp/
echo.

scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no %ZIP_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 上传失败
    del %ZIP_FILE%
    pause
    exit /b 1
)

echo.
echo ========================================
echo    ✓ 上传成功！
echo ========================================
echo.
echo 文件已上传到服务器: /tmp/%ZIP_FILE%
echo.
echo 接下来的步骤:
echo 1. 连接服务器:
echo    ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
echo.
echo 2. 解压代码:
echo    mkdir -p /home/novelapp/novel-system
echo    cd /home/novelapp/novel-system
echo    tar -xzf /tmp/%ZIP_FILE%
echo    rm /tmp/%ZIP_FILE%
echo.
echo 3. 详细步骤请参考:
echo    scripts/deploy/SIMPLE_DEPLOY_GUIDE.md
echo.

REM 删除本地压缩包
del %ZIP_FILE%
pause