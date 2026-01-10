@echo off
chcp 65001 >nul
echo ========================================
echo    服务器状态检查工具
echo ========================================
echo.

set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

if not exist "%KEY_PATH%" (
    echo ❌ 私钥文件不存在: %KEY_PATH%
    pause
    exit /b 1
)

echo 正在连接服务器...
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -s" << 'ENDSSH'
echo "========================================"
echo "服务器基本信息"
echo "========================================"
echo ""
echo "=== 系统信息 ==="
uname -a
echo ""
echo "=== 磁盘空间 ==="
df -h
echo ""
echo "=== 内存使用 ==="
free -h
echo ""
echo "=== Python版本 ==="
python3 --version 2>&1 || echo "Python3 未安装"
python3.10 --version 2>&1 || echo "Python 3.10 未安装"
echo ""
echo "=== 已上传的文件 ==="
ls -lh /tmp/novel_system_*.tar.gz 2>/dev/null || echo "未找到上传的压缩包"
echo ""
echo "=== 项目目录 ==="
if [ -d /home/novelapp/novel-system ]; then
    echo "✓ 项目目录存在: /home/novelapp/novel-system"
    echo ""
    echo "=== 项目文件 ==="
    ls -la /home/novelapp/novel-system/ | head -20
    echo ""
    echo "=== 虚拟环境 ==="
    if [ -d /home/novelapp/novel-system/venv ]; then
        echo "✓ 虚拟环境存在"
        /home/novelapp/novel-system/venv/bin/python --version 2>&1 || echo "虚拟环境Python未正确安装"
    else
        echo "✗ 虚拟环境不存在"
    fi
    echo ""
    echo "=== 运行的服务 ==="
    ps aux | grep -E 'gunicorn|python.*web_server' | grep -v grep || echo "未找到运行的应用服务"
    echo ""
    echo "=== Supervisor状态 ==="
    if command -v supervisorctl &> /dev/null; then
        supervisorctl status 2>&1 || echo "Supervisor未配置"
    else
        echo "Supervisor未安装"
    fi
    echo ""
    echo "=== Nginx状态 ==="
    if command -v nginx &> /dev/null; then
        systemctl status nginx --no-pager -l | grep -E "Active:|Loaded:" || echo "Nginx未运行"
    else
        echo "Nginx未安装"
    fi
    echo ""
    echo "=== 监听端口 ==="
    netstat -tulpn 2>/dev/null | grep -E '5000|80|443' || ss -tulpn 2>/dev/null | grep -E '5000|80|443' || echo "无法查看端口信息"
else
    echo "✗ 项目目录不存在: /home/novelapp/novel-system"
fi
echo ""
echo "========================================"
ENDSSH

echo.
pause