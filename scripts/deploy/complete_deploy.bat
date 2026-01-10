@echo off
chcp 65001 >nul
echo ========================================
echo    完整自动部署工具
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
    echo ❌ 未找到Git Bash
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
    pause
    exit /b 1
)

echo ✓ 压缩包创建成功: %ZIP_FILE%
for %%F in (%ZIP_FILE%) do echo 大小: %%~zF 字节
echo.

REM 上传压缩包
echo 正在上传到服务器...
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

REM 在服务器上执行部署脚本
echo.
echo ========================================
echo    开始服务器端部署
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -s" << 'ENDSSH'
#!/bin/bash
set -e

echo "步骤 1/5: 检查上传的压缩包..."
TAR_FILE=$(ls -t /tmp/novel_system_*.tar.gz 2>/dev/null | head -1)
if [ -z "$TAR_FILE" ]; then
    echo "❌ 未找到上传的压缩包"
    exit 1
fi
echo "✓ 找到压缩包: $TAR_FILE"
ls -lh "$TAR_FILE"

echo ""
echo "步骤 2/5: 创建项目目录..."
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
echo "✓ 目录创建完成"

echo ""
echo "步骤 3/5: 解压代码..."
cd /home/novelapp/novel-system
tar -xzf "$TAR_FILE"
echo "✓ 代码解压完成"
ls -la | head -20

echo ""
echo "步骤 4/5: 清理并创建虚拟环境..."
rm -f "$TAR_FILE"

# 检查Python
if ! command -v python3.10 &> /dev/null; then
    echo "Python 3.10 未安装，正在安装..."
    apt update > /dev/null 2>&1
    apt install -y software-properties-common > /dev/null 2>&1
    add-apt-repository ppa:deadsnakes/ppa -y > /dev/null 2>&1
    apt update > /dev/null 2>&1
    apt install -y python3.10 python3.10-venv python3.10-dev python3-pip > /dev/null 2>&1
fi

python3.10 -m venv venv
echo "✓ 虚拟环境创建完成"

source venv/bin/activate
pip install --upgrade pip -q
pip install flask gunicorn eventlet -q

if [ -f requirements.txt ]; then
    echo "正在安装项目依赖..."
    pip install -r requirements.txt -q || echo "⚠️  部分依赖安装失败"
fi
echo "✓ 依赖安装完成"

echo ""
echo "步骤 5/5: 创建配置文件..."
cat > .env << 'EOF'
# Web服务配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False
LOG_LEVEL=INFO
EOF
echo "✓ 配置文件创建完成"

echo ""
echo "测试应用导入..."
if python -c "from web.web_server_refactored import app; print('✓ 应用导入成功')" 2>&1; then
    echo ""
    echo "========================================"
    echo "✓ 部署完成！"
    echo "========================================"
    echo ""
    IP=$(hostname -I | awk '{print $1}')
    echo "手动启动服务:"
    echo "  cd /home/novelapp/novel-system"
    echo "  source venv/bin/activate"
    echo "  gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app"
    echo ""
    echo "访问网站: http://$IP:5000"
    echo ""
else
    echo "❌ 应用导入失败，请检查日志"
    exit 1
fi
ENDSSH

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 所有步骤完成！
    echo ========================================
    echo.
    echo 现在可以连接到服务器启动服务：
    echo.
    echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
    echo.
    echo 然后执行：
    echo   cd /home/novelapp/novel-system
    echo   source venv/bin/activate
    echo   gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
    echo.
) else (
    echo.
    echo ❌ 部署过程中出现错误
    echo.
    echo 请检查：
    echo 1. 服务器连接是否正常
    echo 2. 磁盘空间是否充足
    echo 3. Python是否正确安装
    echo.
    echo 连接到服务器查看详细错误：
    echo ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP%
)

pause