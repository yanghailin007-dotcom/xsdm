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

echo 服务器配置:
echo   公网IP: %SERVER_IP%
echo   用户名: %SERVER_USER%
echo   私钥: %KEY_PATH%
echo.

REM 检查私钥文件
if not exist "%KEY_PATH%" (
    echo 错误: 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 设置私钥权限
echo 设置私钥文件权限...
icacls "%KEY_PATH%" /inheritance:r
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F"
echo ✓ 权限设置完成
echo.

REM 测试连接
echo 测试SSH连接...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo '连接成功！'" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ 连接失败！请检查:
    echo   1. 公网IP是否正确: %SERVER_IP%
    echo   2. 私钥文件是否正确: %KEY_PATH%
    echo   3. 阿里云安全组是否开放22端口
    pause
    exit /b 1
)
echo ✓ 连接测试成功
echo.

echo ========================================
echo 请选择操作:
echo ========================================
echo.
echo 1. 准备并上传代码到服务器
echo 2. 连接到服务器并手动部署
echo 3. 查看服务器状态
echo 4. 一键完成所有部署（推荐）
echo 0. 退出
echo.
set /p ACTION="请输入选项 (0-4): "

if "%ACTION%"=="1" goto upload_code
if "%ACTION%"=="2" goto connect_server
if "%ACTION%"=="3" goto check_status
if "%ACTION%"=="4" goto auto_deploy
if "%ACTION%"=="0" goto end
echo 无效选项
pause
exit /b 1

:upload_code
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

cd /d d:\work6.05
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
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no %ZIP_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/

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
echo 代码已上传到服务器！
echo ========================================
echo.
echo 接下来请选择:
echo 1. 返回主菜单继续操作
echo 2. 退出
echo.
set /p NEXT="请输入选项 (1-2): "
if "%NEXT%"=="1" goto start
if "%NEXT%"=="2" goto end
goto end

:connect_server
echo.
echo 正在连接到服务器...
echo.
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP%
exit /b 0

:check_status
echo.
echo 正在检查服务器状态...
echo.
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo '=== 系统信息 ===' && uname -a && echo '' && echo '=== 磁盘空间 ===' && df -h && echo '' && echo '=== 内存使用 ===' && free -h && echo '' && echo '=== Python版本 ===' && python3 --version 2>&1 || echo 'Python未安装' && echo '' && echo '=== 运行的服务 ===' && ps aux | grep -E 'gunicorn|nginx|supervisor' | grep -v grep || echo '未找到运行的应用服务'"
echo.
pause
goto start

:auto_deploy
echo.
echo ========================================
echo    一键自动部署
echo ========================================
echo.
echo 这将自动完成以下操作:
echo 1. 上传代码到服务器
echo 2. 配置服务器环境
echo 3. 安装依赖
echo 4. 配置并启动服务
echo.
echo 注意: 您需要在服务器上手动配置 .env 文件中的API密钥
echo.
set /p CONFIRM="确认继续？(y/n): "
if /i not "%CONFIRM%"=="y" goto start

echo.
echo 步骤 1/5: 上传代码...
call :upload_code_silent
if %ERRORLEVEL% neq 0 (
    echo ❌ 代码上传失败
    pause
    exit /b 1
)
echo ✓ 代码上传完成
echo.

echo 步骤 2/5: 配置服务器环境...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -s" << 'DEPLOY_SCRIPT'
#!/bin/bash
set -e

echo "开始配置服务器环境..."

# 切换到root（如果需要）
if [ "$USER" != "root" ]; then
    echo "需要sudo权限..."
    SUDO="sudo"
else
    SUDO=""
fi

# 更新系统
echo "更新系统包..."
$SUDO apt update && $SUDO apt upgrade -y

# 安装基础工具
echo "安装基础工具..."
$SUDO apt install -y wget curl git vim build-essential software-properties-common lrzsz

# 安装Python 3.10
echo "安装Python 3.10..."
$SUDO add-apt-repository ppa:deadsnakes/ppa -y
$SUDO apt update
$SUDO apt install -y python3.10 python3.10-venv python3.10-dev python3-pip

# 创建应用用户
echo "创建应用用户..."
$SUDO useradd -m -s /bin/bash novelapp || true

# 创建项目目录
echo "创建项目目录..."
$SUDO mkdir -p /home/novelapp/novel-system
$SUDO mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
$SUDO chown -R novelapp:novelapp /home/novelapp/novel-system

# 解压代码
echo "解压代码..."
$SUDO tar -xzf /tmp/novel_system_*.tar.gz -C /home/novelapp/novel-system
$SUDO rm /tmp/novel_system_*.tar.gz

# 安装Nginx和Supervisor
echo "安装Nginx和Supervisor..."
$SUDO apt install -y nginx supervisor

echo "✓ 服务器环境配置完成"
DEPLOY_SCRIPT

if %ERRORLEVEL% neq 0 (
    echo ❌ 服务器环境配置失败
    pause
    exit /b 1
)

echo.
echo 步骤 3/5: 部署应用...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -s" << 'DEPLOY_APP_SCRIPT'
#!/bin/bash
set -e

