#!/bin/bash

# 针对私网服务器的快速部署脚本
# 使用方法: sudo bash quick_deploy_private_server.sh

set -e

echo "========================================"
echo "   小说生成系统 - 私网服务器快速部署"
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

# 配置变量
APP_USER="novelapp"
PROJECT_DIR="/home/$APP_USER/novel-system"
WORKERS=$(($(nproc) * 2 + 1))

echo -e "${YELLOW}配置信息:${NC}"
echo "  应用用户: $APP_USER"
echo "  项目目录: $PROJECT_DIR"
echo "  Worker数量: $WORKERS"
echo ""

# 更新系统
echo -e "${YELLOW}步骤 1/10: 更新系统${NC}"
apt update && apt upgrade -y
echo -e "${GREEN}✓ 系统更新完成${NC}"
echo ""

# 安装基础工具
echo -e "${YELLOW}步骤 2/10: 安装基础工具${NC}"
apt install -y wget curl git vim build-essential software-properties-common lrzsz
echo -e "${GREEN}✓ 基础工具安装完成${NC}"
echo ""

# 安装Python
echo -e "${YELLOW}步骤 3/10: 安装Python 3.10${NC}"
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
echo -e "${GREEN}✓ Python安装完成${NC}"
python3.10 --version
echo ""

# 创建应用用户
echo -e "${YELLOW}步骤 4/10: 创建应用用户${NC}"
if id "$APP_USER" &>/dev/null; then
    echo -e "${YELLOW}用户 $APP_USER 已存在${NC}"
else
    useradd -m -s /bin/bash $APP_USER
    echo -e "${GREEN}✓ 用户 $APP_USER 创建完成${NC}"
fi
echo ""

# 创建项目目录
echo -e "${YELLOW}步骤 5/10: 创建项目目录${NC}"
mkdir -p $PROJECT_DIR
mkdir -p $PROJECT_DIR/logs
mkdir -p $PROJECT_DIR/data
mkdir -p $PROJECT_DIR/generated_images
mkdir -p $PROJECT_DIR/temp_fanqie_upload
chown -R $APP_USER:$APP_USER $PROJECT_DIR
echo -e "${GREEN}✓ 项目目录创建完成${NC}"
echo ""

# 安装Nginx
echo -e "${YELLOW}步骤 6/10: 安装Nginx${NC}"
apt install -y nginx
echo -e "${GREEN}✓ Nginx安装完成${NC}"
echo ""

# 配置Nginx
echo -e "${YELLOW}步骤 7/10: 配置Nginx${NC}"
cat > /etc/nginx/sites-available/novel-system <<'EOF'
server {
    listen 80;
    server_name _;

    access_log /var/log/nginx/novel-system-access.log;
    error_log /var/log/nginx/novel-system-error.log;

    client_max_body_size 100M;

    location /static {
        alias /home/novelapp/novel-system/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /generated_images {
        alias /home/novelapp/novel-system/generated_images;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }
}
EOF

ln -sf /etc/nginx/sites-available/novel-system /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl restart nginx
systemctl enable nginx
echo -e "${GREEN}✓ Nginx配置完成${NC}"
echo ""

# 安装Supervisor
echo -e "${YELLOW}步骤 8/10: 安装Supervisor${NC}"
apt install -y supervisor
echo -e "${GREEN}✓ Supervisor安装完成${NC}"
echo ""

# 配置Supervisor
echo -e "${YELLOW}步骤 9/10: 配置Supervisor${NC}"
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

supervisorctl reread
supervisorctl update
echo -e "${GREEN}✓ Supervisor配置完成${NC}"
echo ""

# 配置防火墙
echo -e "${YELLOW}步骤 10/10: 配置防火墙${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
    echo -e "${GREEN}✓ 防火墙配置完成${NC}"
else
    echo -e "${YELLOW}UFW未安装，跳过防火墙配置${NC}"
fi
echo ""

echo "========================================"
echo -e "${GREEN}✓ 服务器环境配置完成！${NC}"
echo "========================================"
echo ""
echo "接下来的步骤:"
echo ""
echo "1. 上传代码到服务器:"
echo "   方法A - 使用Git（如果有公网访问）:"
echo "     su - $APP_USER"
echo "     git clone https://github.com/您的仓库.git $PROJECT_DIR"
echo ""
echo "   方法B - 手动上传（私网服务器）:"
echo "     在本地打包代码: tar -czf novel_system.tar.gz ."
echo "     在Workbench终端中:"
echo "     cd $PROJECT_DIR"
echo "     rz  # 上传tar.gz文件"
echo "     tar -xzf novel_system.tar.gz"
echo "     rm novel_system.tar.gz"
echo ""
echo "2. 部署应用:"
echo "   su - $APP_USER"
echo "   cd $PROJECT_DIR"
echo "   python3.10 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install --upgrade pip"
echo "   pip install -r requirements.txt"
echo "   pip install gunicorn eventlet"
echo ""
echo "3. 配置环境变量:"
echo "   cp .env.example .env"
echo "   vim .env"
echo "   # 配置API密钥和其他必要参数"
echo ""
echo "4. 初始化数据库:"
echo "   source venv/bin/activate"
echo "   python -c \"from web.models.user_model import db; from web.web_server_refactored import app; app.app_context().push(); db.create_all()\""
echo ""
echo "5. 启动应用:"
echo "   sudo supervisorctl start novel-system"
echo "   sudo supervisorctl status novel-system"
echo ""
echo "6. 配置公网访问（重要！）:"
echo "   由于是私网地址，需要配置以下之一:"
echo "   - 阿里云负载均衡"
echo "   - NAT网关"
echo "   - 配置公网IP"
echo "   在阿里云控制台配置安全组规则，开放80和443端口"
echo ""
echo "7. 测试访问:"
echo "   sudo supervisorctl tail -f novel-system"
echo "   curl http://localhost"
echo ""