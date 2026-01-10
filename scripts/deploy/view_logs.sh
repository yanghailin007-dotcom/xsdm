#!/bin/bash

# 日志查看脚本
# 使用方法: bash view_logs.sh [log_type]

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_USER=${APP_USER:-novelapp}
PROJECT_DIR="/home/$APP_USER/novel-system"

echo "========================================"
echo "   日志查看工具"
echo "========================================"
echo ""

# 显示菜单
show_menu() {
    echo -e "${BLUE}请选择要查看的日志:${NC}"
    echo "1) Supervisor日志 (实时)"
    echo "2) Gunicorn错误日志 (实时)"
    echo "3) Gunicorn访问日志 (实时)"
    echo "4) Nginx错误日志 (实时)"
    echo "5) Nginx访问日志 (实时)"
    echo "6) 查看最近的Supervisor日志 (最后50行)"
    echo "7) 查看最近的Gunicorn错误 (最后50行)"
    echo "8) 查看最近的Nginx错误 (最后50行)"
    echo "0) 退出"
    echo ""
}

# 主循环
while true; do
    show_menu
    read -p "请输入选项: " choice
    
    case $choice in
        1)
            echo -e "${GREEN}查看Supervisor日志 (按Ctrl+C退出)...${NC}"
            supervisorctl tail -f novel-system 2>/dev/null || echo -e "${RED}无法查看Supervisor日志${NC}"
            ;;
        2)
            echo -e "${GREEN}查看Gunicorn错误日志 (按Ctrl+C退出)...${NC}"
            tail -f $PROJECT_DIR/logs/gunicorn-error.log 2>/dev/null || echo -e "${RED}日志文件不存在${NC}"
            ;;
        3)
            echo -e "${GREEN}查看Gunicorn访问日志 (按Ctrl+C退出)...${NC}"
            tail -f $PROJECT_DIR/logs/gunicorn-access.log 2>/dev/null || echo -e "${RED}日志文件不存在${NC}"
            ;;
        4)
            echo -e "${GREEN}查看Nginx错误日志 (按Ctrl+C退出)...${NC}"
            sudo tail -f /var/log/nginx/novel-system-error.log 2>/dev/null || echo -e "${RED}日志文件不存在${NC}"
            ;;
        5)
            echo -e "${GREEN}查看Nginx访问日志 (按Ctrl+C退出)...${NC}"
            sudo tail -f /var/log/nginx/novel-system-access.log 2>/dev/null || echo -e "${RED}日志文件不存在${NC}"
            ;;
        6)
            echo -e "${GREEN}最近50行Supervisor日志:${NC}"
            supervisorctl tail -500 novel-system 2>/dev/null | tail -50 || echo -e "${RED}无法查看日志${NC}"
            echo ""
            read -p "按Enter继续..."
            ;;
        7)
            echo -e "${GREEN}最近50行Gunicorn错误日志:${NC}"
            tail -50 $PROJECT_DIR/logs/gunicorn-error.log 2>/dev/null || echo -e "${RED}日志文件不存在${NC}"
            echo ""
            read -p "按Enter继续..."
            ;;
        8)
            echo -e "${GREEN}最近50行Nginx错误日志:${NC}"
            sudo tail -50 /var/log/nginx/novel-system-error.log 2>/dev/null || echo -e "${RED}日志文件不存在${NC}"
            echo ""
            read -p "按Enter继续..."
            ;;
        0)
            echo "退出"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选项${NC}"
            echo ""
            read -p "按Enter继续..."
            ;;
    esac
done