#!/bin/bash
set -e

echo "========================================"
echo "升级Python并重新部署"
echo "========================================"
echo ""

# 检测系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    echo "系统类型: $OS"
else
    echo "⚠️  无法检测系统类型"
    OS="unknown"
fi

# 检测包管理器
PKG_MANAGER=""
if command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
    echo "包管理器: apt"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "包管理器: yum"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    echo "包管理器: dnf"
else
    echo "❌ 未找到包管理器"
    exit 1
fi
echo ""

# 步骤1: 升级Python
echo "步骤 1/5: 升级Python到3.10..."

if [ "$PKG_MANAGER" = "apt" ]; then
    echo "使用apt安装Python 3.10..."
    apt update
    apt install -y software-properties-common
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
elif [ "$PKG_MANAGER" = "yum" ]; then
    echo "使用yum安装Python 3.10..."
    yum install -y https://repo.ius.io/ius-release-el7.rpm || true
    yum install -y python310 python310-devel python310-pip
elif [ "$PKG_MANAGER" = "dnf" ]; then
    echo "使用dnf安装Python 3.10..."
    dnf install -y python3.10 python3.10-devel python3.10-pip
fi

# 验证Python 3.10安装
if command -v python3.10 &> /dev/null; then
    echo "✓ Python 3.10安装成功"
    python3.10 --version
else
    echo "❌ Python 3.10安装失败"
    echo "尝试使用系统默认Python..."
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        python3 --version
    else
        echo "❌ 系统上没有可用的Python"
        exit 1
    fi
fi
PYTHON_CMD="python3.10"
echo ""

# 步骤2: 清理旧的虚拟环境
echo "步骤 2/5: 清理旧的虚拟环境..."
cd /home/novelapp/novel-system
if [ -d venv ]; then
    echo "删除旧的虚拟环境..."
    rm -rf venv
    echo "✓ 旧虚拟环境已删除"
fi
echo ""

# 步骤3: 创建新的虚拟环境
echo "步骤 3/5: 创建新的虚拟环境..."
$PYTHON_CMD -m venv venv
echo "✓ 虚拟环境创建完成"
source venv/bin/activate
echo ""

# 步骤4: 安装依赖
echo "步骤 4/5: 安装所有依赖..."
echo "升级pip..."
pip install --upgrade pip -q

echo "安装基础依赖..."
pip install flask gunicorn eventlet -q

echo "安装项目依赖..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt -q || echo "⚠️  部分依赖安装失败，继续..."
fi

# 确保关键依赖都安装了
pip install requests flask-cors -q
echo "✓ 依赖安装完成"
echo ""

# 步骤5: 创建配置文件并测试
echo "步骤 5/5: 创建配置文件并测试..."
cat > .env << 'EOF'
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False
LOG_LEVEL=INFO
EOF
echo "✓ 配置文件创建完成"
echo ""

echo "测试应用导入..."
if python -c "from web.web_server_refactored import app; print('✓ 应用导入成功')" 2>&1; then
    echo ""
    echo "========================================"
    echo "✓ Python升级和部署完成！"
    echo "========================================"
    echo ""
    IP=$(hostname -I | awk '{print $1}')
    echo "Python版本: $($PYTHON_CMD --version)"
    echo ""
    echo "启动服务命令:"
    echo "  cd /home/novelapp/novel-system"
    echo "  source venv/bin/activate"
    echo "  gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app"
    echo ""
    echo "访问网站: http://$IP:5000"
    echo ""
else
    echo "❌ 应用导入失败"
    echo ""
    echo "查看详细错误："
    echo "  cd /home/novelapp/novel-system"
    echo "  source venv/bin/activate"
    echo "  python -c 'from web.web_server_refactored import app'"
    exit 1
fi