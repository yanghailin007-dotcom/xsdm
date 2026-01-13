# xsdm.com.cn 域名配置完整指南

## 概述

本指南将帮助您完成域名 `xsdm.com.cn` 到服务器的完整配置流程，包括 DNS 解析、Nginx 反向代理、HTTPS 证书配置等。

## 配置前准备

### 信息确认
- **域名**: xsdm.com.cn
- **服务器IP**: 8.163.37.124
- **应用端口**: 8080
- **操作系统**: Ubuntu 20.04/22.04 LTS

### 配置目标
- [ ] 主域名访问: http://xsdm.com.cn
- [ ] www子域名访问: http://www.xsdm.com.cn
- [ ] HTTPS加密访问: https://xsdm.com.cn
- [ ] 自动HTTP到HTTPS重定向

---

## 步骤一：DNS解析配置

### 1.1 登录阿里云DNS控制台

访问阿里云云解析DNS控制台：https://dns.console.aliyun.com/

### 1.2 添加DNS解析记录

在域名 `xsdm.com.cn` 的解析设置中，添加以下两条A记录：

| 记录类型 | 主机记录 | 记录值 | TTL | 优先级 |
|---------|---------|--------|-----|-------|
| A | @ | 8.163.37.124 | 600 | - |
| A | www | 8.163.37.124 | 600 | - |

**记录说明**：
- `@` 记录：使 `xsdm.com.cn` 解析到服务器IP
- `www` 记录：使 `www.xsdm.com.cn` 解析到服务器IP
- TTL 600秒：10分钟生效（实际可能需要10-30分钟）

### 1.3 验证DNS解析

**在本地Windows电脑上执行**：
```cmd
nslookup xsdm.com.cn
```

**预期结果**：
```
服务器:  UnKnown
Address:  xxx.xxx.xxx.xxx

名称:    xsdm.com.cn
Address:  8.163.37.124
```

**也可以使用ping测试**：
```cmd
ping xsdm.com.cn
```

**常见问题**：
- 如果DNS未生效，等待10-30分钟后重试
- 检查阿里云安全组是否开放80和443端口

---

## 步骤二：服务器端Nginx配置

### 2.1 连接到服务器

```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
```

### 2.2 安装Nginx

```bash
# 更新包列表
apt update

# 安装Nginx
apt install -y nginx

# 启动Nginx服务
systemctl start nginx
systemctl enable nginx

# 验证Nginx状态
systemctl status nginx
```

### 2.3 创建Nginx配置文件

```bash
# 创建站点配置文件
nano /etc/nginx/sites-available/xsdm-novel-system
```

**复制以下配置内容**（已针对 xsdm.com.cn 定制）：

```nginx
# HTTP服务器配置
server {
    listen 80;
    server_name xsdm.com.cn www.xsdm.com.cn;

    # 访问日志
    access_log /var/log/nginx/xsdm-access.log;
    error_log /var/log/nginx/xsdm-error.log;

    # 客户端最大请求体大小（用于图片上传）
    client_max_body_size 100M;

    # 静态文件直接由Nginx提供服务
    location /static {
        alias /home/novelapp/novel-system/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 生成图片缓存
    location /generated_images {
        alias /home/novelapp/novel-system/generated_images;
        expires 7d;
        add_header Cache-Control "public";
    }

    # WebSocket支持（视频生成进度）
    location /ws {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # 应用反向代理
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置（视频生成需要较长时间）
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # 缓冲设置
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

保存文件：按 `Ctrl+O`，然后 `Enter`，最后 `Ctrl+X` 退出。

### 2.4 启用站点配置

```bash
# 创建符号链接
ln -s /etc/nginx/sites-available/xsdm-novel-system /etc/nginx/sites-enabled/

# 删除默认站点（可选）
rm /etc/nginx/sites-enabled/default

# 测试Nginx配置
nginx -t

# 重新加载Nginx
systemctl reload nginx
```

**预期输出**：
```
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 2.5 配置防火墙

