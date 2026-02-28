# 部署指南

本文档说明如何将 Novel Generator 项目部署到生产环境。

## 📋 前置要求

- Python 3.11+
- Linux 服务器（推荐 Ubuntu 22.04）
- Nginx
- SSL 证书（Let's Encrypt 或其他）

## 🚀 快速部署

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y python3-pip python3-venv nginx git
```

### 2. 项目部署

```bash
# 克隆项目
cd /var/www
git clone <your-repo-url> novel-generator
cd novel-generator

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.production.example .env
# 编辑 .env 文件，填入真实的 API 密钥
nano .env
```

### 3. 启动服务

使用启动脚本：
```bash
chmod +x deploy/start_production.sh
./deploy/start_production.sh
```

或使用 Gunicorn 直接启动：
```bash
cd /var/www/novel-generator
source .venv/bin/activate
gunicorn -w 4 -b 127.0.0.1:5000 --timeout 300 web.wsgi:application
```

### 4. 配置 Nginx

```bash
# 复制 Nginx 配置
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/novel-generator

# 编辑配置，替换域名和路径
sudo nano /etc/nginx/sites-available/novel-generator

# 启用站点
sudo ln -s /etc/nginx/sites-available/novel-generator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. 配置 SSL (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 6. 配置进程守护 (Supervisor)

```bash
# 安装 Supervisor
sudo apt install -y supervisor

# 复制配置
sudo cp deploy/supervisor.conf.example /etc/supervisor/conf.d/novel-generator.conf

# 编辑配置，替换路径
sudo nano /etc/supervisor/conf.d/novel-generator.conf

# 更新配置
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start novel-generator
```

## 🐳 Docker 部署

### 使用 Docker Compose

```bash
# 复制环境变量文件
cp .env.production.example .env
# 编辑 .env 文件

# 启动服务
cd deploy
docker-compose up -d
```

### 单独使用 Docker

```bash
# 构建镜像
docker build -f deploy/Dockerfile -t novel-generator .

# 运行容器
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/小说项目:/app/小说项目 \
  -v $(pwd)/.env:/app/.env:ro \
  --name novel-generator \
  novel-generator
```

## 🔒 安全检查清单

部署前请确认：

- [ ] `.env` 文件已创建并配置了真实的 API 密钥
- [ ] `config/api_keys.py` 未被提交到 Git
- [ ] `.env` 文件未被提交到 Git
- [ ] 已配置 HTTPS
- [ ] 已配置防火墙（只开放 80、443 端口）
- [ ] 已配置日志轮转
- [ ] 已配置自动备份

## 📝 日志查看

```bash
# 应用日志
tail -f logs/novel_generator.log

# Nginx 访问日志
sudo tail -f /var/log/nginx/novel_generator_access.log

# Supervisor 日志
sudo tail -f /var/log/supervisor/novel-generator-stdout.log
```

## 🔄 更新部署

```bash
cd /var/www/novel-generator

# 拉取最新代码
git pull origin main

# 更新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 重启服务
sudo supervisorctl restart novel-generator
```

## 🐛 故障排查

### 服务无法启动

1. 检查环境变量是否正确配置
2. 检查日志文件权限
3. 检查端口是否被占用

### API 请求失败

1. 检查 API 密钥是否有效
2. 检查网络连接
3. 查看应用日志获取详细错误信息

### 健康检查失败

访问 `http://your-domain/health` 查看详细状态：
- `status: healthy` - 服务正常
- `status: degraded` - 部分功能异常，检查目录权限
- `status: unhealthy` - 服务异常，查看日志

## 📞 支持

如有问题，请查看：
- 应用日志：`logs/novel_generator.log`
- Nginx 日志：`/var/log/nginx/`
- 系统日志：`journalctl -u supervisor`
