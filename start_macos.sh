#!/bin/bash
# macOS 启动脚本
# 使用方法: ./start_macos.sh

echo "=========================================="
echo "🍎 NovelPublisher macOS 启动脚本"
echo "=========================================="
echo ""

# 检查 Python
if command -v python3.11 &> /dev/null; then
    PYTHON=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON=python3
    # 检查版本
    PY_VERSION=$($PYTHON --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ "$PY_VERSION" != "3.11" ]]; then
        echo "⚠️  警告: 当前 Python 版本为 $PY_VERSION，建议使用 3.11"
        read -p "是否继续? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo "❌ 未找到 Python，请先安装 Python 3.11"
    echo "安装方式:"
    echo "  1. Homebrew: brew install python@3.11"
    echo "  2. 官网下载: https://www.python.org/downloads/macos/"
    exit 1
fi

echo "✅ 使用 Python: $PYTHON"
echo ""

# 检查依赖
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    $PYTHON -m venv venv
fi

echo "📦 激活虚拟环境..."
source venv/bin/activate

echo "📦 检查依赖..."
pip install -q -r requirements.txt

echo ""
echo "🚀 启动服务..."
echo "服务将在 http://localhost:5000 运行"
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

# 启动服务
$PYTHON start.py
