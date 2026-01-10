# 阿里云部署快速开始指南

## 📋 前提条件

- ✅ 已购买阿里云ECS服务器
- ✅ 已购买域名
- ✅ 本地有项目代码

## 🚀 快速部署步骤

### 第一步：服务器基础配置

使用SSH连接到服务器：

```bash
ssh root@您的服务器IP
```

运行一键部署脚本：

```bash
# 下载并运行部署脚本（需要root权限）
wget https://raw.githubusercontent.com/您的仓库/main/scripts/deploy/aliyun_deploy.sh
sudo bash aliyun_deploy.sh
```

按提示输入：
- 域名（例如：example.com）
- 服务器公网IP
- 应用用户名（默认：novelapp）

### 第二步：上传代码到服务器

#### 方法1：使用Git（推荐）

```bash
# 在服务器上执行
cd /home/novelapp
git clone https://github.com/您的用户名/您的仓库.git novel-system
```

#### 方法2：使用本地Windows上传脚本

在本地项目目录运行：

```bash
# PowerShell或CMD
cd d:\work6.05
scripts\deploy\upload_to_server.bat
```

按提示输入：
- 服务器IP地址
- 用户名（默认：novelapp）

### 第三步：配置应用

SSH登录服务器：

```bash
ssh novelapp@您的服务器IP
cd ~/novel-system
```

运行应用部署脚本：

```bash
bash scripts/deploy/deploy_app.sh
```

### 第四步：配置环境变量

编辑环境变量文件：

```bash
vim .env
```

配置以下关键参数：

```bash
# 生成密钥
SECRET_KEY=$(openssl rand -hex 32)

# API密钥
DOUBAO_API_KEY=您的豆包API密钥
NANOBANANA_API_KEY=您的NanoBanana API密钥

# 数据库
DATABASE_URL=sqlite:///data/users.db

# 生产环境
FLASK_ENV=production
DEBUG=False
```

### 第五步：初始化数据库

```bash
source venv/bin/activate
python -c "from web.models.user_model import db; from web.web_server_refactored import app; app.app_context().push(); db.create_all()"
```

### 第六步：启动服务

```bash
sudo bash scripts/deploy/setup_supervisor.sh
```

### 第七步：配置SSL证书

确保域名DNS已解析到服务器IP，然后：

```bash
sudo certbot --nginx -d 您的域名 -d www.您的域名
```

### 第八步：验证部署

检查服务状态：

```bash
sudo supervisorctl status novel-system
sudo systemctl status nginx
```

访问网站：
- http://您的域名
- https://您的域名

## 🛠️ 常用命令

### 查看服务状态
```bash
sudo supervisorctl status novel-system
```

### 重启服务
```bash
sudo supervisorctl restart novel-system
```

### 查看日志
```bash
# 实时日志
sudo supervisorctl tail -f novel-system

# 或使用日志查看工具
bash scripts/deploy/view_logs.sh
```

### 监控服务器
```bash
bash scripts/deploy/monitor.sh
```

### 备份数据
```bash
bash scripts/deploy/backup.sh
```

## 📝 配置DNS解析

在阿里云域名控制台添加以下解析：

| 记录类型 | 主机记录 | 记录值 |
|---------|---------|--------|
| A | @ | 服务器IP |
| A | www | 服务器IP |

## 🔍 故障排查

### 服务无法启动

```bash
# 查看详细错误
sudo supervisorctl tail -f novel-system

# 手动测试
source venv/bin/activate
python web/web_server_refactored.py
```

### 502 Bad Gateway

```bash
# 检查Gunicorn是否运行
sudo supervisorctl status

# 检查端口
netstat -tulpn | grep 5000
```

### 权限问题

```bash
sudo chown -R novelapp:novelapp /home/novelapp/novel-system
sudo chmod -R 755 /home/novelapp/novel-system
```

### Nginx配置问题

```bash
# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

## 📊 性能优化

### 调整Worker数量

根据服务器CPU核心数调整：

```bash
# 编辑Supervisor配置
sudo vim /etc/supervisor/conf.d/novel-system.conf

# 修改worker数量
# -w $(($(nproc) * 2) + 1)

# 重启服务
sudo supervisorctl restart novel-system
```

### 配置Swap（内存不足时）

```bash
# 创建2GB swap
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 🔄 更新部署

```bash
cd ~/novel-system
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo supervisorctl restart novel-system
```

## 📞 获取帮助

查看详细文档：
- 完整部署指南：`docs/guides/ALIYUN_DEPLOYMENT_GUIDE.md`
- Web系统指南：`docs/guides/WEB_SYSTEM_README.md`

## ✅ 部署检查清单

- [ ] 服务器环境配置完成
- [ ] 代码上传到服务器
- [ ] Python虚拟环境创建
- [ ] 依赖安装完成
- [ ] 环境变量配置（.env）
- [ ] 数据库初始化
- [ ] Nginx配置并启动
- [ ] 域名DNS解析配置
- [ ] SSL证书安装
- [ ] Supervisor配置并启动
- [ ] 防火墙规则配置
- [ ] 备份脚本配置
- [ ] 测试访问网站