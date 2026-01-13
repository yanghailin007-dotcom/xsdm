@echo off
chcp 65001 >nul
echo ========================================
echo    小说生成系统 - 一键部署（完整版）
echo ========================================
echo.
echo 此脚本将自动完成：
echo   ✓ 同步所有代码（包括前端UI文件）
echo   ✓ 重启Web服务
echo   ✓ 验证部署状态
echo.
pause

REM ========================================
REM 配置部分
REM ========================================
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem
set LOCAL_ROOT=d:\work6.05
set REMOTE_PATH=/home/novelapp/novel-system

echo 服务器: %SERVER_IP%
echo 本地路径: %LOCAL_ROOT%
echo 远程路径: %REMOTE_PATH%
echo.

REM ========================================
REM 1. 检查环境
REM ========================================
echo [步骤 1/5] 检查部署环境...
echo.

REM 检查私钥文件
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)
echo ✓ 私钥文件存在

REM 检查项目目录
if not exist "%LOCAL_ROOT%\src" (
    echo ❌ 项目目录不存在: %LOCAL_ROOT%
    pause
    exit /b 1
)
echo ✓ 项目目录存在

REM 设置私钥权限
icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1
echo ✓ 私钥权限设置完成

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

REM ========================================
REM 2. 同步代码到服务器
REM ========================================
echo [步骤 2/5] 同步代码到服务器...
echo.
echo 正在同步以下目录和文件：
echo   - src/ (核心代码)
echo   - web/ (Web应用和UI文件)
echo   - config/ (配置文件)
echo   - scripts/ (脚本文件)
echo   - requirements.txt (依赖)
echo.

REM 使用SCP同步文件（逐个同步关键目录）
echo 正在同步 src/ ...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no -r "%LOCAL_ROOT%\src" %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/temp_src >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ 同步 src/ 失败
    pause
    exit /b 1
)
echo ✓ src/ 同步完成

echo 正在同步 web/ (包含UI文件)...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no -r "%LOCAL_ROOT%\web" %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/temp_web >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ 同步 web/ 失败
    pause
    exit /b 1
)
echo ✓ web/ 同步完成（已包含所有UI文件）

echo 正在同步 config/ ...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no -r "%LOCAL_ROOT%\config" %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/temp_config >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ 同步 config/ 失败
    pause
    exit /b 1
)
echo ✓ config/ 同步完成

echo 正在同步 requirements.txt ...
scp -i "%KEY_PATH%" -o StrictHostKeyChecking=no "%LOCAL_ROOT%\requirements.txt" %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%/temp_requirements.txt >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ 同步 requirements.txt 失败
    pause
    exit /b 1
)
echo ✓ requirements.txt 同步完成

echo.

REM ========================================
REM 3. 服务器端部署操作
REM ========================================
echo [步骤 3/5] 执行服务器端部署...
echo.

ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "
echo '========================================'
echo '服务器端部署脚本'
echo '========================================'
echo ''

# 进入项目目录
cd %REMOTE_PATH%

# 记录部署日志
mkdir -p logs
echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 开始部署更新\" >> logs/application.log

# 停止旧服务
echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 停止旧服务...\" >> logs/application.log
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
sleep 2

# 备份旧代码
echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 备份旧代码...\" >> logs/application.log
rm -rf src_backup web_backup config_backup
mv src src_backup 2>/dev/null || true
mv web web_backup 2>/dev/null || true
mv config config_backup 2>/dev/null || true

# 部署新代码
echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 部署新代码...\" >> logs/application.log
mv temp_src src
mv temp_web web
mv temp_config config
mv temp_requirements.txt requirements.txt

# 更新依赖
echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 更新依赖...\" >> logs/application.log
source venv/bin/activate
pip install -r requirements.txt --quiet 2>/dev/null || echo \"依赖更新有警告，继续部署\" >> logs/application.log

echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 代码部署完成\" >> logs/application.log
"
if %ERRORLEVEL% neq 0 (
    echo ❌ 服务器端部署失败
    pause
    exit /b 1
)
echo ✓ 服务器端部署完成
echo.

REM ========================================
REM 4. 启动Web服务
REM ========================================
echo [步骤 4/5] 启动Web服务...
echo.

ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "
cd %REMOTE_PATH%
source venv/bin/activate
echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 启动Web服务...\" >> logs/application.log
nohup gunicorn -w 2 -b 0.0.0.0:8080 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app > logs/gunicorn.log 2>&1 &
sleep 5

if lsof -ti:8080 >/dev/null 2>&1; then
    echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] ✓ 服务启动成功\" >> logs/application.log
    echo '✓ 服务启动成功'
    echo '  端口: 8080'
    echo '  PID: '\$(lsof -ti:8080)
else
    echo \"[\$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] ❌ 服务启动失败\" >> logs/application.log
    echo '❌ 服务启动失败'
    exit 1
fi
"
if %ERRORLEVEL% neq 0 (
    echo ❌ 服务启动失败
    echo.
    echo 请检查日志：
    echo   运行: scripts\deploy\view_server_logs.bat
    pause
    exit /b 1
)
echo.

REM ========================================
REM 5. 验证部署
REM ========================================
echo [步骤 5/5] 验证部署状态...
echo.

echo 测试Web服务...
curl -s -o nul -w "%%{http_code}" http://%SERVER_IP%:8080/ 2>nul | findstr "200" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo ✓ Web服务正常响应
) else (
    echo ⚠ Web服务响应检查失败（可能仍在启动中）
)

echo.
echo ========================================
echo    ✓ 部署成功！
echo ========================================
echo.
echo 服务信息：
echo   服务器: %SERVER_IP%
echo   端口: 8080
echo.
echo 访问地址：
echo   http://%SERVER_IP%:8080
echo.
echo 重要提示：
echo   1. 请强制刷新浏览器（Ctrl+F5）查看UI更新
echo   2. 如果UI没有更新，清除浏览器缓存后重试
echo   3. 确保浏览器使用硬刷新（Ctrl+Shift+R）
echo.
echo 查看日志：
echo   运行: scripts\deploy\view_server_logs.bat
echo   或手动: ssh -i "%KEY_PATH%" %SERVER_USER%@%SERVER_IP% "tail -f /home/novelapp/novel-system/logs/application.log"
echo.

pause