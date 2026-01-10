# 简化部署指南

这个指南提供了分步骤的部署方案，不需要配置API密钥。

## 方案概述

部署将分为独立步骤，每步都可以单独测试：
1. 上传代码
2. 安装依赖
3. 启动服务

## 前提条件

- 已安装 Git for Windows
- 有服务器私钥文件 (xsdm.pem)
- 服务器已开放 SSH 端口 (22)

## 快速诊断

首先运行诊断工具：

```batch
cd d:\work6.05
scripts\deploy\diagnose_deploy_issue.bat
```

这会检查：
- SSH/SCP 工具是否安装
- 私钥文件是否存在
- 私钥权限是否正确
- SSH连接是否成功
- 压缩和上传功能是否正常

## 分步部署

### 步骤 1: 上传代码

使用简化上传脚本：

```batch
cd d:\work6.05
scripts\deploy\simple_upload.bat
```

这会：
- 创建代码压缩包
- 上传到服务器 `/tmp/` 目录
- 显示详细进度和错误信息

### 步骤 2: 在服务器上解压

连接到服务器：

```batch
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
```

然后执行：

```bash
# 创建项目目录
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images}

# 解压代码
cd /home/novelapp/novel-system
tar -xzf /tmp/novel_system_*.tar.gz
rm /tmp/novel_system_*.tar.gz

# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip
```

### 步骤 3: 安装依赖

```bash
# 安装基本依赖
pip install -r requirements.txt
pip install gunicorn eventlet flask

# 创建环境文件（不需要API密钥）
cat > .env << 'EOF'
# Web服务配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False

# 日志配置
LOG_LEVEL=INFO

# API密钥（可选，如果需要API功能再配置）
# ARK_API_KEY=your_key_here
EOF
```

### 步骤 4: 测试启动

```bash
# 测试启动
cd /home/novelapp/novel-system
source venv/bin/activate
python -c "from web.web_server_refactored import app; print('导入成功')"

# 如果上面成功，继续
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
```

在浏览器访问：`http://8.163.37.124:5000`

### 步骤 5: 配置系统服务（可选）

如果需要服务随系统启动，配置 supervisor：

```bash
# 安装supervisor
apt install -y supervisor

# 创建配置文件
cat > /etc/supervisor/conf.d/novel-system.conf << 'EOF'
[program:novel-system]
command=/home/novelapp/novel-system/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 --timeout 600 web.web_server_refactored:app
directory=/home/novelapp/novel-system
user=root
autostart=true
autorestart=true
stderr_logfile=/home/novelapp/novel-system/logs/error.log
stdout_logfile=/home/novelapp/novel-system/logs/access.log
EOF

# 启动服务
supervisorctl reread
supervisorctl update
supervisorctl start novel-system

# 查看状态
supervisorctl status
```

## 常见问题

### 问题 1: SSH连接失败

**检查：**
- 私钥文件路径是否正确
- 服务器IP是否正确
- 阿里云安全组是否开放22端口

**解决：**
```batch
# 详细连接测试
ssh -i d:\work6.05\xsdm.pem -v root@8.163.37.124
```

### 问题 2: 压缩包创建失败

**检查：**
- Git Bash 是否安装
- 是否在正确的目录 (d:\work6.05)

**解决：**
```batch
# 手动测试压缩
"C:\Program Files\Git\bin\bash.exe" -c "tar -czf test.tar.gz --exclude='__pycache__' --exclude='.git' ."
```

### 问题 3: 上传失败

**检查：**
- 服务器磁盘空间
- 网络连接

**解决：**
```bash
# 在服务器上检查空间
df -h /tmp
```

### 问题 4: Python模块导入失败

**检查：**
- Python版本 (需要 3.10+)
- 依赖是否安装完整

**解决：**
```bash
# 检查Python版本
python3.10 --version

# 重新安装依赖
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

## 不需要API密钥的功能

以下功能可以在没有API密钥的情况下使用：
- 项目管理
- 角色编辑
- 世界观查看
- 章节浏览
- 创意库管理

需要API密钥的功能：
- AI生成内容
- AI生成图片
- AI生成视频

## 下一步

1. 先上传代码并启动基础服务
2. 测试不需要API密钥的功能
3. 如果需要AI功能，再配置API密钥

## 获取帮助

如果遇到问题：
1. 运行诊断工具：`scripts\deploy\diagnose_deploy_issue.bat`
2. 查看详细日志
3. 检查服务器状态：`scripts\deploy\check_status.bat`