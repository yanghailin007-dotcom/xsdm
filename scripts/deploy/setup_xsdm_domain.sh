#!/bin/bash
# xsdm.com.cn 域名自动配置脚本
# 使用方法: sudo bash setup_xsdm_domain.sh

set -e

# 配置参数
DOMAIN="xsdm.com.cn"
SERVER_IP="8.163.37.124"
APP_PORT="8080"
APP_PATH="/home/novelapp/novel-system"

echo "========================================"
echo "  xsdm.com.cn 域名配置脚本"
echo "========================================"
echo ""
echo "域名: $DOMAIN"
echo "服务器IP: $SERVER_IP"
echo "应用端口: $APP_PORT"
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 错误: 请使用root权限运行此脚本"
    echo "使用方法: sudo bash setup_xsdm_domain.sh"
    exit 1
fi

# 步骤1: 安装Nginx
echo "📦 步骤1: 安装Nginx..."
apt update
apt install -y nginx

# 步骤2: 创建Nginx配置文件
echo "📝 步骤2: 创建Nginx配置文件..."
cat > /etc/nginx/sites-available/xsdm-novel-system << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # 日志配置
    access_log /var/log/nginx/xsdm-access.log;
    error_log /var/log/nginx/xsdm-error.log;

    # 客户端配置
    client_max_body_size 100M;

    # 静态文件
    location /static {
        alias $APP_PATH/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 生成图片
    location /generated_images {
        alias $APP_PATH/generated_images;
        expires 7d;
        add_header Cache-Control "public";
    }

    # WebSocket支持
    location /ws {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    # 应用代理
    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # 超时配置
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # 缓冲配置
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
EOF

echo "✅ Nginx配置文件已创建: /etc/nginx/sites-available/xsdm-novel-system"

# 步骤3: 启用站点配置
echo "🔗 步骤3: 启用站点配置..."
ln -sf /etc/nginx/sites-available/xsdm-novel-system /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 步骤4: 测试Nginx配置
echo "🧪 步骤4: 测试Nginx配置..."
if nginx -t; then
    echo "✅ Nginx配置测试通过"
else
    echo "❌ Nginx配置测试失败"
    exit 1
fi

# 步骤5: 重启Nginx
echo "🔄 步骤5: 重启Nginx服务..."
systemctl restart nginx
systemctl enable nginx

if systemctl status nginx > /dev/null 2>&1; then
    echo "✅ Nginx服务已启动并设置为开机自启"
else
    echo "❌ Nginx服务启动失败"
    exit 1
fi

# 步骤6: 配置防火墙
echo "🔥 步骤6: 配置防火墙..."
ufw allow 80/tcp comment "HTTP" > /dev/null 2>&1 || true
ufw allow 443/tcp comment "HTTPS" > /dev/null 2>&1 || true
echo "✅ 防火墙规则已添加"

# 步骤7: 安装Certbot（用于SSL证书）
echo "🔐 步骤7: 安装Certbot..."
apt install -y certbot python3-certbot-nginx
echo "✅ Certbot已安装"

# 完成
echo ""
echo "========================================"
echo "  ✅ 基础配置完成！"
echo "========================================"
echo ""
echo "📋 下一步操作："
echo ""
echo "1️⃣  配置DNS解析（在阿里云DNS控制台）："
echo "   - 登录 https://dns.console.aliyun.com/"
echo "   - 添加 A记录: @ → $SERVER_IP"
echo "   - 添加 A记录: www → $SERVER_IP"
echo ""
echo "2️⃣  等待DNS生效（通常10-30分钟）"
echo "   - 验证命令: nslookup $DOMAIN"
echo "   - 验证命令: ping $DOMAIN"
echo ""
echo "3️⃣  申请SSL证书（DNS生效后）："
echo "   运行以下命令:"
echo "   sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo ""
echo "4️⃣  验证访问："
echo "   - http://$DOMAIN"
echo "   - http://www.$DOMAIN"
echo ""
echo "5️⃣  配置HTTPS后验证："
echo "   - https://$DOMAIN"
echo "   - https://www.$DOMAIN"
echo ""
echo "📖 详细配置指南: docs/guides/XSDM_DOMAIN_SETUP_GUIDE.md"
echo ""
echo "🔍 常用命令："
echo "   - 查看Nginx状态: systemctl status nginx"
echo "   - 查看Nginx日志: tail -f /var/log/nginx/xsdm-error.log"
echo "   - 重启Nginx: systemctl restart nginx"
echo "   - 测试配置: nginx -t"
echo ""