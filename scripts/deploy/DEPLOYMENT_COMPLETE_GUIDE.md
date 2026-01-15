# 完整部署工具使用指南

## 概述

这是一套完整的自动化部署工具，实现了从本地代码到服务器运行的全流程自动化：

1. ✅ **创建部署压缩包** - 使用 Git Bash 创建 tar.gz 压缩包
2. ✅ **上传到服务器** - 使用 SCP 上传压缩包和部署脚本
3. ✅ **自动部署** - 解压、安装依赖、配置环境
4. ✅ **启动服务** - 使用 Gunicorn 启动 Web 服务
5. ✅ **测试验证** - 自动测试应用是否正常运行

## 文件说明

### Windows 批处理脚本
- **[`deploy_now_fixed.bat`](deploy_now_fixed.bat)** - 主部署脚本（Windows 端）
  - 创建压缩包
  - 上传到服务器
  - 执行部署
  - 测试验证

### Linux 部署脚本
- **[`server_deploy.sh`](server_deploy.sh)** - 服务器端部署脚本
  - 检查压缩包
  - 创建项目目录
  - 解压代码
  - 设置虚拟环境
  - 安装依赖
  - 创建配置
  - 启动服务
  - 测试验证

## 使用方法

### 前提条件

1. **本地环境**
   - Windows 10/11
   - Git for Windows（包含 Git Bash）
   - SSH 客户端
   - 服务器 SSH 私钥文件

2. **服务器环境**
   - Ubuntu 20.04/22.04/24.04
   - Python 3.10+（会自动安装）
   - 足够的磁盘空间（建议 10GB+）

3. **网络要求**
   - 可以访问服务器 SSH 端口（22）
   - 可以访问服务器 Web 端口（5000）

### 快速开始

#### 1. 配置服务器信息

编辑 [`deploy_now_fixed.bat`](deploy_now_fixed.bat)，修改服务器配置：

```batch
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem
```

#### 2. 运行部署脚本

**方式一：双击运行**
```
双击 deploy_now_fixed.bat
```

**方式二：命令行运行**
```cmd
cd d:\work6.05
scripts\deploy\deploy_now_fixed.bat
```

#### 3. 等待部署完成

脚本会自动执行以下步骤：

```
========================================
   完整自动部署工具 - 上传、部署、运行、测试
========================================

服务器信息:
  IP: 8.163.37.124
  用户: root
  密钥: d:\work6.05\xsdm.pem

正在设置私钥权限...
正在测试SSH连接...
SSH连接成功

========================================
步骤 1/5: 创建部署压缩包
========================================

正在创建压缩包: novel_system_20260115_195030.tar.gz
压缩包创建成功: novel_system_20260115_195030.tar.gz
大小: 709708265 字节

========================================
步骤 2/5: 上传压缩包到服务器
========================================

正在上传 novel_system_20260115_195030.tar.gz 到服务器...
上传成功

========================================
步骤 3/5: 上传部署脚本到服务器
========================================

正在上传部署脚本...
部署脚本上传成功

========================================
步骤 4/5: 执行部署并启动服务
========================================

正在部署应用并启动服务...
步骤 1/6: 检查上传的压缩包...
找到压缩包: /tmp/novel_system_20260115_195030.tar.gz
步骤 2/6: 创建项目目录...
步骤 3/6: 解压代码...
步骤 4/6: 设置虚拟环境...
使用 Python 3.12.3
虚拟环境已创建
正在安装依赖...
依赖已安装
步骤 5/6: 创建配置文件...
配置文件已创建
步骤 6/6: 启动应用服务...
✓ 服务启动成功
正在测试应用...
✓ 应用响应正常
✓ HTTP 状态码: 200

========================================
✓ 部署完成！
========================================

访问网站: http://172.18.60.76:5000

========================================
步骤 5/5: 测试应用访问
========================================

服务器IP: 172.18.60.76

正在测试 HTTP 连接...
HTTP状态码: 200

========================================
  ✓ 所有步骤完成！
========================================

部署成功！应用已启动并运行。

访问地址:
  本地测试: http://127.0.0.1:5000/
  外网访问: http://172.18.60.76:5000/

服务管理命令:
  查看状态: ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "pgrep -f gunicorn"
  停止服务: ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "pkill -f gunicorn"
  查看日志: ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "tail -f /home/novelapp/novel-system/logs/error.log"

连接到服务器:
  ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
```

## 部署流程详解

### 1. 创建压缩包（本地）

使用 Git Bash 创建 tar.gz 压缩包，排除不必要的文件：

```bash
tar -czf novel_system_TIMESTAMP.tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='logs' \
  --exclude='generated_images' \
  --exclude='*.tar.gz' \
  --exclude='.env' \
  --exclude='xsdm.pem' \
  .
```

**排除的文件：**
- Python 缓存文件（`__pycache__`, `*.pyc`）
- Git 仓库（`.git`）
- 日志文件（`logs/`）
- 生成的图片（`generated_images/`）
- 环境配置（`.env`）
- SSH 密钥（`xsdm.pem`）
- 临时压缩包（`*.tar.gz`）

### 2. 上传到服务器（SCP）

