@echo off
chcp 65001 >nul
echo ========================================
echo    上传并重启服务
echo ========================================
echo.

set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

icacls "%KEY_PATH%" /inheritance:r >nul 2>&1
icacls "%KEY_PATH%" /grant:r "%USERNAME%:F" >nul 2>&1

echo 正在上传最新文件到服务器...
echo.

REM 上传WSGI入口
echo 上传 web/wsgi.py...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no web\wsgi.py %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/web/

REM 上传启动脚本
echo 上传 scripts/start_app.py...
scp -i "%KEY_PATH%" -P 22 -o StrictHostKeyChecking=no scripts\start_app.py %SERVER_USER%@%SERVER_IP%:/home/novelapp/novel-system/scripts/

echo ✓ 文件上传完成
echo.

echo 正在重启服务器上的服务...
echo.
echo "========================================"
echo "   重启服务"
echo "========================================"
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -l" << 'ENDSSH'
#!/bin/bash
set -e

echo "1/3: 清理端口5000..."
fuser -k 5000/tcp 2>/dev/null || lsof -ti:5000 | xargs kill -9 2>/dev/null || echo "  无进程占用"
echo "  ✓ 端口已清理"

echo ""
echo "2/3: 进入项目目录..."
cd /home/novelapp/novel-system

echo ""
echo "3/3: 重启服务..."
source venv/bin/activate

# 停止旧服务
lsof -ti:5000 | xargs kill -9 2>/dev/null || true
sleep 2

# 启动新服务
nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log --log-level info web.wsgi:app > logs/gunicorn.log 2>&1 &

echo "  ✓ 服务已启动"

# 等待服务完全启动
sleep 3

# 检查服务状态
if lsof -i:5000 > /dev/null 2>&1; then
    echo ""
    echo "========================================"
    echo "✓ 服务启动成功！"
    echo "========================================"
    echo ""
    IP=$(hostname -I | awk '{print $1}')
    echo "访问地址: http://$IP:5000"
    echo ""
    echo "查看日志:"
    echo "  tail -f /home/novelapp/novel-system/logs/gunicorn.log"
    echo ""
    echo "停止服务:"
    echo "  lsof -ti:5000 | xargs kill -9"
else
    echo ""
    echo "❌ 服务启动失败"
    echo ""
    echo "查看错误日志:"
    tail -20 /home/novelapp/novel-system/logs/gunicorn.log
fi
ENDSSH

echo.
echo ========================================
echo    完成！
echo ========================================
echo.

pause