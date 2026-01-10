# 部署问题解决方案

## 问题诊断

您遇到了 "步骤 1/5: 上传代码... ❌ 代码上传失败" 的错误。

## 解决方案

我已经创建了一套简化的部署工具，**不需要配置API密钥**即可部署和测试应用。

## 新增工具

### 1. 诊断工具
**文件**: `scripts/deploy/diagnose_deploy_issue.bat`

检查所有部署前提条件：
- SSH/SCP 工具安装
- 私钥文件存在性和权限
- SSH连接测试
- 压缩和上传功能测试

**使用方法**:
```batch
cd d:\work6.05
scripts\deploy\diagnose_deploy_issue.bat
```

### 2. 简化上传工具
**文件**: `scripts/deploy/simple_upload.bat`

简化版本的上传工具，专注于代码上传功能：
- 自动设置私钥权限
- 创建压缩包并上传
- 显示详细的错误信息

**使用方法**:
```batch
cd d:\work6.05
scripts\deploy\simple_upload.bat
```

### 3. 服务器状态检查
**文件**: `scripts/deploy/check_status.bat`

检查服务器上的部署状态：
- 系统信息
- Python版本
- 已上传的文件
- 项目目录状态
- 运行的服务

**使用方法**:
```batch
cd d:\work6.05
scripts\deploy\check_status.bat
```

### 4. 服务器端部署脚本
**文件**: `scripts/deploy/server_deploy.sh`

在服务器上自动完成部署：
- 解压代码
- 创建虚拟环境
- 安装依赖
- 创建配置文件（不需要API密钥）
- 测试应用导入

**使用方法**:
```bash
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
bash /home/novelapp/novel-system/scripts/deploy/server_deploy.sh
```

## 快速部署流程

### 第一步：诊断环境
```batch
cd d:\work6.05
scripts\deploy\diagnose_deploy_issue.bat
```

### 第二步：上传代码
```batch
cd d:\work6.05
scripts\deploy\simple_upload.bat
```

### 第三步：连接服务器
```batch
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
```

### 第四步：在服务器上部署
```bash
# 方案A：使用自动脚本（推荐）
bash scripts/deploy/server_deploy.sh

# 方案B：手动执行
mkdir -p /home/novelapp/novel-system
cd /home/novelapp/novel-system
tar -xzf /tmp/novel_system_*.tar.gz
rm /tmp/novel_system_*.tar.gz
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn eventlet flask
cat > .env << 'EOF'
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False
LOG_LEVEL=INFO
EOF
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
```

### 第五步：访问应用
在浏览器打开：`http://8.163.37.124:5000`

## 与原方案的区别

### 原方案（quick_start.bat）
- ❌ 一步完成所有操作
- ❌ 需要配置API密钥
- ❌ 错误难以诊断
- ❌ 无法单独测试各步骤

### 新方案
- ✅ 分步执行，每步可独立测试
- ✅ **不需要API密钥**
- ✅ 详细的错误信息
- ✅ 可以单独诊断每个步骤
- ✅ 提供状态检查工具

## 不需要API密钥的功能

以下功能可以在没有API密钥的情况下使用：
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

### 如果诊断失败
运行 `diagnose_deploy_issue.bat` 查看详细错误信息，它会告诉你：
- 哪个工具缺失
- 私钥文件路径是否正确
- SSH连接是否正常
- 具体是哪一步失败

### 如果上传失败
1. 检查网络连接
2. 运行 `check_status.bat` 查看服务器状态
3. 查看服务器磁盘空间：`df -h /tmp`

### 如果部署失败
1. 连接到服务器查看日志
2. 检查Python版本：`python3.10 --version`
3. 检查依赖安装：`source venv/bin/activate && pip list`

## 文档

- **快速部署指南**: `scripts/deploy/README_QUICK_DEPLOY.md`
- **详细部署指南**: `scripts/deploy/SIMPLE_DEPLOY_GUIDE.md`
- **本文档**: `scripts/deploy/DEPLOYMENT_FIX_SUMMARY.md`

## 下一步

1. 运行诊断工具确认环境正常
2. 使用简化上传工具上传代码
3. 在服务器上运行部署脚本
4. 测试不需要API密钥的功能
5. 如果需要AI功能，再配置API密钥

## 获取帮助

如果遇到问题：
1. 首先运行诊断工具
2. 查看详细的部署指南
3. 检查服务器状态
4. 查看错误日志