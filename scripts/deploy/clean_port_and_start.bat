@echo off
chcp 65001 >nul
echo ========================================
echo    清理端口并启动服务
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

echo 正在连接服务器并清理端口5000...
ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -l" << 'ENDSSH'
#!/bin/bash
set -e

echo "步骤 1/3: 查找占用端口5000的进程..."
PORT_PID=$(lsof -ti:5000 2>/dev/null || echo "无")

if [ -n "$PORT_PID" ]; then
    echo "找到占用端口的进程: $PORT_PID"
    echo ""
    echo "进程详情:"
    ps -fp $PORT_PID || true
    echo ""
    echo "正在终止进程..."
    kill -9 $PORT_PID
    echo "✓ 进程已终止"
    echo ""
    sleep 2
else
    echo "✓ 端口5000未被占用"
fi

echo ""
echo "步骤 2/3: 进入项目目录并激活虚拟环境..."
cd /home/novelapp/novel-system
source venv/bin/activate
echo "✓ 虚拟环境已激活"

echo ""
echo "步骤 3/3: 启动Gunicorn服务..."
echo "使用WSGI入口文件..."
nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log --log-level info web.wsgi:app > logs/gunicorn.log 2>&1 &
GUNICORN_PID=$!

echo "✓ Gunicorn服务已启动 (PID: $GUNICORN_PID)"
echo ""
echo "========================================"
echo "✓ 服务启动成功！"
echo "========================================"
echo ""
echo "PID: $GUNICORN_PID"
echo "访问地址: http://8.163.37.124:5000"
echo ""
echo "查看日志:"
echo "  tail -f /home/novelapp/novel-system/logs/gunicorn.log"
echo "  tail -f /home/novelapp/novel-system/logs/access.log"
echo ""
echo "停止服务:"
echo "  kill $GUNICORN_PID"
echo "  或"
echo "  lsof -ti:5000 | xargs kill -9"
echo ""

# 等待几秒让服务完全启动
echo "等待服务启动..."
sleep 5

# 检查服务是否正常运行
if lsof -i:5000 > /dev/null 2>&1; then
    echo "✓ 服务正在运行"
    echo ""
    echo "监听端口:"
    netstat -tulpn | grep :5000 || ss -tulpn | grep :5000 || lsof -i:5000
else
    echo "❌ 服务未能正常启动"
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
echo 如果服务启动成功，请访问: http://8.163.37.124:5000
echo.
pause