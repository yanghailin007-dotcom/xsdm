#!/bin/bash

# 阿里云一键部署脚本
# 使用方法: sudo bash aliyun_deploy.sh

set -e

echo "========================================"
echo "   小说生成系统 - 阿里云一键部署脚本"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用sudo运行此脚本${NC}"
    exit 1
fi

# 获取服务器信息
echo -e "${YELLOW}步骤 1/10: 获取服务器信息${NC}"
read -p "请输入您的域名 (例如: example.com): " DOMAIN
read -p "请输入服务器公网IP: " SERVER_IP
read -p "请输入应用用户名 (默认: novelapp): " APP_USER
APP_USER=${APP_USER:-novelapp}

echo -e "${GREEN}域名: $DOMAIN${NC}"
echo -e "${GREEN}服务器IP: $SERVER_IP${NC}"
echo -e "${GREEN}应用用户: $APP_USER${NC}"
echo ""

# 更新系统
echo -e "${YELLOW}步骤 2/10: 更新系统${NC}"
apt update && apt upgrade -y
echo -e "${GREEN}✓ 系统更新完成${NC}"
echo ""

# 安装基础工具
echo -e "${YELLOW}步骤 3/10: 安装基础工具${NC}"
apt install -y wget curl git vim build-essential software-properties-common
echo -e "${GREEN}✓ 基础工具安装完成${NC}"
echo ""

# 安装Python
echo -e "${YELLOW}步骤 4/10: 安装Python 3.10${NC}"
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
echo -e "${GREEN}✓ Python安装完成${NC}"
python3.10 --version
echo ""

# 创建应用用户
echo -e "${YELLOW}步骤 5/10: 创建应用用户${NC}"
if id "$APP_USER" &>/dev/null; then
    echo -e "${YELLOW}用户 $APP_USER 已存在${NC}"
else
    useradd -m -s /bin/bash $APP_USER
    echo -e "${GREEN}✓ 用户 $APP_USER 创建完成${NC}"
fi
echo ""

# 安装Nginx
echo -e "${YELLOW}步骤 6/10: 安装Nginx${NC}"
apt install -y nginx
echo -e "${GREEN}✓ Nginx安装完成${NC}"
echo ""

# 安装Supervisor
echo -e "${YELLOW}步骤 7/10: 安装Supervisor${NC}"
apt install -y supervisor
echo -e "${GREEN}✓ Supervisor安装完成${NC}"
echo ""

# 创建项目目录
echo -e "${YELLOW}步骤 8/10: 创建项目目录${NC}"
PROJECT_DIR="/home/$APP_USER/novel-system"
mkdir -p $PROJECT_DIR
mkdir -p $PROJECT_DIR/logs
mkdir -p $PROJECT_DIR/data
mkdir -p $PROJECT_DIR/generated_images
mkdir -p $PROJECT_DIR/temp_fanqie_upload
chown -R $APP_USER:$APP_USER $PROJECT_DIR
echo -e "${GREEN}✓ 项目目录创建完成${NC}"
echo ""

# 配置Nginx
echo -e "${YELLOW}步骤 9/10: 配置Nginx${NC}"
cat > /etc/nginx/sites-available/novel-system <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    access_log /var/log/nginx/novel-system-access.log;
    error_log /var/log/nginx/novel-system-error.log;

    client_max_body_size 100M;

    location /static {
        alias $PROJECT_DIR/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /generated_images {
        alias $PROJECT_DIR/generated_images;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
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

# 安装SSL证书
echo -e "${YELLOW}是否安装SSL证书?${NC}"
read -p "输入 y 安装，其他键跳过: " INSTALL_SSL
if [ "$INSTALL_SSL" = "y" ] || [ "$INSTALL_SSL" = "Y" ]; then
    apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}请确保域名DNS已解析到 $SERVER_IP${NC}"
    echo -e "${GREEN}然后运行: certbot --nginx -d $DOMAIN -d www.$DOMAIN${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}✓ 基础环境配置完成！${NC}"
echo "========================================"
echo ""
echo "接下来的步骤:"
echo "1. 上传代码到服务器:"
echo "   scp -r your-project/* $APP_USER@$SERVER_IP:$PROJECT_DIR/"
echo ""
echo "2. SSH登录服务器:"
echo "   ssh $APP_USER@$SERVER_IP"
echo ""
echo "3. 创建虚拟环境并安装依赖:"
echo "   cd $PROJECT_DIR"
echo "   python3.10 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "   pip install gunicorn"
echo ""
echo "4. 配置环境变量:"
echo "   cp .env.example .env"
echo "   vim .env"
echo ""
echo "5. 配置Supervisor并启动应用:"
echo "   sudo bash /home/$APP_USER/novel-system/scripts/deploy/setup_supervisor.sh"
echo ""
echo "6. 访问您的网站:"
echo "   http://$DOMAIN"
echo ""