使用 SCP 上传两个文件：
1. 压缩包 → `/tmp/novel_system_TIMESTAMP.tar.gz`
2. 部署脚本 → `/tmp/deploy_script.sh`

### 3. 执行部署（服务器）

部署脚本 [`server_deploy.sh`](server_deploy.sh) 会自动执行：

#### 步骤 1: 检查压缩包
```bash
TAR_FILE=$(ls -t /tmp/novel_system_*.tar.gz 2>/dev/null | head -1)
```

#### 步骤 2: 创建项目目录
```bash
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
```

#### 步骤 3: 解压代码
```bash
cd /home/novelapp/novel-system
tar -xzf "$TAR_FILE"
rm -f "$TAR_FILE"
```

#### 步骤 4: 设置虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install flask gunicorn eventlet -q
pip install -r requirements.txt -q
```

**支持的 Python 版本：**
- Python 3.10（Ubuntu 20.04/22.04）
- Python 3.12（Ubuntu 24.04）
- 其他 Python 3.x 版本

#### 步骤 5: 创建配置文件
```bash
cat > .env << 'ENVEOF'
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False
LOG_LEVEL=INFO
ENVEOF
```

#### 步骤 6: 启动服务
```bash
# 停止旧服务
pkill -f "gunicorn.*web.web_server_refactored" || true

# 启动新服务（后台运行）
nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 \
  --daemon \
  --pidfile /tmp/novel_system.pid \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  web.web_server_refactored:app

# 等待服务启动
sleep 5

# 检查服务状态
if pgrep -f "gunicorn.*web.web_server_refactored" > /dev/null; then
    echo "✓ 服务启动成功"
fi
```

**Gunicorn 配置说明：**
- `-w 2` - 2 个工作进程
- `-b 0.0.0.0:5000` - 绑定所有网络接口的 5000 端口
- `--timeout 600` - 请求超时 600 秒（10 分钟）
- `--daemon` - 后台运行
- `--pidfile` - PID 文件位置
- `--access-logfile` - 访问日志
- `--error-logfile` - 错误日志

### 4. 测试验证

#### 服务状态检查
```bash
# 检查进程
pgrep -f gunicorn

# 检查端口
netstat -tuln | grep ':5000'

# 测试 HTTP
curl -s http://127.0.0.1:5000/
```

#### 应用响应测试
```bash
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/)
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✓ 应用响应正常"
fi
```

## 服务管理

### 查看服务状态

```bash
# 方法 1: 使用 SSH 从本地查看
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "pgrep -f gunicorn"

# 方法 2: 连接到服务器后查看
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
pgrep -f gunicorn
ps aux | grep gunicorn
```

### 查看日志

```bash
# 错误日志（实时）
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "tail -f /home/novelapp/novel-system/logs/error.log"

# 访问日志（实时）
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "tail -f /home/novelapp/novel-system/logs/access.log"

# 查看最近 50 行错误日志
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "tail -50 /home/novelapp/novel-system/logs/error.log"
```

### 停止服务

```bash
# 方法 1: 使用 SSH 从本地停止
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "pkill -f gunicorn"

# 方法 2: 连接到服务器后停止
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
pkill -f gunicorn

# 方法 3: 使用 PID 文件
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
kill $(cat /tmp/novel_system.pid)
```

### 重启服务

```bash
# 方法 1: 连接到服务器手动重启
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
cd /home/novelapp/novel-system
source venv/bin/activate
pkill -f gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --daemon web.web_server_refactored:app

# 方法 2: 一键重启命令
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "cd /home/novelapp/novel-system && source venv/bin/activate && pkill -f gunicorn && sleep 2 && gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --daemon web.web_server_refactored:app"
```

## 常见问题排查

### 1. 压缩包创建失败

**问题：** `错误: 压缩包创建失败`

**排查：**
```cmd
# 检查 Git Bash 是否安装
"C:\Program Files\Git\bin\bash.exe" --version

# 检查磁盘空间
dir d:\work6.05
```

**解决：**
- 安装 Git for Windows
- 清理磁盘空间

### 2. SSH 连接失败

**问题：** `错误: SSH连接失败`

**排查：**
```cmd
# 测试 SSH 连接
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "echo 'test'"
```

**解决：**
- 检查私钥文件路径是否正确
- 检查服务器 IP 是否正确
- 检查网络连接
- 检查服务器 SSH 服务是否运行

### 3. 上传失败

**问题：** `错误: 上传失败`

**排查：**
```cmd
# 测试 SCP
scp -i "d:\work6.05\xsdm.pem" test.txt root@8.163.37.124:/tmp/
```

**解决：**
- 检查网络连接
- 检查服务器磁盘空间
- 检查 /tmp 目录权限

### 4. Python 未找到

**问题：** `错误: 未找到 Python 3`

**排查：**
```bash
# 连接到服务器检查
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
python3 --version
which python3
```

**解决：**
- 脚本会自动安装 Python 3.10
- 如果自动安装失败，手动安装：
```bash
apt-get update
apt-get install -y python3.10 python3.10-venv python3.10-dev python3-pip
```

### 5. 依赖安装失败

**问题：** `警告: 部分依赖安装失败`

**排查：**
```bash
# 连接到服务器查看详细错误
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
cd /home/novelapp/novel-system
source venv/bin/activate
pip install -r requirements.txt
```

**解决：**
- 检查 requirements.txt 文件
- 手动安装失败的依赖
- 检查网络连接（可能需要配置 pip 镜像源）

### 6. 服务启动失败

**问题：** `✗ 服务启动失败`

**排查：**
```bash
# 查看详细错误日志
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
cat /home/novelapp/novel-system/logs/error.log

