@echo off
chcp 65001 >nul
echo ========================================
echo    连接阿里云服务器并部署应用
echo ========================================
echo.

REM 检查是否安装了SSH
where ssh >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到SSH命令
    echo 请安装OpenSSH客户端或Git for Windows
    echo.
    echo 下载地址:
    echo - Git for Windows: https://git-scm.com/download/win
    echo - OpenSSH: Windows 10/11 自带，在"启用Windows功能"中启用
    pause
    exit /b 1
)

REM 获取服务器信息
echo 请输入服务器信息:
echo.
set /p SERVER_IP="请输入服务器公网IP: "
set /p SERVER_USER="请输入用户名 (默认: admin): "
if "%SERVER_USER%"=="" set SERVER_USER=admin
set /p KEY_PATH="请输入私钥文件路径 (例如: C:\path\to\key.pem): "

if not exist "%KEY_PATH%" (
    echo 错误: 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

echo.
echo 服务器配置:
echo   公网IP: %SERVER_IP%
echo   用户名: %SERVER_USER%
echo   私钥: %KEY_PATH%
echo.

REM 测试连接
echo 测试SSH连接...
ssh -i "%KEY_PATH%" -p 22 -o ConnectTimeout=10 %SERVER_USER%@%SERVER_IP% "echo '连接成功！'"
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 连接失败！请检查:
    echo   1. 公网IP是否正确
    echo   2. 私钥文件是否正确
    echo   3. 阿里云安全组是否开放22端口
    echo   4. 用户名是否正确
    pause
    exit /b 1
)

echo.
echo ✓ 连接成功！
echo.

REM 选择操作
echo 请选择操作:
echo 1. 准备并上传代码
echo 2. 仅连接到服务器
echo 3. 查看服务器状态
echo 4. 退出
echo.
set /p ACTION="请输入选项 (1-4): "

if "%ACTION%"=="1" goto upload_and_deploy
if "%ACTION%"=="2" goto connect_only
if "%ACTION%"=="3" goto check_status
if "%ACTION%"=="4" goto end
echo 无效选项
pause
exit /b 1

:upload_and_deploy
echo.
echo ========================================
echo    准备并上传代码
echo ========================================
echo.

REM 检查Git Bash
set GIT_BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %GIT_BASH% (
    echo 错误: 未找到Git Bash
    echo 请安装Git for Windows: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM 创建压缩包
echo 正在创建代码压缩包...
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set ZIP_FILE=novel_system_%TIMESTAMP%.tar.gz

%GIT_BASH% -c "tar -czf %ZIP_FILE% --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' --exclude='.env' --exclude='test_*.py' --exclude='*.db' ."

if not exist %ZIP_FILE% (
    echo ❌ 压缩包创建失败
    pause
    exit /b 1
)

echo ✓ 压缩包创建完成: %ZIP_FILE%
echo.

REM 上传压缩包
echo 正在上传压缩包到服务器...
scp -i "%KEY_PATH%" -P 22 %ZIP_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/

if %ERRORLEVEL% neq 0 (
    echo ❌ 上传失败
    del %ZIP_FILE%
    pause
    exit /b 1
)

echo ✓ 上传成功！
echo.

REM 删除本地压缩包
del %ZIP_FILE%

echo.
echo ========================================
echo    代码已上传到服务器
echo ========================================
echo.
echo 接下来请在服务器上执行以下命令:
echo.
echo 1. 连接服务器:
echo    ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
echo.
echo 2. 在服务器上执行:
echo    sudo su -
echo    cd /tmp
echo    tar -xzf novel_system_*.tar.gz -C /home/novelapp/novel-system
echo    rm novel_system_*.tar.gz
echo    cd /home/novelapp/novel-system
echo    python3.10 -m venv venv
echo    source venv/bin/activate
echo    pip install -r requirements.txt
echo    pip install gunicorn eventlet
echo    cp .env.example .env
echo    vim .env
echo    # 编辑.env文件，配置API密钥
echo.
echo 3. 配置并启动服务:
echo    # 请参考 scripts/deploy/LOCAL_TO_ALIYUN_DEPLOYMENT_GUIDE.md
echo.
pause
exit /b 0

:connect_only
echo.
echo 正在连接到服务器...
echo.
ssh -i "%KEY_PATH%" -p 22 %SERVER_USER%@%SERVER_IP%
exit /b 0

:check_status
echo.
echo 正在检查服务器状态...
echo.
ssh -i "%KEY_PATH%" -p 22 %SERVER_USER%@%SERVER_IP% "echo '=== 系统信息 ===' && uname -a && echo '' && echo '=== 磁盘空间 ===' && df -h && echo '' && echo '=== 内存使用 ===' && free -h && echo '' && echo '=== 运行进程 ===' && ps aux | grep -E 'gunicorn|nginx' | grep -v grep || echo '未找到运行的应用进程'"
echo.
pause
exit /b 0

:end
echo 退出
exit /b 0