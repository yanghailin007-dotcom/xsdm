# 服务器部署工具 - 完整指南

## 📋 目录

1. [快速开始](#快速开始)
2. [首次使用](#首次使用)
3. [部署工具说明](#部署工具说明)
4. [日志系统](#日志系统)
5. [故障排查](#故障排查)
6. [常用命令](#常用命令)

---

## 🚀 快速开始

### 第一步：首次使用 - 初始化日志系统

**如果你是第一次使用日志功能，必须先运行：**

```bash
# 双击运行
scripts/deploy/init_logs.bat
```

这将：
- ✅ 在服务器上创建日志目录 `/home/novelapp/novel-system/logs/`
- ✅ 初始化所有日志文件
- ✅ 检查服务运行状态

---

## 🎯 部署工具说明

### 1. 完整部署（首次或大更新）

**文件**: [`一键部署_with_logs.bat`](一键部署_with_logs.bat)

**适用场景**:
- 首次部署到服务器
- 代码有较大改动
- 需要重新安装依赖

**执行步骤**:
1. 双击运行脚本
2. 等待完成（首次5-10分钟）
3. 访问 http://8.163.37.124:5000

**本地日志**: `deploy_logs/deploy_YYYYMMDD_HHMMSS.log`

---

### 2. 快速重启（代码小改动）

**文件**: [`quick_restart_with_logs.bat`](quick_restart_with_logs.bat)

**适用场景**:
- 代码有小改动
- 只需重启服务
- 快速部署

**执行步骤**:
1. 双击运行脚本
2. 等待完成（约30秒）
3. 刷新浏览器

**本地日志**: `deploy_logs/restart_YYYYMMDD_HHMMSS.log`

---

### 3. 查看服务器日志

**文件**: [`view_server_logs.bat`](view_server_logs.bat)

**功能**:
1. 应用主日志 (application.log) - 推荐首选
2. Gunicorn 日志 (gunicorn.log)
3. 访问日志 (access.log)
4. 错误日志 (error.log)
5. 所有日志（最新100行）
6. 实时监控应用日志
7. 实时监控Gunicorn日志
8. 列出所有日志文件

---

## 📊 日志系统

### 本地日志文件

位置: `scripts/deploy/deploy_logs/`

- `deploy_*.log` - 完整部署日志
- `restart_*.log` - 快速重启日志

### 服务器日志文件

位置: `/home/novelapp/novel-system/logs/`

| 日志文件 | 说明 | 用途 |
|---------|------|------|
| `application.log` | 应用主日志 | 查看部署过程、启动信息 |
| `gunicorn.log` | Gunicorn日志 | 查看服务器运行状态 |
| `access.log` | 访问日志 | 查看HTTP请求记录 |
| `error.log` | 错误日志 | 查看错误和异常信息 |

---

## 🔧 常用命令

### 连接到服务器

```bash
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
```

### 查看实时日志

```bash
# 应用日志
tail -f /home/novelapp/novel-system/logs/application.log

# Gunicorn日志
tail -f /home/novelapp/novel-system/logs/gunicorn.log

# 访问日志
tail -f /home/novelapp/novel-system/logs/access.log

# 错误日志
tail -f /home/novelapp/novel-system/logs/error.log
```

### 查看最近的日志

```bash
# 最近100行
tail -100 /home/novelapp/novel-system/logs/application.log

# 最近50行
tail -50 /home/novelapp/novel-system/logs/gunicorn.log
```

### 重启服务

```bash
cd /home/novelapp/novel-system
source venv/bin/activate
lsof -ti:5000 | xargs kill -9
nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  web.wsgi:app > logs/gunicorn.log 2>&1 &
```

### 检查服务状态

```bash
# 检查端口
lsof -ti:5000 && echo "服务运行中" || echo "服务未运行"

# 查看进程
ps aux | grep gunicorn

# 查看最近的应用日志
tail -50 /home/novelapp/novel-system/logs/application.log
```

### 清理旧日志

```bash
# 删除7天前的日志
find /home/novelapp/novel-system/logs/ -name "*.log" -mtime +7 -delete

# 压缩旧日志
find /home/novelapp/novel-system/logs/ -name "*.log" -mtime +7 -gzip
```

---

## ❗ 故障排查

### 问题1: 日志文件不存在

**症状**: `tail: cannot open '/home/novelapp/novel-system/logs/application.log' for reading: No such file or directory`

**原因**: 服务器上还没有初始化日志系统

**解决方案**:
```bash
# 运行初始化脚本
scripts/deploy/init_logs.bat
```

---

### 问题2: 服务无法访问

**检查步骤**:
1. 运行 `view_server_logs.bat` 选择 "4. 错误日志"
2. 运行 `view_server_logs.bat` 选择 "6. 实时监控应用日志"
3. 检查端口是否占用

**解决方法**:
```bash
# 手动重启
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
cd /home/novelapp/novel-system
source venv/bin/activate
lsof -ti:5000 | xargs kill -9
bash /tmp/start_with_logging.sh
```

---

### 问题3: 部署失败

**检查步骤**:
1. 查看本地日志: `scripts/deploy/deploy_logs/deploy_*.log`
2. 连接服务器检查
3. 查看服务器日志: `tail -100 /tmp/deploy.log`

---

### 问题4: 代码未生效

**检查步骤**:
1. 确认使用的是 `quick_restart_with_logs.bat`
2. 检查 rsync 是否安装
3. 手动验证文件是否同步

---

## 📋 工作流程建议

### 日常开发流程

1. **本地开发** → 在本地修改代码
2. **快速重启** → 运行 `quick_restart_with_logs.bat`
3. **测试验证** → 访问 http://8.163.37.124:5000
4. **查看日志** → 如有问题，运行 `view_server_logs.bat`

### 重大更新流程

1. **本地开发** → 完成功能开发
2. **完整部署** → 运行 `一键部署_with_logs.bat`
3. **测试验证** → 全面测试功能
4. **监控日志** → 使用 `view_server_logs.bat` 监控

---

## 🎯 最佳实践

1. **定期清理日志**: 避免日志文件过大
   ```bash
   find /home/novelapp/novel-system/logs/ -name "*.log" -mtime +7 -delete
   ```

2. **备份重要数据**: 定期备份数据库和配置

3. **监控服务状态**: 使用 `view_server_logs.bat` 实时监控

4. **保持日志简洁**: 删除不必要的调试日志

5. **定期更新依赖**: 每月运行一次完整部署

---

## 📞 获取帮助

如遇到问题：
1. 查看详细文档: [`DEPLOYMENT_WITH_LOGS_GUIDE.md`](DEPLOYMENT_WITH_LOGS_GUIDE.md)
2. 查看快速指南: [`QUICK_START_WITH_LOGS.md`](QUICK_START_WITH_LOGS.md)
3. 检查日志文件
4. 使用 `view_server_logs.bat` 查看实时状态

---

## 📦 文件清单

### 部署脚本
- `一键部署_with_logs.bat` - 完整部署
- `quick_restart_with_logs.bat` - 快速重启
- `init_logs.bat` - 初始化日志系统

### 服务器脚本
- `server_deploy_with_logging.sh` - 服务器端部署
- `start_with_logging.sh` - 服务器端启动
- `init_logs_on_server.sh` - 服务器端日志初始化

### 工具
- `view_server_logs.bat` - 日志查看工具

### 文档
- `README_LOGGING_DEPLOYMENT.md` - 本文档
- `DEPLOYMENT_WITH_LOGS_GUIDE.md` - 详细指南
- `QUICK_START_WITH_LOGS.md` - 快速开始

---

## 🔗 相关链接

- 服务器IP: 8.163.37.124
- 端口: 5000
- 项目目录: /home/novelapp/novel-system
- 日志目录: /home/novelapp/novel-system/logs/

---

**版本**: 1.0.0  
**更新日期**: 2025-01-11