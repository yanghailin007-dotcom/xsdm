@echo off
chcp 65001 >nul
echo ========================================
echo    小说生成系统 - 完整重新部署
echo ========================================
echo.
echo 此脚本将：
echo   1. 停止服务器上的服务
echo   2. 删除服务器上的旧代码
echo   3. 上传本地代码
echo   4. 重新安装依赖
echo   5. 启动服务
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem
set REMOTE_PATH=/home/novelapp/novel-system

echo 服务器: %SERVER_IP%
echo 远程路径: %REMOTE_PATH%
echo.

REM 检查私钥
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)
echo ✓ 私钥文件存在
echo.

REM 设置私钥权限
echo 设置私钥权限...
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1
echo ✓ 权限设置完成
echo.

REM 测试SSH连接
echo 测试SSH连接...
ssh -i "%KEY_PATH%" -o ConnectTimeout=10 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "echo '连接成功'" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ SSH连接失败
    pause
    exit /b 1
)
echo ✓ SSH连接成功
echo.

echo ========================================
echo    步骤 1/5: 停止并清理旧服务
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "
echo '停止服务...'
cd %REMOTE_PATH% 2>/dev/null || echo '项目目录不存在，跳过停止服务'
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi
echo '✓ 服务已停止'
echo ''
"

echo ========================================
echo    步骤 2/5: 删除旧代码
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "
echo '删除旧代码...'
rm -rf %REMOTE_PATH%
echo '✓ 旧代码已删除'
echo ''
"

echo ========================================
echo    步骤 3/5: 上传本地代码
echo ========================================
echo.

cd /d d:\work6.05

echo 创建部署包...
echo   - 使用Python脚本创建部署包，确保所有UI资源都被包含
echo   - 包含 src/ 目录（所有源代码）
echo   - 包含 web/ 目录（所有UI资源：templates、static、api等）
echo   - 包含 config/ 目录（配置文件）
echo   - 包含 requirements.txt（Python依赖）
echo   - 包含 web/wsgi.py（WSGI入口）
python scripts\deploy\create_deploy_package.py

if %ERRORLEVEL% neq 0 (
    echo ❌ 创建部署包失败
    pause
    exit /b 1
)

if %ERRORLEVEL% neq 0 (
    echo ❌ 创建部署包失败
    pause
    exit /b 1
)
echo ✓ 部署包创建完成
echo.

echo 验证部署包内容...
python scripts\deploy\verify_deploy_package.py
if %ERRORLEVEL% neq 0 (
    echo ❌ 部署包验证失败，缺少必要的UI资源文件
    pause
    exit /b 1
)
echo ✓ 部署包验证通过
echo.

echo 上传部署包到服务器...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no deploy_package.zip %SERVER_USER%@%SERVER_IP%:/tmp/
if %ERRORLEVEL% neq 0 (
    echo ❌ 上传失败
    pause
    exit /b 1
)
echo ✓ 部署包上传完成
echo.

REM 清理本地部署包
del deploy_package.zip

echo ========================================
echo    步骤 4/5: 服务器端部署
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "
echo '创建项目目录...'
mkdir -p %REMOTE_PATH%
mkdir -p %REMOTE_PATH%/{logs,data,generated_images,temp_fanqie_upload}
echo '✓ 目录创建完成'
echo ''

echo '解压代码...'
cd %REMOTE_PATH%
unzip -q /tmp/deploy_package.zip
rm -f /tmp/deploy_package.zip
echo '✓ 代码解压完成'
echo ''

echo '创建Python虚拟环境...'
python3.10 -m venv venv
echo '✓ 虚拟环境创建完成'
echo ''

echo '安装Python依赖...'
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn eventlet flask -q
echo '✓ 依赖安装完成'
echo ''

echo '创建环境配置文件...'
cat > .env << 'EOF'
# Web服务配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False

# 日志配置
LOG_LEVEL=INFO

# API配置（可选 - 如果需要AI功能再配置）
# ARK_API_KEY=
# ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
# ARK_MODEL_ID=
EOF
echo '✓ 环境配置文件创建完成'
echo ''

echo '测试应用导入...'
python -c \"from web.web_server_refactored import app; print('✓ 应用导入成功')\" 2>&1 || {
    echo '❌ 应用导入失败'
    exit 1
}
echo ''
"

echo ========================================
echo    步骤 5/5: 启动服务
echo ========================================
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "
echo '启动服务...'
cd %REMOTE_PATH%
source venv/bin/activate
nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app > logs/gunicorn.log 2>&1 &
sleep 5

if lsof -ti:5000 >/dev/null 2>&1; then
    echo ''
    echo '========================================'
    echo '   ✓ 部署成功！服务已启动'
    echo '========================================'
    echo ''
    echo '服务信息:'
    echo '  端口: 5000'
    echo '  PID: '$(lsof -ti:5000)
    echo ''
    echo '访问地址: http://%SERVER_IP%:5000'
    echo ''
    echo '查看日志:'
    echo '  tail -f %REMOTE_PATH%/logs/application.log'
    echo '  tail -f %REMOTE_PATH%/logs/error.log'
    echo ''
else
    echo ''
    echo '========================================'
    echo '   ❌ 服务启动失败'
    echo '========================================'
    echo ''
    echo '请检查日志:'
    echo '  tail -50 %REMOTE_PATH%/logs/error.log'
    echo '  tail -50 %REMOTE_PATH%/logs/gunicorn.log'
    echo ''
    exit 1
fi
"

echo.
echo ========================================
echo    部署完成！
echo ========================================
echo.
echo 请访问: http://%SERVER_IP%:5000
echo.
pause