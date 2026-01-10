#!/bin/bash
set -e

echo "========================================"
echo "服务器端自动部署脚本"
echo "========================================"
echo ""

# 步骤1: 检查上传的压缩包
echo "步骤 1/6: 检查上传的压缩包..."
TAR_FILE=$(ls -t /tmp/novel_system_*.tar.gz 2>/dev/null | head -1)
if [ -z "$TAR_FILE" ]; then
    echo "❌ 未找到上传的压缩包"
    echo ""
    echo "请先在本地运行以下命令上传代码："
    echo "   cd d:\\work6.05"
    echo "   scripts\\deploy\\simple_upload.bat"
    echo ""
    echo "或者手动上传："
    echo "   scp -i xsdm.pem novel_system.tar.gz root@8.163.37.124:/tmp/"
    exit 1
fi
echo "✓ 找到压缩包: $TAR_FILE"
ls -lh "$TAR_FILE"
echo ""

# 步骤2: 创建项目目录
echo "步骤 2/6: 创建项目目录..."
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
echo "✓ 目录创建完成"
echo ""

# 步骤3: 解压代码
echo "步骤 3/6: 解压代码..."
cd /home/novelapp/novel-system
tar -xzf "$TAR_FILE"
echo "✓ 代码解压完成"
ls -la | head -20
echo ""

# 步骤4: 清理压缩包
echo "步骤 4/6: 清理临时文件..."
rm -f "$TAR_FILE"
echo "✓ 临时文件已清理"
echo ""

# 步骤5: 创建虚拟环境并安装依赖
echo "步骤 5/6: 创建虚拟环境并安装依赖..."
echo "   检查Python版本..."
python3.10 --version || {
    echo "❌ Python 3.10 未安装"
    echo "正在安装 Python 3.10..."
    apt update
    apt install -y software-properties-common
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
}

echo "   创建虚拟环境..."
python3.10 -m venv venv
echo "✓ 虚拟环境创建完成"

echo "   激活虚拟环境..."
source venv/bin/activate

echo "   升级pip..."
pip install --upgrade pip -q

echo "   安装基础依赖..."
pip install flask gunicorn eventlet -q

echo "   安装项目依赖..."
if [ -f requirements.txt ]; then
    echo "正在安装项目依赖..."
    pip install -r requirements.txt -q || echo "⚠️  部分依赖安装失败"
else
    echo "⚠️  未找到 requirements.txt"
fi
echo "✓ 依赖安装完成"
echo ""

# 步骤6: 创建配置文件
echo "步骤 6/6: 创建配置文件..."
cat > .env << 'EOF'
# Web服务配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False
LOG_LEVEL=INFO
EOF
echo "✓ 配置文件创建完成"
echo ""

# 测试应用导入
echo "测试应用导入..."
if python -c "from web.web_server_refactored import app; print('✓ 应用导入成功')" 2>&1; then
    echo ""
    echo "========================================"
    echo "✓ 部署完成！"
    echo "========================================"
    echo ""
    IP=$(hostname -I | awk '{print $1}')
    echo "手动启动服务:"
    echo "  cd /home/novelapp/novel-system"
    echo "  source venv/bin/activate"
    echo "  gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app"
    echo ""
    echo "访问网站: http://$IP:5000"
    echo ""
    echo "查看日志:"
    echo "  tail -f /home/novelapp/novel-system/logs/*.log"
    echo ""
else
    echo "❌ 应用导入失败，请检查日志"
    echo ""
    echo "查看详细错误："
    echo "  cd /home/novelapp/novel-system"
    echo "  source venv/bin/activate"
    echo "  python -c 'from web.web_server_refactored import app'"
    echo ""
    echo "常见问题："
    echo "1. 缺少依赖：pip install -r requirements.txt"
    echo "2. Python版本问题：确保使用 Python 3.10+"
    echo "3. 模块路径问题：检查项目结构"
    exit 1
fi