# 一键部署工具使用指南（带日志记录）

## 概述

这套部署工具提供了完整的代码同步和部署功能，支持详细的日志记录，方便追踪部署过程和排查问题。

## 新增文件

1. **一键部署_with_logs.bat** - Windows端一键部署脚本
2. **server_deploy_with_logging.sh** - 服务器端部署脚本
3. **start_with_logging.sh** - 服务器端启动脚本
4. **view_server_logs.bat** - 日志查看工具

## 使用方法

### 1. 一键部署（推荐）

双击运行 `scripts/deploy/一键部署_with_logs.bat`

脚本会自动完成以下步骤：
- ✅ 创建压缩包（排除不必要的文件）
- ✅ 上传到服务器
- ✅ 服务器端部署
- ✅ 启动应用服务
- ✅ 记录详细日志

### 2. 查看服务器日志

双击运行 `scripts/deploy/view_server_logs.bat`

提供以下选项：
1. 应用主日志 (application.log) - 推荐首选
2. Gunicorn 日志 (gunicorn.log)
3. 访问日志 (access.log)
4. 错误日志 (error.log)
5. 所有日志（最新100行）
6. 实时监控应用日志
7. 实时监控Gunicorn日志
8. 列出所有日志文件

## 日志文件说明

### 本地部署日志

位置：`scripts/deploy/deploy_logs/`

文件命名：`deploy_YYYYMMDD_HHMMSS.log`

包含内容：
- SSH连接状态
- 压缩包创建过程
- 上传进度
- 服务器端部署输出
- 服务启动状态

### 服务器端日志

位置：`/home/novelapp/novel-system/logs/`

日志文件：
- **application.log** - 应用主日志（部署过程、启动信息）
- **gunicorn.log** - Gunicorn服务器日志
- **access.log** - HTTP访问日志
- **error.log** - 错误日志

## 手动操作命令

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

### 重启服务

```bash
# 进入项目目录
cd /home/novelapp/novel-system

# 激活虚拟环境
source venv/bin/activate

# 停止旧服务
lsof -ti:5000 | xargs kill -9

# 启动服务
bash /tmp/start_with_logging.sh
```

### 检查服务状态

```bash
# 检查端口是否被占用
lsof -ti:5000

# 查看进程
ps aux | grep gunicorn

# 查看最近的日志
tail -100 /home/novelapp/novel-system/logs/application.log
```

## 故障排查

### 问题1：SSH连接失败

检查私钥权限：
```bash
icacls "d:\work6.05\xsdm.pem" /inheritance:r
icacls "d:\work6.05\xsdm.pem" /grant:r "%USERNAME%:F"
```

### 问题2：服务启动失败

1. 查看错误日志：
```bash
tail -100 /home/novelapp/novel-system/logs/error.log
```

2. 查看Gunicorn日志：
```bash
tail -100 /home/novelapp/novel-system/logs/gunicorn.log
```

3. 手动测试启动：
```bash
cd /home/novelapp/novel-system
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.wsgi:app
```

### 问题3：端口被占用

```bash
# 查看占用端口的进程
lsof -ti:5000

# 强制停止
lsof -ti:5000 | xargs kill -9
```

### 问题4：依赖安装失败

```bash
cd /home/novelapp/novel-system
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 服务器配置

- IP: 8.163.37.124
- 用户: root
- 端口: 5000
- 项目目录: /home/novelapp/novel-system
- 日志目录: /home/novelapp/novel-system/logs/

## 访问地址

- 本地测试: http://localhost:5000
- 服务器: http://8.163.37.124:5000

## 注意事项

1. 首次部署需要较长时间安装依赖
2. 确保私钥文件路径正确
3. 确保服务器安全组已开放5000端口
4. 定期查看日志文件大小，必要时进行清理
5. 建议保留最近7天的日志，删除旧日志

## 日志清理命令

```bash
# 清理7天前的日志
find /home/novelapp/novel-system/logs/ -name "*.log" -mtime +7 -delete

# 或者压缩旧日志
find /home/novelapp/novel-system/logs/ -name "*.log" -mtime +7 -gzip
```

## 快速命令参考

```bash
# 快速查看应用日志
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124 "tail -50 /home/novelapp/novel-system/logs/application.log"

# 快速重启服务
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124 "cd /home/novelapp/novel-system && source venv/bin/activate && lsof -ti:5000 | xargs kill -9 2>/dev/null; nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --access-logfile logs/access.log --error-logfile logs/error.log web.wsgi:app > logs/gunicorn.log 2>&1 &"

# 检查服务状态
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124 "lsof -ti:5000 && echo '服务运行中' || echo '服务未运行'"
```

## 更新日志

- 2025-01-11: 创建带日志记录的部署工具
- 支持本地部署日志记录
- 支持服务器端多日志文件记录
- 添加便捷的日志查看工具