echo "部署应用..."

# 切换到应用用户
$SUDO -u novelapp -i << 'EOF'
cd /home/novelapp/novel-system

# 创建虚拟环境
echo "创建Python虚拟环境..."
python3.10 -m venv venv
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装Python依赖..."
pip install -r requirements.txt
pip install gunicorn eventlet

# 配置环境变量模板
echo "配置环境变量..."
cp .env.example .env || echo "未找到.env.example，请手动创建.env文件"

echo "✓ 应用部署完成"
echo ""
echo "⚠️  重要: 请手动配置 /home/novelapp/novel-system/.env 文件"
echo "   需要配置以下内容:"
echo "   SECRET_KEY=\$(openssl rand -hex 32)"
echo "   DOUBAO_API_KEY=您的豆包API密钥"
echo "   NANOBANANA_API_KEY=您的NanoBanana API密钥"
echo "   FLASK_ENV=production"
echo "   DEBUG=False"
EOF
DEPLOY_APP_SCRIPT

if %ERRORLEVEL% neq 0 (
    echo ❌ 应用部署失败
    pause
    exit /b 1
)

echo.
echo 步骤 4/5: 配置并启动服务...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -s" << 'CONFIG_SERVICE_SCRIPT'
#!/bin/bash
set -e

echo "配置服务..."

# 获取CPU核心数
WORKERS=$(($(nproc) * 2 + 1))

# 配置Nginx
echo "配置Nginx..."
sudo tee /etc/nginx/sites-available/novel-system > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    access_log /var/log/nginx/novel-system-access.log;
    error_log /var/log/nginx/novel-system-error.log;

    client_max_body_size 100M;

    location /static {
        alias /home/novelapp/novel-system/web/static;
        expires 30d;
    }

    location /generated_images {
        alias /home/novelapp/novel-system/generated_images;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/novel-system /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# 配置Supervisor
echo "配置Supervisor..."
sudo tee /etc/supervisor/conf.d/novel-system.conf > /dev/null << EOF
[program:novel-system]
command=/home/novelapp/novel-system/venv/bin/gunicorn -w $WORKERS -b 127.0.0.1:5000 --timeout 600 --access-logfile /home/novelapp/novel-system/logs/gunicorn-access.log --error-logfile /home/novelapp/novel-system/logs/gunicorn-error.log --log-level info web.web_server_refactored:app
directory=/home/novelapp/novel-system
user=novelapp
autostart=true
autorestart=true
startretries=3
stderr_logfile=/home/novelapp/novel-system/logs/supervisor-stderr.log
stdout_logfile=/home/novelapp/novel-system/logs/supervisor-stdout.log
environment=FLASK_ENV="production"
EOF

sudo supervisorctl reread
sudo supervisorctl update

# 配置防火墙
echo "配置防火墙..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable || true

echo "✓ 服务配置完成"
CONFIG_SERVICE_SCRIPT

if %ERRORLEVEL% neq 0 (
    echo ❌ 服务配置失败
    pause
    exit /b 1
)

echo.
echo 步骤 5/5: 启动服务并检查状态...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -s" << 'START_SERVICE_SCRIPT'
#!/bin/bash

echo "启动应用服务..."
sudo supervisorctl start novel-system

sleep 3

echo ""
echo "========================================"
echo "检查服务状态:"
echo "========================================"
echo ""
echo "=== Supervisor状态 ==="
sudo supervisorctl status novel-system
echo ""
echo "=== Nginx状态 ==="
sudo systemctl status nginx --no-pager -l | grep "Active:"
echo ""
echo "=== 监听端口 ==="
sudo netstat -tulpn | grep -E '80|443|5000'
echo ""

echo "========================================"
echo "部署完成！"
echo "========================================"
echo ""
echo "接下来的步骤:"
echo "1. 连接到服务器配置 .env 文件:"
echo "   ssh -i %KEY_PATH% %SERVER_USER%@%SERVER_IP%"
echo "   sudo -u novelapp vim /home/novelapp/novel-system/.env"
echo ""
echo "2. 配置API密钥后重启服务:"
echo "   sudo supervisorctl restart novel-system"
echo ""
echo "3. 访问网站:"
echo "   http://%SERVER_IP%"
echo ""
echo "4. 查看日志:"
echo "   sudo supervisorctl tail -f novel-system"
echo ""
START_SERVICE_SCRIPT

pause
exit /b 0

:upload_code_silent
REM 创建压缩包
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set ZIP_FILE=novel_system_%TIMESTAMP%.tar.gz

cd /d d:\work6.05
%GIT_BASH% -c "tar -czf %ZIP_FILE% --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' --exclude='.env' --exclude='test_*.py' --exclude='*.db' ." >nul 2>&1

if not exist %ZIP_FILE% exit /b 1

scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no %ZIP_FILE% %SERVER_USER%@%SERVER_IP%:/tmp/ >nul 2>&1
if %ERRORLEVEL% neq 0 (
    del %ZIP_FILE%
    exit /b 1
)

del %ZIP_FILE%
exit /b 0

:start
cls
goto :eof

:end
echo 退出
exit /b 0