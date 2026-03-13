#!/bin/bash
# 清理缓存并启动服务器
# 用法: sh start_clean.sh

echo "============================================"
echo "🧹 清理缓存并启动服务器"
echo "============================================"
echo ""

# 1. 清理 Python 缓存
echo "🔍 清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
echo "✅ Python 缓存已清理"
echo ""

# 2. 清理运行时文件
echo "🔍 清理运行时文件..."
rm -f .server.pid 2>/dev/null
rm -f logs/server_*.log 2>/dev/null
echo "✅ 运行时文件已清理"
echo ""

# 3. 确保日志目录存在
mkdir -p logs
echo "✅ 日志目录已确认"
echo ""

# 4. 拉取最新代码（可选）
if [ "$1" == "--pull" ]; then
    echo "🔄 拉取最新代码..."
    git pull
    echo "✅ 代码已更新"
    echo ""
fi

# 5. 启动服务器
echo "🚀 启动服务器..."
echo "============================================"

# 检测启动方式
if [ -f "start.sh" ]; then
    sh start.sh
elif [ -f "deploy/start_production.sh" ]; then
    sh deploy/start_production.sh
elif [ -f "web/wsgi.py" ]; then
    # 使用 Python 直接启动
    source .venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
    python -m web.web_server_refactored
else
    echo "❌ 未找到启动脚本"
    exit 1
fi
