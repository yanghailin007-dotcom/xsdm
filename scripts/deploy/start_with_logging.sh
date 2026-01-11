#!/bin/bash
set -e

echo "========================================"
echo "启动应用服务 (带日志记录)"
echo "========================================"
echo ""

# 进入项目目录
cd /home/novelapp/novel-system

# 激活虚拟环境
source venv/bin/activate

# 确保日志目录存在
mkdir -p logs

# 记录开始时间
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动应用服务" | tee -a logs/application.log

# 检查并停止旧进程
echo "检查并停止旧进程..." | tee -a logs/application.log
OLD_PID=$(lsof -ti:5000 2>/dev/null || echo "")
if [ -n "$OLD_PID" ]; then
    echo "发现运行中的进程 PID: $OLD_PID，正在停止..." | tee -a logs/application.log
    kill -9 $OLD_PID 2>/dev/null || true
    sleep 2
    echo "旧进程已停止" | tee -a logs/application.log
else
    echo "没有发现运行中的进程" | tee -a logs/application.log
fi

# 等待端口释放
echo "等待端口释放..." | tee -a logs/application.log
for i in {1..10}; do
    if ! lsof -ti:5000 >/dev/null 2>&1; then
        echo "端口5000已释放" | tee -a logs/application.log
        break
    fi
    echo "等待中... ($i/10)" | tee -a logs/application.log
    sleep 1
done

# 创建日志文件（如果不存在）
touch logs/application.log
touch logs/gunicorn.log
touch logs/access.log
touch logs/error.log

echo "" | tee -a logs/application.log
echo "========================================" | tee -a logs/application.log
echo "启动 Gunicorn 服务器" | tee -a logs/application.log
echo "========================================" | tee -a logs/application.log
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a logs/application.log
echo "工作目录: $(pwd)" | tee -a logs/application.log
echo "Python版本: $(python --version)" | tee -a logs/application.log
echo "Gunicorn版本: $(gunicorn --version)" | tee -a logs/application.log
echo "" | tee -a logs/application.log

# 启动 Gunicorn 服务器（后台运行）
echo "启动命令: gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app" | tee -a logs/application.log

nohup gunicorn -w 2 \
    -b 0.0.0.0:5000 \
    --timeout 600 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info \
    --capture-output \
    web.wsgi:app \
    > logs/gunicorn.log 2>&1 &

NEW_PID=$!
echo "Gunicorn 进程 PID: $NEW_PID" | tee -a logs/application.log

# 等待服务启动
echo "" | tee -a logs/application.log
echo "等待服务启动..." | tee -a logs/application.log
sleep 5

# 检查服务是否启动成功
if lsof -ti:5000 >/dev/null 2>&1; then
    echo "" | tee -a logs/application.log
    echo "========================================" | tee -a logs/application.log
    echo "✓ 服务启动成功！" | tee -a logs/application.log
    echo "========================================" | tee -a logs/application.log
    echo "" | tee -a logs/application.log
    echo "服务信息：" | tee -a logs/application.log
    echo "  PID: $(lsof -ti:5000)" | tee -a logs/application.log
    echo "  端口: 5000" | tee -a logs/application.log
    echo "  访问地址: http://$(hostname -I | awk '{print $1}'):5000" | tee -a logs/application.log
    echo "" | tee -a logs/application.log
    echo "日志文件：" | tee -a logs/application.log
    echo "  - 应用日志: logs/application.log" | tee -a logs/application.log
    echo "  - Gunicorn日志: logs/gunicorn.log" | tee -a logs/application.log
    echo "  - 访问日志: logs/access.log" | tee -a logs/application.log
    echo "  - 错误日志: logs/error.log" | tee -a logs/application.log
    echo "" | tee -a logs/application.log
    echo "查看日志命令：" | tee -a logs/application.log
    echo "  tail -f logs/application.log  # 应用主日志" | tee -a logs/application.log
    echo "  tail -f logs/gunicorn.log     # Gunicorn日志" | tee -a logs/application.log
    echo "  tail -f logs/access.log       # 访问日志" | tee -a logs/application.log
    echo "  tail -f logs/error.log        # 错误日志" | tee -a logs/application.log
    echo "" | tee -a logs/application.log
    echo "停止服务命令：" | tee -a logs/application.log
    echo "  lsof -ti:5000 | xargs kill -9" | tee -a logs/application.log
    echo "" | tee -a logs/application.log
else
    echo "" | tee -a logs/application.log
    echo "❌ 服务启动失败！" | tee -a logs/application.log
    echo "请检查错误日志: logs/error.log" | tee -a logs/application.log
    echo "请检查 Gunicorn 日志: logs/gunicorn.log" | tee -a logs/application.log
    exit 1
fi