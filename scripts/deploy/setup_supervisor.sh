#!/bin/bash

# Supervisor配置脚本
# 使用方法: sudo bash setup_supervisor.sh

set -e

echo "========================================"
echo "   配置Supervisor服务"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用sudo运行此脚本${NC}"
    exit 1
fi

# 获取配置
read -p "请输入应用用户名 (默认: novelapp): " APP_USER
APP_USER=${APP_USER:-novelapp}

PROJECT_DIR="/home/$APP_USER/novel-system"
WORKERS=$(($(nproc) * 2 + 1))

echo -e "${YELLOW}应用用户: $APP_USER${NC}"
echo -e "${YELLOW}项目目录: $PROJECT_DIR${NC}"
echo -e "${YELLOW}Worker数量: $WORKERS${NC}"
echo ""

# 检查项目目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}错误: 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

# 创建Supervisor配置
echo -e "${YELLOW}创建Supervisor配置...${NC}"
cat > /etc/supervisor/conf.d/novel-system.conf <<EOF
[program:novel-system]
command=$PROJECT_DIR/venv/bin/gunicorn -w $WORKERS -b 127.0.0.1:5000 --timeout 600 --access-logfile $PROJECT_DIR/logs/gunicorn-access.log --error-logfile $PROJECT_DIR/logs/gunicorn-error.log --log-level info web.web_server_refactored:app
directory=$PROJECT_DIR
user=$APP_USER
autostart=true
autorestart=true
startretries=3
stderr_logfile=$PROJECT_DIR/logs/supervisor-stderr.log
stdout_logfile=$PROJECT_DIR/logs/supervisor-stdout.log
environment=FLASK_ENV="production"
EOF

echo -e "${GREEN}✓ Supervisor配置创建完成${NC}"

# 重新加载Supervisor
echo -e "${YELLOW}重新加载Supervisor配置...${NC}"
supervisorctl reread
supervisorctl update

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
supervisorctl start novel-system

# 等待服务启动
sleep 3

# 检查服务状态
echo ""
echo -e "${YELLOW}检查服务状态...${NC}"
supervisorctl status novel-system

echo ""
echo "========================================"
echo -e "${GREEN}✓ Supervisor配置完成！${NC}"
echo "========================================"
echo ""
echo "常用命令:"
echo "  查看状态: sudo supervisorctl status novel-system"
echo "  重启服务: sudo supervisorctl restart novel-system"
echo "  停止服务: sudo supervisorctl stop novel-system"
echo "  查看日志: sudo supervisorctl tail -f novel-system"
echo ""