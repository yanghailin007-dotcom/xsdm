#!/bin/bash
# 服务器端自动配置和启动脚本
# 同步完成后在服务器上运行此脚本

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/home/novelapp/novel-system"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_VERSION="python3"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  服务器自动配置和启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查是否在正确的目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}错误: 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# 1. 清理旧进程
echo -e "${YELLOW}[1/7] 清理旧进程...${NC}"

# 清理可能存在的Python进程
pkill -f "gunicorn" || true
pkill -f "python.*web_server" || true
pkill -f "flask" || true

# 清理端口占用
fuser -k 5000/tcp 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true

# 等待进程完全退出
sleep 2

echo -e "${GREEN}✓ 进程清理完成${NC}"
echo ""

# 2. 创建必要的目录
echo -e "${YELLOW}[2/7] 创建目录结构...${NC}"

mkdir -p logs
mkdir -p data
mkdir -p generated_images
mkdir -p temp_fanqie_upload

echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""

# 3. 创建Python虚拟环境（如果不存在）
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[3/7] 创建Python虚拟环境...${NC}"
    $PYTHON_VERSION -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"
else
    echo -e "${GREEN}[3/7] 虚拟环境已存在，跳过创建${NC}"
fi
echo ""

# 4. 激活虚拟环境并安装依赖
echo -e "${YELLOW}[4/7] 安装/更新依赖...${NC}"

source "$VENV_DIR/bin/activate"

# 升级pip
pip install --upgrade pip -q

# 安装依赖
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
    echo -e "${GREEN}✓ 依赖安装完成${NC}"
else
    echo -e "${RED}错误: 未找到 requirements.txt${NC}"
    exit 1
fi
echo ""

# 5. 配置环境变量
echo -e "${YELLOW}[5/7] 检查环境变量配置...${NC}"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠ 已创建 .env 文件，请手动编辑配置API密钥${NC}"
        echo -e "${YELLOW}   命令: vim .env${NC}"
    else
        echo -e "${RED}错误: 未找到 .env.example 文件${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi
echo ""

# 6. 配置Supervisor
echo -e "${YELLOW}[6/7] 配置Supervisor服务管理...${NC}"

SUPERVISOR_CONF="/etc/supervisor/conf.d/novel-system.conf"

# 创建Supervisor配置
sudo bash -c "cat > $SUPERVISOR_CONF" << 'EOF'
[program:novel-system]
command=/home/novelapp/novel-system/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 600 --access-logfile /home/novelapp/novel-system/logs/gunicorn-access.log --error-logfile /home/novelapp/novel-system/logs/gunicorn-error.log --log-level info web.wsgi:app
directory=/home/novelapp/novel-system
user=novelapp
autostart=true
autorestart=true
startretries=3
stderr_logfile=/home/novelapp/novel-system/logs/supervisor-stderr.log
stdout_logfile=/home/novelapp/novel-system/logs/supervisor-stdout.log
environment=FLASK_ENV="production"
EOF

# 重新加载Supervisor配置
sudo supervisorctl reread
sudo supervisorctl update

echo -e "${GREEN}✓ Supervisor配置完成${NC}"
echo ""

# 7. 启动服务
echo -e "${YELLOW}[7/7] 启动服务...${NC}"

# 使用Supervisor启动服务
sudo supervisorctl start novel-system

# 等待服务启动
sleep 3

# 检查服务状态
if sudo supervisorctl status novel-system | grep -q "RUNNING"; then
    echo -e "${GREEN}✓ 服务启动成功！${NC}"
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}  部署完成！${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${YELLOW}服务信息:${NC}"
    echo -e "  状态: ${GREEN}运行中${NC}"
    echo -e "  端口: 5000"
    echo -e "  日志: $PROJECT_DIR/logs/"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo -e "  查看状态: ${BLUE}sudo supervisorctl status novel-system${NC}"
    echo -e "  重启服务: ${BLUE}sudo supervisorctl restart novel-system${NC}"
    echo -e "  查看日志: ${BLUE}sudo supervisorctl tail -f novel-system${NC}"
    echo -e "  停止服务: ${BLUE}sudo supervisorctl stop novel-system${NC}"
    echo ""
    echo -e "${YELLOW}访问地址:${NC}"
    echo -e "  本地: ${BLUE}http://localhost:5000${NC}"
    echo -e "  公网: ${BLUE}http://8.163.37.124:5000${NC}"
    echo ""
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo -e "${YELLOW}查看错误日志:${NC}"
    echo -e "  tail -f $PROJECT_DIR/logs/gunicorn-error.log"
    exit 1
fi