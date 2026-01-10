#!/bin/bash

# 应用部署脚本 - 在服务器上执行
# 使用方法: bash deploy_app.sh

set -e

echo "========================================"
echo "   小说生成系统 - 应用部署脚本"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
APP_USER=${APP_USER:-novelapp}
PROJECT_DIR="/home/$APP_USER/novel-system"

echo -e "${YELLOW}步骤 1/7: 检查环境${NC}"
echo "当前目录: $(pwd)"
echo "项目目录: $PROJECT_DIR"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}错误: 项目目录不存在${NC}"
    exit 1
fi

cd $PROJECT_DIR
echo -e "${GREEN}✓ 环境检查完成${NC}"
echo ""

# 创建虚拟环境
echo -e "${YELLOW}步骤 2/7: 创建Python虚拟环境${NC}"
if [ ! -d "venv" ]; then
    python3.10 -m venv venv
    echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"
else
    echo -e "${YELLOW}虚拟环境已存在${NC}"
fi
echo ""

# 激活虚拟环境
source venv/bin/activate

# 升级pip
echo -e "${YELLOW}步骤 3/7: 升级pip${NC}"
pip install --upgrade pip
echo -e "${GREEN}✓ pip升级完成${NC}"
echo ""

# 安装依赖
echo -e "${YELLOW}步骤 4/7: 安装Python依赖${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ 依赖安装完成${NC}"
else
    echo -e "${RED}错误: requirements.txt不存在${NC}"
    exit 1
fi
echo ""

# 安装生产环境依赖
echo -e "${YELLOW}步骤 5/7: 安装生产环境依赖${NC}"
pip install gunicorn eventlet
echo -e "${GREEN}✓ 生产环境依赖安装完成${NC}"
echo ""

# 配置环境变量
echo -e "${YELLOW}步骤 6/7: 配置环境变量${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ .env文件已创建${NC}"
        echo -e "${YELLOW}请编辑 .env 文件配置您的环境变量${NC}"
        echo -e "命令: vim .env"
    else
        echo -e "${RED}错误: .env.example不存在${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}.env文件已存在${NC}"
fi
echo ""

# 创建必要的目录
echo -e "${YELLOW}步骤 7/7: 创建必要目录${NC}"
mkdir -p logs data generated_images temp_fanqie_upload
echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""

echo "========================================"
echo -e "${GREEN}✓ 应用部署完成！${NC}"
echo "========================================"
echo ""
echo "接下来的步骤:"
echo "1. 配置环境变量:"
echo "   vim .env"
echo ""
echo "2. 初始化数据库（如果需要）:"
echo "   source venv/bin/activate"
echo "   python -c \"from web.models.user_model import db; from web.web_server_refactored import app; app.app_context().push(); db.create_all()\""
echo ""
echo "3. 配置并启动Supervisor服务:"
echo "   sudo bash $PROJECT_DIR/scripts/deploy/setup_supervisor.sh"
echo ""
echo "4. 查看服务状态:"
echo "   sudo supervisorctl status novel-system"
echo ""