# 从本地Windows连接阿里云服务器部署指南

## 📋 前提条件检查

### 1. 获取服务器公网IP

⚠️ **重要**：您提供的 `172.18.60.76` 是私网地址，无法从外网直接访问。

**如何获取公网IP**：
1. 登录阿里云ECS控制台：https://ecs.console.aliyun.com/
2. 找到您的ECS实例
3. 在实例详情页查看"公网IP"或"弹性公网IP"
4. 如果没有公网IP，需要先分配一个

### 2. 准备私钥文件

- 确保您有 `.pem` 格式的私钥文件
- 私钥文件应该保存在本地安全的目录中

## 🚀 部署步骤

### 方法1：使用PowerShell/CMD（推荐）

#### 步骤1：测试SSH连接

打开PowerShell或CMD，执行：

```powershell
# 替换以下参数
# 公网IP: 您的服务器公网IP
# 私钥路径: 您的私钥文件路径
# 用户名: admin（或其他用户名）

ssh -i "C:\path\to\your\key.pem" -p 22 admin@您的公网IP
```

**第一次连接会提示确认主机指纹，输入 `yes`**

如果连接成功，您会看到服务器的命令行提示符。

#### 步骤2：准备本地代码

在本地PowerShell中：

```powershell
# 进入项目目录
cd d:\work6.05

# 创建压缩包（使用Git Bash）
"C:\Program Files\Git\bin\bash.exe" -c "tar -czf novel_system.tar.gz --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='logs/*' --exclude='generated_images/*' --exclude='temp_fanqie_upload/*' --exclude='.env' --exclude='test_*.py' --exclude='*.db' ."
```

#### 步骤3：上传代码到服务器

```powershell
# 使用SCP上传压缩包
scp -i "C:\path\to\your\key.pem" -P 22 novel_system.tar.gz admin@您的公网IP:/tmp/

# 或使用PSCP（如果安装了PuTTY）
pscp -i "C:\path\to\your\key.pem" -P 22 novel_system.tar.gz admin@您的公网IP:/tmp/
```

#### 步骤4：SSH登录服务器并部署

```powershell
# 连接服务器
ssh -i "C:\path\to\your\key.pem" -p 22 admin@您的公网IP
```

在服务器上执行：

```bash
# 切换到root（如果需要）
sudo su -

# 下载并运行快速部署脚本
cd /tmp
cat > quick_deploy.sh << 'EOF'
#!/bin/bash
set -e
echo "开始配置服务器环境..."

# 更新系统
apt update && apt upgrade -y

# 安装基础工具
apt install -y wget curl git vim build-essential software-properties-common python3.10 python3.10-venv python3.10-dev python3-pip

# 创建应用用户
useradd -m -s /bin/bash novelapp || true

# 创建项目目录
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
chown -R novelapp:novelapp /home/novelapp/novel-system

# 解压代码
tar -xzf /tmp/novel_system.tar.gz -C /home/novelapp/novel-system
rm /tmp/novel_system.tar.gz

# 安装Nginx和Supervisor
apt install -y nginx supervisor

echo "服务器环境配置完成！"
echo "接下来请手动执行应用部署步骤。"
EOF

chmod +x quick_deploy.sh
bash quick_deploy.sh
```

#### 步骤5：部署应用

继续在服务器上执行：

```bash
# 切换到应用用户
su - novelapp
cd /home/novelapp/novel-system

# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
pip install gunicorn eventlet

# 配置环境变量
cp .env.example .env
vim .env
# 编辑以下内容：
# SECRET_KEY=$(openssl rand -hex 32)
# DOUBAO_API_KEY=您的API密钥
# NANOBANANA_API_KEY=您的API密钥
# FLASK_ENV=production
# DEBUG=False

# 初始化数据库
python -c "from web.models.user_model import db; from web.web_server_refactored import app; app.app_context().push(); db.create_all()"

# 退出应用用户
exit
```

#### 步骤6：配置Nginx和Supervisor

```bash
# 配置Nginx
sudo su -
cat > /etc/nginx/sites-available/novel-system << 'EOF'
server {
    listen 80;
    server_name _;

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
EOF

ln -sf /etc/nginx/sites-available/novel-system /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# 配置Supervisor
WORKERS=$(($(nproc) * 2 + 1))
cat > /etc/supervisor/conf.d/novel-system.conf << EOF
[program:novel-system]
command=/home/novelapp/novel-system/venv/bin/gunicorn -w $WORKERS -b 127.0.0.1:5000 --timeout 600 --access-logfile /home/novelapp/novel-system/logs/gunicorn-access.log --error-logfile /home/novelapp/novel-system/logs/gunicorn-error.log --log-level info web.web_server_refactored:app
directory=/home/novelapp/novel-system
user=novelapp
autostart=true
autorestart=true
startretries=3
stderr_logfile=/home/novelapp/novel-system/logs/supervisor-stderr.log
stdout_logfile=/home/novelapp/novel-system/logs/supervisor-stdout.log
environment=FLASK_ENV="production"
EOF

supervisorctl reread
supervisorctl update
supervisorctl start novel-system

# 配置防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "部署完成！"
echo "检查服务状态："
supervisorctl status novel-system
systemctl status nginx
```

