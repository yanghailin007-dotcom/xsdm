#!/bin/bash
set -e

echo "步骤 1/6: 检查上传的压缩包..."
TAR_FILE=$(ls -t /tmp/novel_system_*.tar.gz 2>/dev/null | head -1)
if [ -z "$TAR_FILE" ]; then
    echo "错误: 未找到压缩包"
    exit 1
fi
echo "找到压缩包: $TAR_FILE"
ls -lh "$TAR_FILE"
echo ""

echo "步骤 2/6: 创建项目目录..."
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
echo "目录已创建"
echo ""

echo "步骤 3/6: 解压代码..."
cd /home/novelapp/novel-system
tar -xzf "$TAR_FILE"
rm -f "$TAR_FILE"
echo "代码已解压"
ls -la | head -20
echo ""

echo "步骤 4/6: 设置虚拟环境..."
PYTHON_CMD=$(command -v python3 || echo "")
if [ -z "$PYTHON_CMD" ]; then
    echo "错误: 未找到 Python 3"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version)
echo "使用 $PYTHON_VERSION"

$PYTHON_CMD -m venv venv
echo "虚拟环境已创建"

source venv/bin/activate
pip install --upgrade pip -q
pip install flask gunicorn eventlet -q

if [ -f requirements.txt ]; then
    echo "正在安装依赖..."
    pip install -r requirements.txt -q || echo "警告: 部分依赖安装失败"
fi
echo "依赖已安装"
echo ""

echo "步骤 5/6: 创建配置文件..."
cat > .env << 'ENVEOF'
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False
LOG_LEVEL=INFO
ENVEOF
echo "配置文件已创建"
echo ""

echo "步骤 6/6: 启动应用服务..."
pkill -f "gunicorn.*web.wsgi" || true
sleep 2

nohup gunicorn \
  -w 2 \
  -b 0.0.0.0:5000 \
  --timeout 600 \
  --daemon \
  --pid /tmp/novel_system.pid \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  web.wsgi:app

sleep 5

if pgrep -f "gunicorn.*web.wsgi" > /dev/null; then
    echo "✓ 服务启动成功"
else
    echo "✗ 服务启动失败，查看错误日志："
    tail -20 logs/error.log 2>/dev/null || echo "日志文件不存在"
    exit 1
fi

echo ""
echo "正在测试应用..."
sleep 2

if curl -s http://127.0.0.1:5000/ > /dev/null 2>&1; then
    echo "✓ 应用响应正常"
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/)
    echo "✓ HTTP 状态码: $HTTP_STATUS"
else
    echo "✗ 应用无响应"
    exit 1
fi

echo ""
echo "========================================"
echo "✓ 部署完成！"
echo "========================================"
echo ""
IP=$(hostname -I | awk '{print $1}')
echo "访问网站: http://$IP:5000"
echo ""
echo "服务管理命令:"
echo "  查看状态: pgrep -f gunicorn"
echo "  停止服务: pkill -f gunicorn"
echo "  查看日志: tail -f /home/novelapp/novel-system/logs/error.log"
echo "  重启服务: cd /home/novelapp/novel-system && source venv/bin/activate && gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --daemon web.wsgi:app"
echo ""
