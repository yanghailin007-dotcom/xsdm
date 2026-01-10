# 域名配置指南

## 概述

本指南将帮助您配置域名访问小说生成系统。配置域名后,您可以通过 `http://yourdomain.com` 访问系统,而不是 `http://8.163.37.124:5000`。

## 配置步骤

### 步骤1: DNS解析配置

#### 1.1 登录域名管理控制台

根据您的域名注册商登录相应的控制台:
- 阿里云: https://dc.console.aliyun.com/next/index
- 腾讯云: https://console.cloud.tencent.com/cns
- Cloudflare: https://dash.cloudflare.com/
- 其他: 登录您的域名注册商控制台

#### 1.2 添加A记录

在DNS解析管理中添加以下记录:

| 记录类型 | 主机记录 | 记录值 | TTL | 说明 |
|---------|---------|--------|-----|------|
| A | @ | 8.163.37.124 | 600 | 主域名访问 |
| A | www | 8.163.37.124 | 600 | www子域名 |

**示例:**
- 如果您的域名是 `example.com`
- 访问 `http://example.com` 会解析到 `8.163.37.124`
- 访问 `http://www.example.com` 也会解析到 `8.163.37.124`

#### 1.3 等待DNS生效

DNS解析通常需要10分钟到24小时生效,但通常在10-30分钟内生效。

**验证DNS解析:**
```bash
# Windows
nslookup yourdomain.com

# Linux/Mac
dig yourdomain.com
ping yourdomain.com
```

### 步骤2: (可选) 配置Nginx反向代理

为了更好的性能和安全性,建议配置Nginx作为反向代理。

#### 2.1 安装Nginx

```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124

# 更新包列表
apt update

# 安装Nginx
apt install -y nginx

# 启动Nginx
systemctl start nginx
systemctl enable nginx
```

#### 2.2 创建Nginx配置文件

```bash
# 创建站点配置
nano /etc/nginx/sites-available/novel-system
```

