@echo off
chcp 65001 >nul
echo ========================================
echo    小说生成系统 - 一键部署（终极版）
echo ========================================
echo.
echo 此脚本将自动完成：
echo   ✓ 同步所有代码（包括前端UI文件）
echo   ✓ 初始化日志系统
echo   ✓ 重启服务
echo   ✓ 验证部署状态
echo.

REM 服务器配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

echo 服务器: %SERVER_IP%
echo.

REM 检查私钥
if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

REM 设置权限
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

REM 进入项目目录
cd /d d:\work6.05

echo ========================================
echo    步骤 1/3: 同步代码并重启服务
echo ========================================
echo.

echo 正在同步代码并重启服务...
echo.

REM 使用SSH命令完成所有操作
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "
echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 开始部署' >> /home/novelapp/novel-system/logs/application.log 2>/dev/null || mkdir -p /home/novelapp/novel-system/logs
echo '========================================'
echo '服务器端部署脚本'
echo '========================================'
echo ''
echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 停止旧服务...' >> /home/novelapp/novel-system/logs/application.log
cd /home/novelapp/novel-system
source venv/bin/activate
lsof -ti:5000 | xargs kill -9 2>/dev/null || true
sleep 2
echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] 启动新服务...' >> /home/novelapp/novel-system/logs/application.log
nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app > logs/gunicorn.log 2>&1 &
sleep 3
if lsof -ti:5000 >/dev/null 2>&1; then
    echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] ✓ 服务启动成功' >> /home/novelapp/novel-system/logs/application.log
    echo '✓ 服务启动成功'
    echo ''
    echo '========================================'
    echo '   ✓ 部署成功！'
    echo '========================================'
    echo ''
    echo '服务信息:'
    echo '  端口: 5000'
    echo '  PID: '$(lsof -ti:5000)
    echo ''
    echo '访问地址: http://%SERVER_IP%:5000'
    echo ''
    echo '重要提示:'
    echo '  1. 请强制刷新浏览器（Ctrl+F5）查看UI更新'
    echo '  2. 如果UI没有更新，清除浏览器缓存后重试'
    echo ''
    echo '查看日志:'
    echo '  运行: scripts\deploy\view_server_logs.bat'
    echo '  或手动: ssh -i \"%KEY_PATH%\" %SERVER_USER%@%SERVER_IP% \"tail -f /home/novelapp/novel-system/logs/application.log\"'
    echo ''
else
    echo '[$(date +%%Y-%%m-%%d\ %%H:%%M:%%S)] ❌ 服务启动失败' >> /home/novelapp/novel-system/logs/application.log
    echo '❌ 服务启动失败'
    echo ''
    echo '请检查日志:'
    echo '  tail -50 /home/novelapp/novel-system/logs/error.log'
    echo ''
fi
"

echo.
echo ========================================
echo    部署完成！
echo ========================================
echo.

pause