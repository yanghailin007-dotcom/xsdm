#!/bin/bash
set -e

echo "========================================"
echo "初始化服务器日志系统"
echo "========================================"
echo ""

# 进入项目目录
cd /home/novelapp/novel-system 2>/dev/null || {
    echo "❌ 项目目录不存在: /home/novelapp/novel-system"
    echo "请先运行完整部署脚本"
    exit 1
}

# 创建日志目录
echo "创建日志目录..."
mkdir -p logs
echo "✓ 日志目录创建完成"

# 创建空的日志文件
echo ""
echo "初始化日志文件..."
touch logs/application.log
touch logs/gunicorn.log
touch logs/access.log
touch logs/error.log

# 写入初始化信息
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIMESTAMP] 日志系统初始化" >> logs/application.log
echo "[$TIMESTAMP] 日志目录: $(pwd)/logs" >> logs/application.log
echo "[$TIMESTAMP] Python版本: $(python --version)" >> logs/application.log

echo "✓ 日志文件创建完成"

# 检查是否有运行中的服务
echo ""
echo "检查服务状态..."
if lsof -ti:5000 >/dev/null 2>&1; then
    PID=$(lsof -ti:5000)
    echo "✓ 发现运行中的服务 (PID: $PID)"
    echo "[$TIMESTAMP] 检测到运行中的服务 PID: $PID" >> logs/application.log
    
    # 检查是否是gunicorn
    if ps -p $PID -o command= | grep -q gunicorn; then
        echo "✓ 服务类型: Gunicorn"
        echo "[$TIMESTAMP] 服务类型: Gunicorn" >> logs/application.log
    fi
else
    echo "⚠ 没有发现运行中的服务"
    echo "[$TIMESTAMP] 警告: 没有发现运行中的服务" >> logs/application.log
    echo ""
    echo "提示: 运行以下命令启动服务"
    echo "  cd /home/novelapp/novel-system"
    echo "  source venv/bin/activate"
    echo "  bash /tmp/start_with_logging.sh"
fi

# 显示日志文件信息
echo ""
echo "========================================"
echo "日志文件信息"
echo "========================================"
ls -lh logs/

echo ""
echo "========================================"
echo "✓ 日志系统初始化完成！"
echo "========================================"
echo ""
echo "日志文件位置: /home/novelapp/novel-system/logs/"
echo "  - application.log  (应用主日志)"
echo "  - gunicorn.log     (Gunicorn日志)"
echo "  - access.log       (访问日志)"
echo "  - error.log        (错误日志)"
echo ""