# 手动启动测试
cd /home/novelapp/novel-system
source venv/bin/activate
gunicorn -w 2 -b 127.0.0.1:5000 --timeout 600 web.web_server_refactored:app
```

**解决：**
- 检查应用代码是否有语法错误
- 检查依赖是否完整安装
- 检查端口 5000 是否被占用
- 检查配置文件是否正确

### 7. 应用无响应

**问题：** `✗ 应用无响应`

**排查：**
```bash
# 检查服务进程
ps aux | grep gunicorn

# 检查端口监听
netstat -tuln | grep ':5000'

# 测试本地访问
curl -v http://127.0.0.1:5000/

# 查看错误日志
tail -50 /home/novelapp/novel-system/logs/error.log
```

**解决：**
- 确保服务正在运行
- 检查防火墙设置
- 检查应用启动日志

## 优化建议

### 1. 使用 Supervisor 管理服务

安装 Supervisor 以实现服务的自动重启和管理：

```bash
# 安装 Supervisor
apt-get install -y supervisor

# 创建配置文件
cat > /etc/supervisor/conf.d/novel-system.conf << 'EOF'
[program:novel-system]
directory=/home/novelapp/novel-system
command=/home/novelapp/novel-system/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
user=novelapp
autostart=true
autorestart=true
stderr_logfile=/home/novelapp/novel-system/logs/error.log
stdout_logfile=/home/novelapp/novel-system/logs/access.log
EOF

# 启动服务
supervisorctl reread
supervisorctl update
supervisorctl start novel-system

# 管理命令
supervisorctl status novel-system
supervisorctl restart novel-system
supervisorctl stop novel-system
```

### 2. 使用 Nginx 反向代理

安装 Nginx 作为反向代理：

```bash
# 安装 Nginx
apt-get install -y nginx

# 创建配置文件
cat > /etc/nginx/sites-available/novel-system << 'EOF'
server {
    listen 80;
    server_name 8.163.37.124;

    client_max_body_size 100M;

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

# 启用配置
ln -s /etc/nginx/sites-available/novel-system /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 3. 配置 SSL 证书

使用 Let's Encrypt 免费 SSL 证书：

```bash
# 安装 Certbot
apt-get install -y certbot python3-certbot-nginx

# 申请证书
certbot --nginx -d your-domain.com

# 自动续期
certbot renew --dry-run
```

### 4. 配置防火墙

使用 UFW 配置防火墙：

```bash
# 安装 UFW
apt-get install -y ufw

# 允许 SSH
ufw allow 22/tcp

# 允许 HTTP
ufw allow 80/tcp

# 允许 HTTPS
ufw allow 443/tcp

# 启用防火墙
ufw --force enable

# 查看状态
ufw status
```

## 技术细节

### 系统兼容性

| 系统 | Python 版本 | 状态 |
|------|------------|------|
| Ubuntu 20.04 | Python 3.10 | ✅ 支持 |
| Ubuntu 22.04 | Python 3.10 | ✅ 支持 |
| Ubuntu 24.04 | Python 3.12 | ✅ 支持 |

### 压缩包优化

- 使用 tar.gz 格式（兼容性好）
- 排除不必要的文件（减小体积）
- 典型压缩率：50-70%

### 网络优化

- 使用 SCP（安全、可靠）
- 支持断点续传（使用 rsync 可实现）
- 压缩传输（SCP 自动压缩）

### 性能配置

- Gunicorn 工作进程：2 个
- 请求超时：600 秒
- 适合中等流量应用

## 安全建议

1. **使用专用用户**
   - 不要使用 root 用户运行应用
   - 创建专用用户（如 `novelapp`）

2. **限制文件权限**
   - SSH 私钥：`600`（仅所有者可读写）
   - 应用文件：`644`（所有者可写，其他只读）
   - 目录：`755`（所有者可写，其他可执行）

3. **配置防火墙**
   - 只开放必要端口（22, 80, 443）
   - 限制访问来源

4. **定期更新**
   - 系统安全补丁
   - Python 依赖更新
   - 应用代码更新

5. **日志监控**
   - 定期检查错误日志
   - 监控应用性能
   - 设置日志轮转

## 总结

这套完整的部署工具实现了：

✅ **全自动化** - 一键完成从代码到运行的所有步骤
✅ **错误处理** - 每个步骤都有错误检查和提示
✅ **测试验证** - 自动测试应用是否正常运行
✅ **易于管理** - 提供完整的服务管理命令
✅ **文档完善** - 详细的使用说明和故障排查指南

只需运行一个脚本，即可完成应用部署！