```bash
# 允许HTTP和HTTPS流量
ufw allow 80/tcp
ufw allow 443/tcp

# 查看防火墙状态
ufw status
```

### 2.6 配置阿里云安全组

在阿里云ECS控制台添加安全组规则：

| 端口 | 协议 | 授权对象 | 描述 |
|-----|------|---------|------|
| 80 | TCP | 0.0.0.0/0 | HTTP访问 |
| 443 | TCP | 0.0.0.0/0 | HTTPS访问 |

### 2.7 验证HTTP访问

在浏览器中访问：
- http://xsdm.com.cn
- http://www.xsdm.com.cn

应该能看到您的系统登录页面。

---

## 步骤三：配置HTTPS/SSL证书（推荐）

### 3.1 安装Certbot

```bash
# 安装Certbot和Nginx插件
apt install -y certbot python3-certbot-nginx
```

### 3.2 申请SSL证书

```bash
# 自动申请并配置SSL证书
certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn
```

**按提示操作**：
1. 输入邮箱地址（用于证书到期提醒）
2. 输入 `A` 同意服务条款
3. 输入 `N` 或 `Y` 选择是否共享邮箱（建议选N）
4. 选择是否重定向HTTP到HTTPS（**建议选择 2: Redirect**）

**Certbot会自动**：
- 申请SSL证书
- 修改Nginx配置，添加SSL相关配置
- 配置HTTP到HTTPS的重定向

### 3.3 验证SSL证书

```bash
# 检查证书状态
certbot certificates

# 测试自动续期
certbot renew --dry-run
```

**预期输出**：
```
Saving debug log to /var/log/letsencrypt/letsencrypt.log

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Processing xsdm.com.cn
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Certificate not yet due for renewal

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
The following certs are not due for renewal yet:
  /etc/letsencrypt/live/xsdm.com.cn/fullchain.pem (success)
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
```

### 3.4 自动续期配置

Certbot会自动添加cron任务或systemd定时器，证书会自动续期。

验证定时器：
```bash
systemctl status certbot.timer
systemctl list-timers | grep certbot
```

---

## 步骤四：验证配置

### 4.1 DNS解析验证

```cmd
# Windows本地执行
nslookup xsdm.com.cn
nslookup www.xsdm.com.cn
```

### 4.2 HTTP/HTTPS访问验证

**测试HTTP访问**（如果未强制HTTPS）：
- 访问 http://xsdm.com.cn
- 访问 http://www.xsdm.com.cn

**测试HTTPS访问**：
- 访问 https://xsdm.com.cn
- 访问 https://www.xsdm.com.cn

**验证要点**：
- ✅ 浏览器地址栏显示锁图标
- ✅ 证书有效，无安全警告
- ✅ HTTP自动重定向到HTTPS
- ✅ 系统功能正常

### 4.3 SSL证书验证

访问 SSL Labs 测试：https://www.ssllabs.com/ssltest/

输入 `xsdm.com.cn` 进行测试，目标评级 A 或 A+。

### 4.4 Nginx日志检查

```bash
# 查看访问日志
tail -f /var/log/nginx/xsdm-access.log

# 查看错误日志
tail -f /var/log/nginx/xsdm-error.log
```

---

## 步骤五：（可选）应用配置更新

如果应用需要知道域名和协议：

### 5.1 更新环境变量

```bash
# SSH连接到服务器
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124

# 编辑环境变量
cd /home/novelapp/novel-system
nano .env
```

添加或修改：
```bash
# 域名配置
APP_DOMAIN=xsdm.com.cn
APP_SCHEME=https
APP_URL=https://xsdm.com.cn
```

### 5.2 重启应用服务

```bash
# 如果使用Supervisor
supervisorctl restart novel-system

# 如果使用systemd
systemctl restart novel-system
```

---

## 配置完成后的Nginx配置（参考）

Certbot配置SSL后，最终的Nginx配置会类似这样：

