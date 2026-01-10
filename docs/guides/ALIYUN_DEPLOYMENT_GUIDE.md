# 阿里云服务器部署指南

## 目录
1. [准备工作](#准备工作)
2. [服务器环境配置](#服务器环境配置)
3. [代码上传](#代码上传)
4. [环境配置](#环境配置)
5. [数据库配置](#数据库配置)
6. [Web服务器配置](#web服务器配置)
7. [域名配置](#域名配置)
8. [SSL证书配置](#ssl证书配置)
9. [进程管理](#进程管理)
10. [监控与日志](#监控与日志)

## 准备工作

### 1. 服务器信息收集
- 云服务器公网IP：`您的服务器IP`
- 域名：`您的域名`
- 操作系统：建议使用 Ubuntu 20.04 或 22.04 LTS

### 2. 本地准备
```bash
# 在本地项目目录，创建部署包
cd d:/work6.05
# 排除不必要的文件
tar -czf novel_system.tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='logs/*' \
  --exclude='generated_images/*' \
  --exclude='temp_fanqie_upload/*' \
  --exclude='chapter_failures/*' \
  --exclude='.env' \
  --exclude='test_*.py' \
  --exclude='*.db' \
  .
```

## 服务器环境配置

### 1. 连接服务器
```bash
# 使用SSH连接服务器
ssh root@您的服务器IP

# 或使用密钥（如果配置了）
ssh -i 您的密钥.pem root@您的服务器IP
```

### 2. 更新系统
```bash
apt update && apt upgrade -y
```

### 3. 安装基础工具
```bash
# 安装必要工具
apt install -y wget curl git vim build-essential

# 安装Python 3.10+
apt install -y software-properties-common
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
```

### 4. 创建应用用户
```bash
# 创建专用用户（安全最佳实践）
useradd -m -s /bin/bash novelapp
passwd novelapp  # 设置密码

# 将用户添加到sudo组
usermod -aG sudo novelapp
```

## 代码上传

### 方法1: 使用SCP上传
```bash
# 在本地执行
scp novel_system.tar.gz novelapp@您的服务器IP:/home/novelapp/

# 或使用密钥
scp -i 您的密钥.pem novel_system.tar.gz novelapp@您的服务器IP:/home/novelapp/
```

### 方法2: 使用Git（推荐）
```bash
# 在服务器上
cd /home/novelapp
git clone https://github.com/您的用户名/您的仓库.git novel-system
cd novel-system
```

### 解压代码（如果使用tar.gz）
```bash
# 在服务器上
cd /home/novelapp
tar -xzf novel_system.tar.gz -C novel-system
rm novel_system.tar.gz
```

## 环境配置

### 1. 创建项目目录结构
```bash
cd /home/novelapp/novel-system

# 创建必要的目录
mkdir -p logs
mkdir -p generated_images
mkdir -p temp_fanqie_upload
mkdir -p data

# 设置权限
chmod -R 755 /home/novelapp/novel-system
chown -R novelapp:novelapp /home/novelapp/novel-system
```

### 2. 创建Python虚拟环境
```bash
cd /home/novelapp/novel-system
python3.10 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 安装生产环境依赖
pip install gunicorn supervisor
```

### 4. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

`.env` 配置示例：
```bash
# Flask配置
FLASK_APP=web.web_server_refactored
FLASK_ENV=production
SECRET_KEY=您的随机密钥（使用 openssl rand -hex 32 生成）

# 数据库配置
DATABASE_URL=sqlite:///data/users.db

# API配置
DOUBAO_API_KEY=您的豆包API密钥
NANOBANANA_API_KEY=您的NanoBanana API密钥

# 文件路径配置
PROJECT_ROOT=/home/novelapp/novel-system
DATA_DIR=/home/novelapp/novel-system/data
LOGS_DIR=/home/novelapp/novel-system/logs
GENERATED_IMAGES_DIR=/home/novelapp/novel-system/generated_images

# 服务器配置
HOST=0.0.0.0
PORT=5000
DEBUG=False
```

## 数据库配置

### 初始化数据库
```bash
cd /home/novelapp/novel-system
source venv/bin/activate

# 创建数据库目录
mkdir -p data

# 初始化数据库（如果项目有初始化脚本）
python -c "from web.models.user_model import db; from web.web_server_refactored import app; app.app_context().push(); db.create_all()"
```

## Web服务器配置

### 1. 安装Nginx
```bash
apt install -y nginx
```

### 2. 配置Nginx
```bash
# 创建站点配置
vim /etc/nginx/sites-available/novel-system
```

Nginx配置文件内容：
```nginx
# /etc/nginx/sites-available/novel-system
server {
    listen 80;
    server_name 您的域名 www.您的域名;

    # 日志配置
    access_log /var/log/nginx/novel-system-access.log;
    error_log /var/log/nginx/novel-system-error.log;

    # 客户端最大请求体大小
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
        expires 30d;
    }

    # WebSocket支持（如果需要）
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
        proxy_redirect off;
        
        # 超时配置
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }
}
```

### 3. 启用站点
```bash
# 创建符号链接
ln -s /etc/nginx/sites-available/novel-system /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重启Nginx
systemctl restart nginx
systemctl enable nginx
```

## 域名配置

### 1. DNS解析配置
在阿里云域名控制台添加解析：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| A | @ | 您的服务器IP | 600 |
| A | www | 您的服务器IP | 600 |

### 2. 验证DNS解析
```bash
# 在本地测试
ping 您的域名
nslookup 您的域名
```

## SSL证书配置

### 使用Certbot自动配置Let's Encrypt证书

#### 1. 安装Certbot
```bash
apt install -y certbot python3-certbot-nginx
```

#### 2. 申请证书
```bash
# 自动配置Nginx
certbot --nginx -d 您的域名 -d www.您的域名

# 按提示输入邮箱并同意服务条款
```

#### 3. 自动续期
```bash
# 测试续期
certbot renew --dry-run

# Certbot会自动添加cron任务，证书会自动续期
```

### 证书配置完成后的Nginx配置
Certbot会自动修改配置，添加SSL相关配置：
```nginx
server {
    listen 443 ssl;
    server_name 您的域名 www.您的域名;

    ssl_certificate /etc/letsencrypt/live/您的域名/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/您的域名/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # ... 其他配置保持不变
}

# HTTP重定向到HTTPS
server {
    listen 80;
    server_name 您的域名 www.您的域名;
    return 301 https://$server_name$request_uri;
}
```

## 进程管理

### 使用Supervisor管理Gunicorn进程

#### 1. 安装Supervisor
```bash
apt install -y supervisor
```

#### 2. 创建Supervisor配置
```bash
vim /etc/supervisor/conf.d/novel-system.conf
```

配置内容：
```ini
[program:novel-system]
command=/home/novelapp/novel-system/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 600 --access-logfile /home/novelapp/novel-system/logs/gunicorn-access.log --error-logfile /home/novelapp/novel-system/logs/gunicorn-error.log --log-level info web.web_server_refactored:app
directory=/home/novelapp/novel-system
user=novelapp
autostart=true
autorestart=true
startretries=3
stderr_logfile=/home/novelapp/novel-system/logs/supervisor-stderr.log
stdout_logfile=/home/novelapp/novel-system/logs/supervisor-stdout.log
environment=FLASK_ENV="production"
```

#### 3. 启动服务
```bash
# 重新加载Supervisor配置
supervisorctl reread
supervisorctl update

# 启动应用
supervisorctl start novel-system

# 查看状态
supervisorctl status

# 查看日志
supervisorctl tail -f novel-system
```

### 使用Systemd管理（备选方案）

```bash
# 创建systemd服务文件
vim /etc/systemd/system/novel-system.service
```

配置内容：
```ini
[Unit]
Description=Novel Generation System
After=network.target

[Service]
Type=notify
User=novelapp
Group=novelapp
WorkingDirectory=/home/novelapp/novel-system
Environment="PATH=/home/novelapp/novel-system/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=/home/novelapp/novel-system/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 600 web.web_server_refactored:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
systemctl daemon-reload
systemctl start novel-system
systemctl enable novel-system
systemctl status novel-system
```

## 监控与日志

### 1. 应用日志配置
```bash
# 在项目中配置日志
cd /home/novelapp/novel-system

# 创建日志目录
mkdir -p logs
chmod 755 logs
```

### 2. 日志轮转配置
```bash
vim /etc/logrotate.d/novel-system
```

配置内容：
```
/home/novelapp/novel-system/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 novelapp novelapp
    sharedscripts
    postrotate
        supervisorctl restart novel-system
    endscript
}
```

### 3. 监控工具

#### 安装htop和iotop
```bash
apt install -y htop iotop
```

#### 查看资源使用
```bash
# CPU和内存
htop

# 磁盘IO
sudo iotop

# 查看磁盘空间
df -h

# 查看目录大小
du -sh /home/novelapp/novel-system/*
```

#### 查看应用日志
```bash
# Supervisor日志
supervisorctl tail -f novel-system

# Gunicorn日志
tail -f /home/novelapp/novel-system/logs/gunicorn-error.log

# Nginx日志
tail -f /var/log/nginx/novel-system-error.log
```

### 4. 性能监控

#### 安装Nginx Amplify（可选）
```bash
# 参考官方文档安装
curl -sS -L -O https://github.com/nginxinc/nginx-amplify-agent/raw/master/packages/install.sh
API_KEY='您的API_KEY' sh ./install.sh
```

## 防火墙配置

```bash
# 启用UFW防火墙
ufw enable

# 允许SSH
ufw allow 22/tcp

# 允许HTTP和HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# 查看状态
ufw status
```

## 安全加固

### 1. 禁用root远程登录
```bash
vim /etc/ssh/sshd_config
# 修改：PermitRootLogin no
systemctl restart sshd
```

### 2. 配置fail2ban
```bash
apt install -y fail2ban
systemctl enable fail2ban
systemctl start fail2ban
```

## 备份策略

### 1. 数据库备份脚本
```bash
vim /home/novelapp/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/novelapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
cp /home/novelapp/novel-system/data/*.db $BACKUP_DIR/db_$DATE.db

# 备份配置文件
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /home/novelapp/novel-system/.env

# 删除30天前的备份
find $BACKUP_DIR -type f -mtime +30 -delete
```

```bash
chmod +x /home/novelapp/backup.sh

# 添加到crontab
crontab -e
# 每天凌晨2点备份
0 2 * * * /home/novelapp/backup.sh
```

## 更新部署

### 1. 更新代码
```bash
cd /home/novelapp/novel-system
git pull origin main

# 或使用新的tar.gz包
```

### 2. 更新依赖
```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### 3. 重启服务
```bash
supervisorctl restart novel-system
```

## 故障排查

### 常见问题

#### 1. 服务无法启动
```bash
# 查看详细错误
supervisorctl tail -f novel-system

# 手动测试
source venv/bin/activate
python web/web_server_refactored.py
```

#### 2. 502 Bad Gateway
```bash
# 检查Gunicorn是否运行
supervisorctl status

# 检查端口
netstat -tulpn | grep 5000
```

#### 3. 权限问题
```bash
# 确保目录权限正确
chown -R novelapp:novelapp /home/novelapp/novel-system
chmod -R 755 /home/novelapp/novel-system
```

#### 4. 内存不足
```bash
# 创建swap文件
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 性能优化

### 1. Gunicorn配置优化
```bash
# 根据CPU核心数调整worker数量
# $(($(nproc) * 2)) + 1

# 在supervisor配置中修改
command=/home/novelapp/novel-system/venv/bin/gunicorn \
  -w $(($(nproc) * 2) + 1) \
  -k gevent \
  --worker-class gevent \
  --worker-connections 1000 \
  --timeout 600 \
  -b 127.0.0.1:5000 \
  web.web_server_refactored:app
```

### 2. Nginx缓存配置
```nginx
# 添加到http块
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=app_cache:10m max_size=1g inactive=60m;

# 在location块中使用
location /static {
    proxy_cache app_cache;
    proxy_cache_valid 200 30d;
    proxy_cache_use_stale error timeout invalid_header updating;
    # ... 其他配置
}
```

## 联系支持

如果遇到问题，请检查：
1. 应用日志：`/home/novelapp/novel-system/logs/`
2. Nginx日志：`/var/log/nginx/`
3. Supervisor日志：`supervisorctl tail novel-system`

## 部署检查清单

- [ ] 服务器环境配置完成
- [ ] 代码上传并解压
- [ ] Python虚拟环境创建
- [ ] 依赖安装完成
- [ ] 环境变量配置
- [ ] 数据库初始化
- [ ] Nginx配置并启动
- [ ] 域名DNS解析配置
- [ ] SSL证书安装
- [ ] Supervisor配置并启动
- [ ] 防火墙规则配置
- [ ] 备份脚本配置
- [ ] 测试访问：http://您的域名
- [ ] 测试HTTPS：https://您的域名