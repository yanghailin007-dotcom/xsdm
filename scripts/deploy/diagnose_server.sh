#!/bin/bash
echo "========================================"
echo "服务器环境诊断"
echo "========================================"
echo ""

echo "=== 系统信息 ==="
cat /etc/os-release 2>/dev/null || cat /etc/issue
echo ""

echo "=== Python版本 ==="
echo "检查python命令..."
which python python3 python3.10 python3.8 python3.9 2>/dev/null
echo ""

echo "Python版本:"
python3 --version 2>&1 || echo "python3 未找到"
python3.10 --version 2>&1 || echo "python3.10 未找到"
python3.8 --version 2>&1 || echo "python3.8 未找到"
python3.9 --version 2>&1 || echo "python3.9 未找到"
echo ""

echo "=== 包管理器 ==="
echo "检查apt..."
which apt
apt --version 2>&1 || echo "apt 未安装"
echo ""

echo "检查yum..."
which yum
yum --version 2>&1 || echo "yum 未安装"
echo ""

echo "检查dnf..."
which dnf
dnf --version 2>&1 || echo "dnf 未安装"
echo ""

echo "=== 磁盘空间 ==="
df -h
echo ""

echo "=== 内存 ==="
free -h
echo ""

echo "=== 用户权限 ==="
whoami
groups
echo ""

echo "=== 已上传的文件 ==="
ls -lh /tmp/novel_system_*.tar.gz 2>/dev/null || echo "未找到压缩包"
echo ""

echo "=== 项目目录 ==="
if [ -d /home/novelapp/novel-system ]; then
    echo "项目目录存在"
    ls -la /home/novelapp/novel-system/ | head -20
else
    echo "项目目录不存在"
fi
echo ""

echo "=== 推荐操作 ==="
PYTHON_CMD=""
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
elif command -v python3.8 &> /dev/null; then
    PYTHON_CMD="python3.8"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

if [ -n "$PYTHON_CMD" ]; then
    echo "✓ 找到Python: $PYTHON_CMD"
    $PYTHON_CMD --version
    echo ""
    echo "建议使用现有Python创建虚拟环境:"
    echo "  cd /home/novelapp/novel-system"
    echo "  $PYTHON_CMD -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install flask gunicorn eventlet"
else
    echo "❌ 未找到Python"
    echo ""
    echo "需要安装Python 3.8+"
    echo ""
    if command -v apt &> /dev/null; then
        echo "Ubuntu/Debian系统:"
        echo "  apt update"
        echo "  apt install -y python3 python3-pip python3-venv"
    elif command -v yum &> /dev/null; then
        echo "CentOS/RHEL系统:"
        echo "  yum install -y python3 python3-pip"
    elif command -v dnf &> /dev/null; then
        echo "Fedora系统:"
        echo "  dnf install -y python3 python3-pip"
    fi
fi