```nginx
# HTTP重定向到HTTPS
server {
    listen 80;
    server_name xsdm.com.cn www.xsdm.com.cn;
    return 301 https://$server_name$request_uri;
}

# HTTPS主服务器
server {
    listen 443 ssl;
    server_name xsdm.com.cn www.xsdm.com.cn;

    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/xsdm.com.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xsdm.com.cn/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # 日志配置
    access_log /var/log/nginx/xsdm-access.log;
    error_log /var/log/nginx/xsdm-error.log;

    # 客户端配置
    client_max_body_size 100M;

    # 静态文件
    location /static {
        alias /home/novelapp/novel-system/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 生成图片
    location /generated_images {
        alias /home/novelapp/novel-system/generated_images;
        expires 7d;
        add_header Cache-Control "public";
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # 应用代理
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

---

## 常见问题排查

### Q1: DNS解析已配置，但无法访问

**检查步骤**：
```bash
# 1. 检查DNS解析
nslookup xsdm.com.cn

# 2. 检查服务器端口
telnet 8.163.37.124 80
telnet 8.163.37.124 443

# 3. 检查Nginx状态
systemctl status nginx

# 4. 检查防火墙
ufw status

# 5. 检查阿里云安全组（登录阿里云控制台）
```

**常见原因**：
- DNS还未生效（等待10-30分钟）
- 阿里云安全组未开放80/443端口
- 服务器防火墙未开放端口
- Nginx未正常启动

### Q2: 访问显示502 Bad Gateway

**检查步骤**：
```bash
# 1. 检查Flask应用是否运行
supervisorctl status novel-system

# 2. 检查端口5000是否监听
netstat -tlnp | grep 5000

# 3. 查看应用日志
supervisorctl tail -f novel-system

# 4. 手动测试应用
curl http://127.0.0.1:5000
```

**解决方法**：
```bash
# 重启应用
supervisorctl restart novel-system

# 或手动启动测试
cd /home/novelapp/novel-system
source venv/bin/activate
python web/wsgi.py
```

### Q3: SSL证书申请失败

**常见原因**：
1. DNS还未完全生效
2. 80端口被占用或未开放
3. 域名指向了错误的IP

**解决方法**：
```bash
# 1. 检查80端口
netstat -tlnp | grep :80

# 2. 确保Nginx监听80
nginx -t
systemctl status nginx

# 3. 验证DNS解析
dig xsdm.com.cn +short

# 4. 检查防火墙
ufw status
```

### Q4: 证书申请成功，但浏览器显示不安全

**检查步骤**：
```bash
# 1. 检查证书有效期
certbot certificates

# 2. 检查Nginx配置
nginx -t

# 3. 查看错误日志
tail -f /var/log/nginx/xsdm-error.log
```

**可能原因**：
- 混合内容（页面中有HTTP资源）
- 证书链不完整
- 时间不同步

---

## 监控与维护

### 日常检查

```bash
# 1. 检查Nginx状态
systemctl status nginx

# 2. 检查SSL证书
certbot certificates

# 3. 查看访问日志（实时）
tail -f /var/log/nginx/xsdm-access.log

# 4. 查看错误日志
tail -f /var/log/nginx/xsdm-error.log

# 5. 检查连接数
ss -ant | grep :443 | wc -l
```

### 证书续期

证书每90天自动续期，验证自动续期：
```bash
certbot renew --dry-run
```

手动续期（如需要）：
```bash
certbot renew
systemctl reload nginx
```

### 性能优化

**启用Gzip压缩**（在Nginx配置的http块或server块中添加）：

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript 
           application/json application/javascript application/xml+rss;
```

**配置缓存**：

```nginx
# 在http块添加
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=app_cache:10m 
                 max_size=1g inactive=60m use_temp_path=off;

# 在location块使用
location /static {
    proxy_cache app_cache;
    proxy_cache_valid 200 30d;
    # ... 其他配置
}
```

