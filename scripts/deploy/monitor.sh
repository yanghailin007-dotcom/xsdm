#!/bin/bash

# 服务器监控脚本
# 使用方法: bash monitor.sh

echo "========================================"
echo "   服务器状态监控"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. 系统信息
echo -e "${BLUE}=== 系统信息 ===${NC}"
echo "主机名: $(hostname)"
echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d '"' -f 2)"
echo "内核版本: $(uname -r)"
echo "运行时间: $(uptime -p)"
echo ""

# 2. CPU使用率
echo -e "${BLUE}=== CPU使用率 ===${NC}"
top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print "CPU使用率: " 100 - $1"%"}'
echo ""

# 3. 内存使用
echo -e "${BLUE}=== 内存使用 ===${NC}"
free -h | awk 'NR==2{printf "总计: %s\n已用: %s (%.2f%%)\n空闲: %s\n", $2,$3,$3*100/$2,$4}'
echo ""

# 4. 磁盘使用
echo -e "${BLUE}=== 磁盘使用 ===${NC}"
df -h | awk '$NF=="/"{printf "根分区: %s (已用: %s / 总计: %s)\n", $5, $3, $2}'
echo ""

# 5. 网络连接
echo -e "${BLUE}=== 网络连接 ===${NC}"
echo "监听端口:"
netstat -tulpn 2>/dev/null | grep LISTEN | awk '{print $4, $7}' | head -10
echo ""

# 6. 应用状态
echo -e "${BLUE}=== 应用状态 ===${NC}"
if command -v supervisorctl &> /dev/null; then
    echo "Supervisor服务:"
    supervisorctl status all 2>/dev/null | grep -E "novel-system|RUNNING|STOPPED|FATAL"
else
    echo -e "${YELLOW}Supervisor未安装${NC}"
fi
echo ""

# 7. Nginx状态
echo -e "${BLUE}=== Nginx状态 ===${NC}"
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx运行中${NC}"
    systemctl status nginx --no-pager -l | grep "Active:" 
else
    echo -e "${RED}✗ Nginx未运行${NC}"
fi
echo ""

# 8. 最近的错误日志
echo -e "${BLUE}=== 最近的错误日志（最后5行）===${NC}"
if [ -f "/var/log/nginx/novel-system-error.log" ]; then
    echo "Nginx错误日志:"
    tail -5 /var/log/nginx/novel-system-error.log
else
    echo -e "${YELLOW}未找到Nginx错误日志${NC}"
fi
echo ""

# 9. 应用错误日志
APP_USER=${APP_USER:-novelapp}
PROJECT_DIR="/home/$APP_USER/novel-system"
if [ -f "$PROJECT_DIR/logs/gunicorn-error.log" ]; then
    echo "应用错误日志:"
    tail -5 $PROJECT_DIR/logs/gunicorn-error.log
else
    echo -e "${YELLOW}未找到应用错误日志${NC}"
fi
echo ""

echo "========================================"
echo "监控完成"
echo "========================================"