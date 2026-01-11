# 快速开始 - 带日志记录的部署工具

## ⚠️ 首次使用必读

**如果这是你第一次使用日志功能，必须先运行初始化脚本：**

```bash
# 双击运行
scripts/deploy/init_logs.bat
```

这将：
- ✅ 在服务器上创建日志目录
- ✅ 初始化所有日志文件
- ✅ 检查服务运行状态

**初始化完成后，就可以正常使用下面的部署工具了。**

---

## 🚀 三种部署方式

### 1. 完整部署（首次部署或大更新）

**文件**: `scripts/deploy/一键部署_with_logs.bat`

**适用场景**:
- 首次部署到服务器
- 代码有较大改动
- 需要重新安装依赖

**执行步骤**:
1. 双击运行 `scripts/deploy/一键部署_with_logs.bat`
2. 等待完成（首次部署需要5-10分钟）
3. 访问 http://8.163.37.124:5000

**日志位置**:
- 本地: `scripts/deploy/deploy_logs/deploy_YYYYMMDD_HHMMSS.log`
- 服务器: `/home/novelapp/novel-system/logs/`

---

### 2. 快速重启（代码小改动）

**文件**: `scripts/deploy/quick_restart_with_logs.bat`

**适用场景**:
- 代码有小改动
- 只需重启服务即可
- 需要快速部署

**执行步骤**:
1. 双击运行 `scripts/deploy/quick_restart_with_logs.bat`
2. 等待完成（约30秒）
3. 刷新浏览器

**日志位置**:
- 本地: `scripts/deploy/deploy_logs/restart_YYYYMMDD_HHMMSS.log`

---

### 3. 查看服务器日志

**文件**: `scripts/deploy/view_server_logs.bat`

**适用场景**:
- 检查服务运行状态
- 排查错误问题
- 查看访问记录

**执行步骤**:
1. 双击运行 `scripts/deploy/view_server_logs.bat`
2. 选择要查看的日志类型：
   - 1. 应用主日志（推荐）
   - 2. Gunicorn日志
   - 3. 访问日志
   - 4. 错误日志
   - 5. 所有日志
   - 6. 实时监控应用日志
   - 7. 实时监控Gunicorn日志
   - 8. 列出所有日志文件

---

## 📋 服务器端日志文件说明

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
lsof -ti:5000 && echo "服务运行中" || echo "服务未运行"
```

---

## 📊 工作流程建议

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

## ❗ 故障排查

### 问题1: 服务无法访问

**检查步骤**:
1. 运行 `view_server_logs.bat` 选择 "4. 错误日志"
2. 运行 `view_server_logs.bat` 选择 "6. 实时监控应用日志"
3. 检查端口是否占用: `lsof -ti:5000`

**解决方法**:
```bash
# 手动重启
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
cd /home/novelapp/novel-system
source venv/bin/activate
lsof -ti:5000 | xargs kill -9
bash /tmp/start_with_logging.sh
```

### 问题2: 部署失败

**检查步骤**:
1. 查看本地日志: `scripts/deploy/deploy_logs/deploy_*.log`
2. 连接服务器检查: `ssh -i d:\work6.05\xsdm.pem root@8.163.37.124`
3. 查看服务器日志: `tail -100 /tmp/deploy.log`

### 问题3: 代码未生效

**检查步骤**:
1. 确认使用的是 `quick_restart_with_logs.bat`（不是完整部署）
2. 检查 rsync 是否安装
3. 手动验证文件是否同步

---

## 📞 获取帮助

如遇到问题：
1. 查看详细文档: `scripts/deploy/DEPLOYMENT_WITH_LOGS_GUIDE.md`
2. 检查日志文件
3. 使用 `view_server_logs.bat` 查看实时状态

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