---

## 快速配置脚本

创建自动化脚本 `setup_xsdm_domain.sh`：

```bash
#!/bin/bash
set -e

DOMAIN="xsdm.com.cn"
IP="8.163.37.124"

echo "=== xsdm.com.cn 域名配置脚本 ==="
echo ""

# 检查是否为root
if [ "$EUID" -ne 0 ]; then 
    echo "请使用root权限运行此脚本"
    exit 1
fi

echo "1. 安装Nginx..."
apt update
apt install -y nginx certbot python3-certbot-nginx

echo "2. 创建Nginx配置..."
cat > /etc/nginx/sites-available/xsdm-novel-system << 'EOF'
server {
    listen 80;
    server_name xsdm.com.cn www.xsdm.com.cn;

    access_log /var/log/nginx/xsdm-access.log;
    error_log /var/log/nginx/xsdm-error.log;
    client_max_body_size 100M;

    location /static {
        alias /home/novelapp/novel-system/web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /generated_images {
        alias /home/novelapp/novel-system/generated_images;
        expires 7d;
        add_header Cache-Control "public";
    }

    location /ws {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
EOF

echo "3. 启用Nginx配置..."
ln -sf /etc/nginx/sites-available/xsdm-novel-system /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

echo "4. 测试Nginx配置..."
nginx -t

echo "5. 重启Nginx..."
systemctl restart nginx
systemctl enable nginx

echo "6. 配置防火墙..."
ufw allow 80/tcp
ufw allow 443/tcp

echo ""
echo "=== 基础配置完成！==="
echo ""
echo "下一步操作："
echo "1. 确认DNS解析已生效（访问阿里云DNS控制台）"
echo "2. 等待DNS生效（10-30分钟）"
echo "3. 运行SSL证书申请命令："
echo "   certbot --nginx -d xsdm.com.cn -d www.xsdm.com.cn"
echo ""
echo "验证访问："
echo "http://xsdm.com.cn"
echo "http://www.xsdm.com.cn"
```

**使用方法**：
```bash
# 1. 上传脚本到服务器
scp -i "d:\work6.05\xsdm.pem" setup_xsdm_domain.sh root@8.163.37.124:/root/

# 2. 连接服务器并执行
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
chmod +x /root/setup_xsdm_domain.sh
/root/setup_xsdm_domain.sh
```

---

## 配置检查清单

配置完成后，请逐项检查：

### DNS配置
- [ ] 在阿里云DNS控制台添加 @ A记录 → 8.163.37.124
- [ ] 在阿里云DNS控制台添加 www A记录 → 8.163.37.124
- [ ] DNS解析已生效（nslookup验证）

### 服务器配置
- [ ] Nginx已安装并启动
- [ ] Nginx配置文件已创建
- [ ] 防火墙已开放80和443端口
- [ ] 阿里云安全组已开放80和443端口

### SSL证书
- [ ] Certbot已安装
- [ ] SSL证书已申请成功
- [ ] HTTP自动重定向到HTTPS
- [ ] 证书自动续期已配置

### 应用配置
- [ ] 后端应用正常运行
- [ ] 5000端口正常监听
- [ ] WebSocket连接正常
- [ ] 静态文件可访问

### 验证测试
- [ ] http://xsdm.com.cn 可访问
- [ ] http://www.xsdm.com.cn 可访问
- [ ] https://xsdm.com.cn 可访问
- [ ] https://www.xsdm.com.cn 可访问
- [ ] 浏览器显示安全锁图标
- [ ] 系统功能正常

---

## 联系支持

如遇到问题，请参考：
- 阿里云DNS文档：https://help.aliyun.com/product/29697.html
- Nginx文档：https://nginx.org/en/docs/
- Let's Encrypt文档：https://letsencrypt.org/docs/

配置完成后，您的系统可通过以下地址访问：
- **主域名**: https://xsdm.com.cn
- **www子域名**: https://www.xsdm.com.cn