### 方法2：使用PuTTY（Windows图形界面）

#### 安装PuTTY

1. 下载PuTTY：https://www.putty.org/
2. 安装PuTTY和PuTTYgen

#### 转换私钥格式

1. 打开PuTTYgen
2. 点击"Load"加载您的`.pem`私钥文件
3. 点击"Save private key"保存为`.ppk`格式

#### 使用PuTTY连接

1. 打开PuTTY
2. **Host Name (or IP address)**: 输入您的公网IP
3. **Port**: 22
4. **Connection type**: SSH
5. 在左侧菜单：Connection → SSH → Auth → Credentials
6. **Private key file**: 选择您的`.ppk`文件
7. 点击"Open"连接
8. **Login as**: admin

#### 使用WinSCP上传文件

1. 下载WinSCP：https://winscp.net/
2. 配置连接：
   - **File protocol**: SFTP
   - **Host name**: 您的公网IP
   - **Port**: 22
   - **User name**: admin
   - **Private key**: 您的私钥文件
3. 连接后拖拽上传文件

### 方法3：使用VS Code Remote SSH（推荐开发人员）

#### 安装扩展

1. 在VS Code中安装"Remote - SSH"扩展
2. 配置SSH连接：

```json
// 在 ~/.ssh/config 中添加（Windows: C:\Users\您的用户名\.ssh\config）
Host aliyun-server
    HostName 您的公网IP
    User admin
    Port 22
    IdentityFile C:\path\to\your\key.pem
```

#### 连接并编辑

1. 按 `F1` 输入 "Remote-SSH: Connect to Host"
2. 选择 "aliyun-server"
3. 连接后可以直接在VS Code中编辑远程文件

## 🔧 常用命令

### 从本地连接服务器

```powershell
# SSH连接
ssh -i "C:\path\to\key.pem" admin@您的公网IP

# 上传文件
scp -i "C:\path\to\key.pem" local_file.txt admin@您的公网IP:/remote/path/

# 下载文件
scp -i "C:\path\to\key.pem" admin@您的公网IP:/remote/file.txt local_path/
```

### 在服务器上管理应用

```bash
# 查看服务状态
sudo supervisorctl status novel-system

# 重启服务
sudo supervisorctl restart novel-system

# 查看日志
sudo supervisorctl tail -f novel-system

# 重启Nginx
sudo systemctl restart nginx

# 查看Nginx日志
sudo tail -f /var/log/nginx/novel-system-error.log
```

## ✅ 验证部署

### 检查服务状态

```bash
# 在服务器上执行
sudo supervisorctl status novel-system
sudo systemctl status nginx
netstat -tulpn | grep -E '80|443|5000'
```

### 测试访问

在本地浏览器访问：
- `http://您的公网IP`
- 或 `http://您的域名`（如果已配置）

## 📝 部署检查清单

- [ ] 已获取服务器公网IP
- [ ] 已准备好私钥文件
- [ ] 可以SSH连接到服务器
- [ ] 代码已上传到服务器
- [ ] Python虚拟环境已创建
- [ ] 依赖已安装
- [ ] .env文件已配置
- [ ] 数据库已初始化
- [ ] Nginx已配置并运行
- [ ] Supervisor已配置并运行
- [ ] 防火墙规则已配置
- [ ] 可以从公网访问网站

## 🆘 故障排查

### 无法连接SSH

1. **检查公网IP是否正确**
2. **检查安全组规则**：在阿里云控制台确保22端口已开放
3. **检查私钥权限**：私钥文件应该是600权限
4. **检查用户名**：确认用户名是admin还是root

### 代码上传失败

1. **检查磁盘空间**：`df -h`
2. **检查目录权限**：确保有写入权限
3. **使用较小的文件**：先上传小文件测试

### 服务无法启动

1. **查看详细日志**：`sudo supervisorctl tail -f novel-system`
2. **检查端口占用**：`netstat -tulpn | grep 5000`
3. **检查配置文件**：`sudo nginx -t`

## 📞 获取帮助

- 详细文档：`docs/guides/ALIYUN_DEPLOYMENT_GUIDE.md`
- 阿里云文档：https://help.aliyun.com/product/25365.html