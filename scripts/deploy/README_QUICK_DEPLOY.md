# 快速部署指南

这个指南帮助您快速将应用部署到服务器，**不需要配置API密钥**。

## 部署流程概述

```
本地Windows → 上传代码 → 服务器解压 → 安装依赖 → 启动服务
```

## 第一步：诊断环境

在开始之前，运行诊断工具检查您的环境：

```batch
cd d:\work6.05
scripts\deploy\diagnose_deploy_issue.bat
```

这个工具会检查：
- ✓ SSH/SCP 工具是否安装
- ✓ 私钥文件是否存在
- ✓ SSH连接是否正常
- ✓ 压缩和上传功能是否正常

**如果所有检查通过，继续下一步。**

## 第二步：上传代码

运行简化上传工具：

```batch
cd d:\work6.05
scripts\deploy\simple_upload.bat
```

这会：
1. 创建代码压缩包（排除不必要的文件）
2. 上传到服务器 `/tmp/` 目录
3. 显示上传结果

**预期输出：**
```
✓ 压缩包创建成功: novel_system_20250110_143025.tar.gz
✓ 上传成功！
文件已上传到服务器: /tmp/novel_system_20250110_143025.tar.gz
```

## 第三步：连接服务器

使用以下命令连接到服务器：

```batch
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
```

## 第四步：在服务器上部署

连接成功后，运行服务器端部署脚本：

```bash
bash /home/novelapp/novel-system/scripts/deploy/server_deploy.sh
```

如果文件不存在，手动执行以下步骤：

```bash
# 1. 查找上传的压缩包
ls -lh /tmp/novel_system_*.tar.gz

# 2. 创建项目目录
mkdir -p /home/novelapp/novel-system
cd /home/novelapp/novel-system

# 3. 解压代码
tar -xzf /tmp/novel_system_*.tar.gz
rm /tmp/novel_system_*.tar.gz

# 4. 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate

# 5. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn eventlet flask

# 6. 创建环境文件（不需要API密钥）
cat > .env << 'EOF'
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False
LOG_LEVEL=INFO
EOF

# 7. 测试启动
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
```

## 第五步：访问应用

服务启动后，在浏览器访问：

```
http://8.163.37.124:5000
```

您应该能看到应用的主页。

## 第六步：配置系统服务（可选）

如果需要服务随系统启动，配置 supervisor：

```bash
# 安装supervisor
apt install -y supervisor

# 创建配置
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

## 可用功能（不需要API密钥）

部署成功后，以下功能立即可用：

- ✓ 项目管理
- ✓ 角色编辑
- ✓ 世界观查看
- ✓ 章节浏览
- ✓ 创意库管理
- ✓ 段落查看

需要API密钥的功能（可选配置）：

- ○ AI生成内容
- ○ AI生成图片
- ○ AI生成视频

## 故障排查

### 检查服务器状态

```batch
cd d:\work6.05
scripts\deploy\check_status.bat
```

### 常见问题

**问题 1: SSH连接失败**
```
❌ 检查：
- 私钥文件路径: d:\work6.05\xsdm.pem
- 服务器IP: 8.163.37.124
- 安全组是否开放22端口
```

**问题 2: 压缩包创建失败**
```
❌ 确保：
- Git for Windows 已安装
- 在正确的目录: d:\work6.05
```

**问题 3: 上传失败**
```
❌ 检查：
- 网络连接
- 服务器磁盘空间: df -h /tmp
```

**问题 4: Python模块导入失败**
```
❌ 解决：
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

## 工具清单

本地Windows工具：
- `diagnose_deploy_issue.bat` - 环境诊断
- `simple_upload.bat` - 代码上传
- `check_status.bat` - 状态检查

服务器端脚本：
- `server_deploy.sh` - 自动部署
- `setup_service.sh` - 配置服务

文档：
- `SIMPLE_DEPLOY_GUIDE.md` - 详细部署指南
- `README_QUICK_DEPLOY.md` - 本文档

## 下一步

1. ✅ 运行诊断工具
2. ✅ 上传代码
3. ✅ 在服务器上部署
4. ✅ 测试访问
5. ⬜ 如果需要AI功能，配置API密钥

## 获取帮助

如果遇到问题：
1. 运行诊断工具查看详细错误
2. 检查服务器状态
3. 查看详细部署指南：`SIMPLE_DEPLOY_GUIDE.md`
4. 查看服务器日志：`tail -f /home/novelapp/novel-system/logs/*.log`