**配置内容:**
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # 日志配置
    access_log /var/log/nginx/novel-system-access.log;
    error_log /var/log/nginx/novel-system-error.log;

    # 反向代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # 大文件上传支持
        client_max_body_size 100M;
    }

    # 静态文件直接由Nginx提供
    location /static {
        alias /home/novelapp/novel-system/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 图片缓存
    location /generated_images {
        alias /home/novelapp/novel-system/generated_images;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

**替换 `yourdomain.com` 为您的实际域名**

#### 2.3 启用站点配置

```bash
# 创建软链接
ln -s /etc/nginx/sites-available/novel-system /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重新加载Nginx
systemctl reload nginx
```

#### 2.4 配置防火墙

```bash
# 允许HTTP流量
ufw allow 'Nginx Full'
# 或
ufw allow 80/tcp
```

#### 2.5 更新阿里云安全组

在阿里云安全组中添加:
- 端口: 80
- 协议: TCP
- 授权对象: 0.0.0.0/0

### 步骤3: (推荐) 配置HTTPS/SSL

使用Let's Encrypt免费SSL证书。

#### 3.1 安装Certbot

```bash
# 安装Certbot
apt install -y certbot python3-certbot-nginx

# 获取并自动配置SSL证书
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

按照提示:
1. 输入邮箱地址
2. 同意服务条款
3. 选择是否重定向HTTP到HTTPS (建议选择 Yes, redirect)

#### 3.2 自动续期

Certbot会自动配置续期任务。验证:
```bash
certbot renew --dry-run
```

### 步骤4: 更新应用配置

如果使用HTTPS,可能需要更新应用配置:

```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124

# 编辑环境变量
cd /home/novelapp/novel-system
nano .env
```

添加或修改:
```
# 应用域名配置
APP_DOMAIN=yourdomain.com
APP_SCHEME=https
```

重启服务:
```bash
supervisorctl restart novel-system
```

## 配置验证

### 1. DNS解析验证

```bash
# 检查域名解析
nslookup yourdomain.com
# 或
dig yourdomain.com
```

应该返回:
```
Name:    yourdomain.com
Address: 8.163.37.124
```

### 2. HTTP访问验证

浏览器访问: `http://yourdomain.com`

应该能看到系统登录页面。

### 3. HTTPS验证(如果配置了SSL)

浏览器访问: `https://yourdomain.com`

应该:
- 自动重定向到HTTPS
- 浏览器地址栏显示锁图标
- 可以正常访问系统

### 4. Nginx日志检查

```bash
# 查看访问日志
tail -f /var/log/nginx/novel-system-access.log

# 查看错误日志
tail -f /var/log/nginx/novel-system-error.log
```

## 常见问题

### Q1: DNS解析已经配置,但无法访问

**A:** 检查以下几点:
1. DNS记录是否正确添加
2. 等待DNS生效(最多24小时)
3. 阿里云安全组是否开放80端口
4. 服务器防火墙是否允许80端口
5. Nginx是否正常运行: `systemctl status nginx`

### Q2: 访问域名显示502错误

**A:** 检查后端服务:
```bash
# 检查Flask服务状态
supervisorctl status novel-system

# 检查端口监听
netstat -tlnp | grep 5000
```

### Q3: SSL证书申请失败

**A:** 常见原因:
1. DNS还未生效
2. 80端口被占用或未开放
3. 域名指向了错误的IP

**解决方法:**
```bash
# 检查80端口
netstat -tlnp | grep :80

# 停止占用80端口的服务
# 或确保Nginx已启动
systemctl start nginx
```

### Q4: 访问速度慢

**A:** 优化建议:
1. 启用Nginx gzip压缩
2. 配置静态文件缓存
3. 使用CDN加速
4. 优化应用性能

## Nginx性能优化

在Nginx配置中添加:

```nginx
# gzip压缩
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript 
           application/json application/javascript application/xml+rss 
           application/rss+xml font/truetype font/opentype 
           application/vnd.ms-fontobject image/svg+xml;

# 保持连接
keepalive_timeout 65;
keepalive_requests 100;

# 缓冲区优化
client_body_buffer_size 128k;
client_max_body_size 100m;
client_header_buffer_size 1k;
large_client_header_buffers 4 16k;
```

## 监控和维护

### 日志轮转

```bash
# 配置logrotate
nano /etc/logrotate.d/nginx
```

```
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

### 性能监控

```bash
# 查看Nginx连接状态
netstat -an | grep :80 | awk '{print $6}' | sort | uniq -c

# 查看当前连接数
ss -ant | grep :80 | wc -l
```

## 完整配置示例

### Nginx完整配置 (`/etc/nginx/sites-available/novel-system`)

```nginx
# HTTP服务器 - 重定向到HTTPS
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS服务器
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 日志配置
    access_log /var/log/nginx/novel-system-access.log;
    error_log /var/log/nginx/novel-system-error.log;

    # gzip压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;

    # 反向代理配置
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        client_max_body_size 100M;
    }

    # 静态文件
    location /static {
        alias /home/novelapp/novel-system/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 图片缓存
    location /generated_images {
        alias /home/novelapp/novel-system/generated_images;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

## 快速配置脚本

创建自动化配置脚本:

```bash
#!/bin/bash
# domain-setup.sh

DOMAIN=$1

if [ -z "$DOMAIN" ]; then
    echo "用法: ./domain-setup.sh yourdomain.com"
    exit 1
fi

echo "配置域名: $DOMAIN"

# 1. 安装Nginx
apt update && apt install -y nginx certbot python3-certbot-nginx

# 2. 创建Nginx配置
cat > /etc/nginx/sites-available/novel-system << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 600s;
        proxy_read_timeout 600s;
        client_max_body_size 100M;
    }
}
EOF

# 3. 启用配置
ln -sf /etc/nginx/sites-available/novel-system /etc/nginx/sites-enabled/

# 4. 测试并重载
nginx -t && systemctl reload nginx

# 5. 获取SSL证书
certbot --nginx -d $DOMAIN -d www.$DOMAIN

echo "配置完成!访问: https://$DOMAIN"
```

使用方法:
```bash
chmod +x domain-setup.sh
./domain-setup.sh yourdomain.com
```

## 联系支持

如需帮助,请查阅:
- Nginx文档: https://nginx.org/en/docs/
- Let's Encrypt文档: https://letsencrypt.org/docs/
- 阿里云DNS文档: https://help.aliyun.com/product/29697.html