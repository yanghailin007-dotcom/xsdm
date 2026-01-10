# 阿里云部署工具集

本目录包含用于将小说生成系统部署到阿里云服务器的完整工具集。

## 📁 工具清单

### 📖 文档

- [`DEPLOYMENT_QUICKSTART.md`](DEPLOYMENT_QUICKSTART.md) - 快速开始指南
- 完整部署指南位于：`docs/guides/ALIYUN_DEPLOYMENT_GUIDE.md`

### 🚀 服务器端脚本

| 脚本 | 用途 | 使用权限 |
|------|------|----------|
| [`aliyun_deploy.sh`](aliyun_deploy.sh) | 一键配置服务器环境 | sudo |
| [`setup_supervisor.sh`](setup_supervisor.sh) | 配置Supervisor服务管理 | sudo |
| [`deploy_app.sh`](deploy_app.sh) | 部署应用（安装依赖等） | 普通用户 |
| [`backup.sh`](backup.sh) | 备份数据库和配置 | 普通用户 |
| [`monitor.sh`](monitor.sh) | 监控服务器状态 | 普通用户 |
| [`view_logs.sh`](view_logs.sh) | 查看应用日志 | 普通用户 |

### 💻 本地脚本

| 脚本 | 用途 | 运行环境 |
|------|------|----------|
| [`upload_to_server.bat`](upload_to_server.bat) | 上传代码到服务器 | Windows |

## 🎯 快速开始

### 方式一：全新部署

1. **配置服务器**
```bash
# SSH连接服务器
ssh root@您的服务器IP

# 下载并运行一键部署脚本
wget https://raw.githubusercontent.com/您的仓库/main/scripts/deploy/aliyun_deploy.sh
sudo bash aliyun_deploy.sh
```

2. **上传代码**
- 方式A：使用Git（推荐）
```bash
# 在服务器上
git clone https://github.com/您的仓库.git /home/novelapp/novel-system
```

- 方式B：使用Windows上传工具
```cmd
# 在本地Windows
cd d:\work6.05
scripts\deploy\upload_to_server.bat
```

3. **部署应用**
```bash
# 在服务器上
ssh novelapp@您的服务器IP
cd ~/novel-system
bash scripts/deploy/deploy_app.sh
```

4. **配置环境变量**
```bash
vim .env
```

5. **启动服务**
```bash
sudo bash scripts/deploy/setup_supervisor.sh
```

6. **配置SSL证书**
```bash
sudo certbot --nginx -d 您的域名 -d www.您的域名
```

### 方式二：更新现有部署

```bash
# 在服务器上
cd ~/novel-system
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo supervisorctl restart novel-system
```

## 📝 详细文档

请查看 [`DEPLOYMENT_QUICKSTART.md`](DEPLOYMENT_QUICKSTART.md) 获取更详细的部署说明和故障排查指南。

## 🛠️ 常用命令

### 服务管理
```bash
# 查看状态
sudo supervisorctl status novel-system

# 重启服务
sudo supervisorctl restart novel-system

# 停止服务
sudo supervisorctl stop novel-system

# 查看日志
sudo supervisorctl tail -f novel-system
```

### 日志查看
```bash
# 使用日志查看工具（交互式）
bash scripts/deploy/view_logs.sh

# 直接查看
tail -f ~/novel-system/logs/gunicorn-error.log
```

### 服务器监控
```bash
bash scripts/deploy/monitor.sh
```

### 数据备份
```bash
bash scripts/deploy/backup.sh
```

## 🔧 脚本说明

### aliyun_deploy.sh
**用途**：一键配置服务器基础环境

**功能**：
- 更新系统
- 安装Python 3.10
- 安装Nginx和Supervisor
- 创建应用用户
- 配置防火墙
- 配置Nginx站点

**使用**：
```bash
sudo bash aliyun_deploy.sh
```

### setup_supervisor.sh
**用途**：配置Supervisor进程管理

**功能**：
- 创建Supervisor配置文件
- 自动计算worker数量
- 启动应用服务

**使用**：
```bash
sudo bash setup_supervisor.sh
```

### deploy_app.sh
**用途**：部署应用

**功能**：
- 创建Python虚拟环境
- 安装项目依赖
- 配置环境变量模板
- 创建必要目录

**使用**：
```bash
bash deploy_app.sh
```

### backup.sh
**用途**：备份数据

**功能**：
- 备份数据库
- 备份配置文件
- 可选备份整个项目
- 自动清理旧备份

**使用**：
```bash
bash backup.sh
```

### monitor.sh
**用途**：监控服务器状态

**显示内容**：
- 系统信息
- CPU使用率
- 内存使用
- 磁盘使用
- 网络连接
- 应用状态
- 最近错误日志

**使用**：
```bash
bash monitor.sh
```

### view_logs.sh
**用途**：查看各种日志

**支持日志类型**：
- Supervisor日志
- Gunicorn错误/访问日志
- Nginx错误/访问日志

**使用**：
```bash
bash view_logs.sh
```

### upload_to_server.bat
**用途**：从Windows上传代码到服务器

**支持方式**：
- 直接上传整个目录
- 压缩后上传
- 显示手动上传命令

**使用**：
```cmd
scripts\deploy\upload_to_server.bat
```

## 📋 部署检查清单

在部署前，请确保：

- [ ] 已购买阿里云ECS服务器
- [ ] 已购买域名
- [ ] 域名DNS已解析到服务器IP
- [ ] 已配置服务器安全组（开放80、443端口）
- [ ] 已准备好API密钥（豆包、NanoBanana等）

部署后，请验证：

- [ ] 服务正常运行
- [ ] 网站可以访问
- [ ] HTTPS证书有效
- [ ] 数据库正常工作
- [ ] 日志正常记录

## 🔐 安全建议

1. **禁用root远程登录**
```bash
sudo vim /etc/ssh/sshd_config
# 设置: PermitRootLogin no
sudo systemctl restart sshd
```

2. **配置防火墙**
```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

3. **定期备份数据**
```bash
# 添加到crontab
crontab -e
# 每天凌晨2点备份
0 2 * * * /home/novelapp/novel-system/scripts/deploy/backup.sh
```

## 🆘 获取帮助

如遇问题，请：

1. 查看详细文档：`docs/guides/ALIYUN_DEPLOYMENT_GUIDE.md`
2. 查看日志：使用 `view_logs.sh`
3. 检查服务状态：使用 `monitor.sh`
4. 查看错误日志：`tail -f ~/novel-system/logs/gunicorn-error.log`

## 📄 许可证

本工具集与主项目使用相同的许可证。