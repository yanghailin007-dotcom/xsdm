# 稳定部署系统使用指南

## 📋 概述

这是一个稳定可靠的部署解决方案，解决了端口占用检测不准确的问题，提供一键部署和快速重启功能。

## 🎯 主要特性

- ✅ **可靠的端口清理**：使用多种方法检测和清理占用端口的进程
- ✅ **一键部署**：自动同步文件、上传脚本、执行部署
- ✅ **快速重启**：无需重新上传文件，直接重启服务
- ✅ **配置管理**：统一管理服务器信息和路径配置
- ✅ **详细日志**：完整的部署过程日志和错误诊断

## 📁 文件结构

```
scripts/deploy/
├── deploy_config.ini          # 配置文件
├── server_deploy_stable.sh    # 服务器端部署脚本
├── deploy_stable.bat          # Windows一键部署脚本
├── restart_server.bat         # 快速重启脚本
└── STABLE_DEPLOYMENT_GUIDE.md # 本文档
```

## 🔧 配置说明

### 1. 编辑配置文件

编辑 `scripts/deploy/deploy_config.ini`:

```ini
[server]
ip = 8.163.37.124              # 服务器IP
port = 22                      # SSH端口
user = root                    # SSH用户
key_path = d:\work6.05\xsdm.pem # 私钥文件路径
remote_project_path = /home/novelapp/novel-system

[paths]
local_root = d:\work6.05
sync_dirs = src,web,scripts,config
sync_files = requirements.txt,web/wsgi.py,scripts/start_app.py

[logs]
access_log = logs/access.log
error_log = logs/error.log
gunicorn_log = logs/gunicorn.log
```

## 🚀 使用方法

### 首次部署

1. **确保私钥文件存在**：
   - 私钥文件路径：`d:\work6.05\xsdm.pem`
   - 如果没有，请从阿里云控制台下载

2. **运行一键部署脚本**：
   ```batch
   scripts\deploy\deploy_stable.bat
   ```

3. **脚本执行步骤**：
   - 步骤 1/4: 上传服务器部署脚本
   - 步骤 2/4: 同步核心文件（使用rsync或scp）
   - 步骤 3/4: 执行服务器部署
   - 步骤 4/4: 验证部署结果

4. **验证部署**：
   - 访问：http://8.163.37.124:5000
   - 查看日志（如需要）

### 快速重启（代码已修改后）

当你修改了代码并需要重启服务器时：

1. **先同步文件**（可选）：
   ```batch
   scripts\sync_to_server.bat
   ```

2. **运行快速重启**：
   ```batch
   scripts\deploy\restart_server.bat
   ```

快速重启会：
- 清理端口5000
- 终止旧的gunicorn进程
- 启动新的gunicorn服务
- 验证服务状态

### 手动部署（高级）

如果自动脚本失败，可以手动执行：

```batch
REM 1. 上传部署脚本
scp -i "d:\work6.05\xsdm.pem" -P 22 ^
    scripts\deploy\server_deploy_stable.sh ^
    root@8.163.37.124:/home/novelapp/novel-system/scripts/deploy/

REM 2. 连接服务器并执行
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
cd /home/novelapp/novel-system
chmod +x scripts/deploy/server_deploy_stable.sh
bash scripts/deploy/server_deploy_stable.sh
```

## 🔍 故障排查

### 问题1: 端口仍被占用

**症状**: 部署时报 "Address already in use"

**解决方案**:
```bash
# SSH连接到服务器
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124

# 手动清理端口
lsof -ti:5000 | xargs kill -9

# 或使用多种方法
fuser -k 5000/tcp
pkill -9 gunicorn
```

### 问题2: 私钥权限错误

**症状**: "WARNING: UNPROTECTED PRIVATE KEY FILE"

**解决方案**:
- Windows脚本会自动修复权限
- 如果仍然失败，手动运行：
  ```batch
  icacls "d:\work6.05\xsdm.pem" /inheritance:r
  icacls "d:\work6.05\xsdm.pem" /grant:r "%USERNAME%:F"
  ```

### 问题3: 文件同步失败

**症状**: rsync或scp命令失败

**解决方案**:
1. 检查网络连接
2. 检查私钥文件是否存在
3. 检查服务器IP和用户是否正确
4. 查看详细错误信息

### 问题4: 服务启动失败

**症状**: 部署成功但无法访问网站

**解决方案**:
```bash
# 查看日志
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
tail -f /home/novelapp/novel-system/logs/gunicorn.log
tail -f /home/novelapp/novel-system/logs/error.log

# 检查进程
ps aux | grep gunicorn

# 检查端口
netstat -tulpn | grep 5000
```

## 📊 服务器端部署脚本功能

[`server_deploy_stable.sh`](server_deploy_stable.sh) 提供以下功能：

1. **多重端口清理**：
   - 使用 lsof 检测
   - 使用 fuser 检测
   - 使用 netstat 检测
   - 使用 ss 检测
   - 使用 pgrep 检测gunicorn进程

2. **优雅进程终止**：
   - 先发送 SIGTERM (kill -15)
   - 等待1秒
   - 如果进程仍存在，发送 SIGKILL (kill -9)

3. **服务验证**：
   - 检查PID文件
   - 检查进程状态
   - 检查端口监听
   - 检查HTTP响应

4. **详细日志**：
   - 彩色输出（蓝/绿/黄/红）
   - 分步骤显示
   - 错误诊断信息

## 🎨 颜色输出说明

服务器端脚本使用颜色输出：
- 🔵 蓝色 (ℹ️): 信息提示
- 🟢 绿色 (✓): 成功操作
- 🟡 黄色 (⚠️): 警告信息
- 🔴 红色 (❌): 错误信息

## 📝 最佳实践

1. **首次部署前**：
   - 确认配置文件正确
   - 确认私钥文件存在
   - 确认服务器可访问

2. **日常开发**：
   - 修改代码后使用 `restart_server.bat`
   - 避免频繁上传大文件

3. **生产环境**：
   - 使用 `deploy_stable.bat` 完整部署
   - 部署后验证服务状态
   - 保存部署日志

4. **故障处理**：
   - 优先查看服务器日志
   - 检查端口占用情况
   - 验证文件同步状态

## 🔗 相关文档

- [`deploy_config.ini`](deploy_config.ini) - 配置文件详解
- [`server_deploy_stable.sh`](server_deploy_stable.sh) - 服务器端脚本详解
- [`deploy_stable.bat`](deploy_stable.bat) - Windows部署脚本详解
- [`restart_server.bat`](restart_server.bat) - 快速重启脚本详解

## 📞 获取帮助

如遇到问题：
1. 查看本文档的故障排查部分
2. 查看服务器日志文件
3. 检查配置文件是否正确
4. 确认网络连接正常

## 📈 版本历史

- **v1.0** (2026-01-10)
  - 初始版本
  - 多重端口清理机制
  - 一键部署功能
  - 快速重启功能
  - 配置文件管理