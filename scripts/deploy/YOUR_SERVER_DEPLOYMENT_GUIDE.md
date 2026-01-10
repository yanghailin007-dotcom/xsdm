# 您的服务器专属部署指南

## 📋 服务器信息

- **主机地址**: 172.18.60.76（私网地址）
- **端口**: 22
- **用户名**: admin
- **认证方式**: 私钥
- **Token**: js7hkkwk2n（有效期至：2026-01-11 13:09:20）

> ⚠️ **注意**：Token有效期只有24小时，请尽快完成部署！

## 🚀 部署步骤

### 第一步：连接服务器

使用阿里云Workbench Web终端：

1. 访问阿里云ECS控制台
2. 找到您的实例
3. 点击"远程连接" → "Workbench"
4. 使用提供的Token登录

或者使用SSH客户端（如果您有公网IP）：

```bash
# 如果您有公网IP，使用私钥连接
ssh -i 您的私钥.pem -p 22 admin@您的公网IP

# 或使用Token认证（Workbench方式）
# 在浏览器中直接使用Workbench终端
```

### 第二步：配置服务器环境

在服务器上执行以下命令：

```bash
# 切换到root用户（可能需要密码）
sudo su -

# 更新系统
apt update && apt upgrade -y

# 安装基础工具
apt install -y wget curl git vim build-essential software-properties-common

# 安装Python 3.10
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.10 python3.10-venv python3.10-dev python3-pip

# 创建应用用户
useradd -m -s /bin/bash novelapp
```

### 第三步：上传代码

#### 方法A：使用Git（推荐，如果有公网访问）

```bash
# 切换到应用用户
su - novelapp

# 克隆代码（替换为您的仓库地址）
git clone https://github.com/您的用户名/您的仓库.git /home/novelapp/novel-system
cd /home/novelapp/novel-system
```

#### 方法B：手动上传（如果是私网，无公网访问）

1. 在本地打包代码：
```cmd
cd d:\work6.05
tar -czf novel_system.tar.gz --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='logs/*' .
```

2. 通过Workbench上传：
   - 在Workbench终端中使用文件上传功能
   - 或使用`rz`命令（需要安装lrzsz）

```bash
# 在服务器上安装lrzsz
sudo apt install -y lrzsz

# 创建项目目录
sudo mkdir -p /home/novelapp/novel-system
sudo chown novelapp:novelapp /home/novelapp/novel-system

# 切换到项目目录
cd /home/novelapp/novel-system

# 上传文件
rz  # 然后选择您的tar.gz文件

# 解压
tar -xzf novel_system.tar.gz
rm novel_system.tar.gz
```

### 第四步：部署应用

```bash
# 确保在项目目录
cd /home/novelapp/novel-system

# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
pip install gunicorn eventlet

# 安装生产环境工具
sudo apt install -y nginx supervisor

# 创建必要目录
mkdir -p logs data generated_images temp_fanqie_upload
```

### 第五步：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

重要配置项：
```bash
# Flask配置
FLASK_APP=web.web_server_refactored
FLASK_ENV=production
SECRET_KEY=使用 openssl rand -hex 32 生成

# API密钥
DOUBAO_API_KEY=您的豆包API密钥
NANOBANANA_API_KEY=您的NanoBanana API密钥

# 文件路径
PROJECT_ROOT=/home/novelapp/novel-system
DATA_DIR=/home/novelapp/novel-system/data
LOGS_DIR=/home/novelapp/novel-system/logs
```

### 第六步：初始化数据库

```bash
source venv/bin/activate
python -c "from web.models.user_model import db; from web.web_server_refactored import app; app.app_context().push(); db.create_all()"
```

### 第七步：配置Nginx

```bash
# 创建Nginx配置
sudo vim /etc/nginx/sites-available/novel-system
```

添加以下内容（**注意**：私网地址需要配置公网IP或域名）：

```nginx
server {
    listen 80;
    server_name _;  # 使用_匹配所有请求，或配置您的域名

    access_log /var/log/nginx/novel-system-access.log;
    error_log /var/log/nginx/novel-system-error.log;

    client_max_body_size 100M;

    location /static {
        alias /home/novelapp/novel-system/web/static;
        expires 30d;
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
        
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/novel-system /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 第八步：配置Supervisor

```bash
# 创建Supervisor配置
sudo vim /etc/supervisor/conf.d/novel-system.conf
```

添加以下内容：
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

```bash
# 启动服务
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start novel-system

# 查看状态
sudo supervisorctl status novel-system
```

### 第九步：配置防火墙

```bash
# 安装并配置UFW
sudo apt install -y ufw
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 查看状态
sudo ufw status
```

### 第十步：配置公网访问（重要！）

由于您的服务器使用私网地址（172.18.60.76），需要配置公网访问：

#### 选项1：配置公网IP（如果有）

在阿里云ECS控制台：
1. 确认实例已分配公网IP
2. 在安全组中开放80和443端口
3. 配置域名解析到公网IP

#### 选项2：使用阿里云负载均衡（推荐）

1. 创建负载均衡实例
2. 配置后端服务器（172.18.60.76:80）
3. 绑定公网IP和域名

#### 选项3：使用NAT网关

1. 配置NAT网关
2. 配置DNAT规则映射到私网IP

### 第十一步：配置SSL证书（可选）

如果有公网访问和域名：

```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d 您的域名
```

## ✅ 验证部署

### 检查服务状态

```bash
# 检查应用服务
sudo supervisorctl status novel-system

# 检查Nginx
sudo systemctl status nginx

# 检查端口
netstat -tulpn | grep -E '80|443|5000'
```

### 查看日志

```bash
# 应用日志
sudo supervisorctl tail -f novel-system

# Nginx日志
sudo tail -f /var/log/nginx/novel-system-error.log

# Gunicorn日志
tail -f /home/novelapp/novel-system/logs/gunicorn-error.log
```

### 测试访问

```bash
# 本地测试
curl http://localhost

# 或从公网IP/域名测试
curl http://您的公网IP
curl http://您的域名
```

## 🔧 常用运维命令

```bash
# 重启应用
sudo supervisorctl restart novel-system

# 重启Nginx
sudo systemctl restart nginx

# 查看监控
bash /home/novelapp/novel-system/scripts/deploy/monitor.sh

# 备份数据
bash /home/novelapp/novel-system/scripts/deploy/backup.sh

# 查看日志
bash /home/novelapp/novel-system/scripts/deploy/view_logs.sh
```

## ⚠️ 重要注意事项

1. **Token有效期**：您的Token只有24小时有效期，请尽快完成部署
2. **私网地址**：172.18.60.76是私网地址，需要配置公网访问
3. **权限问题**：确保novelapp用户有足够权限
4. **安全组**：在阿里云控制台配置安全组规则
5. **API密钥**：记得配置.env文件中的API密钥

## 🆘 故障排查

### 服务无法启动

```bash
# 查看详细错误
sudo supervisorctl tail -f novel-system

# 检查端口占用
netstat -tulpn | grep 5000
```

### 权限问题

```bash
# 修复权限
sudo chown -R novelapp:novelapp /home/novelapp/novel-system
sudo chmod -R 755 /home/novelapp/novel-system
```

### 网络问题

```bash
# 检查防火墙
sudo ufw status

# 检查Nginx配置
sudo nginx -t

# 重启网络服务
sudo systemctl restart networking
```

## 📞 获取帮助

如遇问题：
1. 查看详细文档：`docs/guides/ALIYUN_DEPLOYMENT_GUIDE.md`
2. 查看日志：使用`view_logs.sh`
3. 检查服务状态：使用`monitor.sh`