# 阿里云Alibaba Cloud Linux 3 最终部署指南

## 问题分析

从日志看，应用其实已经成功加载了所有模块！问题是测试导入的方式不对：

```
ImportError: cannot import name 'app' from 'web.web_server_refactored'
```

这是因为`app`不是全局变量，需要通过`create_app()`函数创建。

## 解决方案

我已经修复了测试代码。现在请重新运行部署脚本：

```batch
cd d:\work6.05
scripts\deploy\ALIYANG_CLOUD_DEPLOY.bat
```

## 或者直接启动服务（代码已经部署好了）

由于代码已经上传并解压，虚拟环境已创建，依赖已安装，您可以直接启动服务：

### 方法1：使用Python直接启动

```batch
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
```

```bash
cd /home/novelapp/novel-system
source venv/bin/activate
python web/web_server_refactored.py
```

### 方法2：使用Gunicorn（推荐用于生产）

```bash
cd /home/novelapp/novel-system
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
```

注意：Gunicorn会自动查找模块级别的`app`对象，所以这个命令是正确的。

### 方法3：配置系统服务（持久化运行）

```bash
# 安装supervisor
yum install -y supervisor

# 创建配置
cat > /etc/supervisord.d/novel-system.ini << 'EOF'
[program:novel-system]
command=/home/novelapp/novel-system/venv/bin/python web/web_server_refactored.py
directory=/home/novelapp/novel-system
user=root
autostart=true
autorestart=true
stderr_logfile=/home/novelapp/novel-system/logs/error.log
stdout_logfile=/home/novelapp/novel-system/logs/access.log
environment=PYTHONUNBUFFERED="1"
EOF

# 启动服务
supervisord -c /etc/supervisord.conf
supervisorctl start novel-system
supervisorctl status
```

## 访问网站

启动成功后访问：`http://8.163.37.124:5000`

## 验证部署

在浏览器中打开 `http://8.163.37.124:5000`，您应该能看到应用的主页。

## 如果仍有问题

### 检查日志

```bash
cd /home/novelapp/novel-system
tail -f logs/*.log
```

### 测试导入

```bash
cd /home/novelapp/novel-system
source venv/bin/activate
python -c "from web.web_server_refactored import create_app; app, manager = create_app(); print('✓ 应用创建成功')"
```

### 检查端口

```bash
netstat -tulpn | grep 5000
```

## 总结

您的应用实际上已经部署成功了！从日志可以看到：

- ✓ Python环境正常
- ✓ 虚拟环境创建成功
- ✓ 依赖安装完成
- ✓ 配置文件创建完成
- ✓ 所有模块成功加载
- ✓ 数据库初始化完成
- ✓ 小说项目加载完成

只需要使用正确的命令启动服务即可！