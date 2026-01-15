# 一键部署工具

## 快速开始

### 1. 配置服务器信息

编辑 `deploy.bat`，修改服务器配置：

```batch
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem
```

### 2. 运行部署脚本

双击 `deploy.bat` 或在命令行运行：

```cmd
cd d:\work6.05
scripts\deploy\deploy.bat
```

## 部署流程

脚本会自动完成：

1. ✅ 创建部署压缩包（约 677MB）
2. ✅ 上传到服务器
3. ✅ 解压并配置环境
4. ✅ 安装 Python 依赖
5. ✅ 启动 Gunicorn 服务
6. ✅ 测试验证

## 服务管理

```bash
# 查看服务状态
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "pgrep -f gunicorn"

# 停止服务
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "pkill -f gunicorn"

# 查看日志
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "tail -f /home/novelapp/novel-system/logs/error.log"

# 重启服务
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "cd /home/novelapp/novel-system && source venv/bin/activate && gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 --daemon web.wsgi:app"
```

## 系统要求

### 本地环境
- Windows 10/11
- Git for Windows
- SSH 客户端

### 服务器环境
- Ubuntu 20.04/22.04/24.04
- Python 3.10+（会自动安装）
- 足够的磁盘空间（建议 10GB+）

## 故障排查

### SSH 连接失败
检查私钥文件路径和服务器 IP 是否正确

### 压缩包创建失败
确保 Git Bash 已安装在 `C:\Program Files\Git\bin\bash.exe`

### 服务启动失败
连接到服务器查看错误日志：
```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "tail -50 /home/novelapp/novel-system/logs/error.log"
```

## 文件说明

- **`deploy.bat`** - Windows 主部署脚本
- **`server_deploy.sh`** - Linux 服务器端脚本
- **`README.md`** - 本说明文档
