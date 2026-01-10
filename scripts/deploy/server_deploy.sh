#!/bin/bash
set -e

echo "========================================"
echo "服务器端部署脚本"
echo "========================================"
echo ""

# 检查是否以root运行
if [ "$USER" != "root" ]; then
    echo "请以root用户运行此脚本"
    exit 1
fi

# 检查压缩包
echo "检查上传的压缩包..."
TAR_FILE=$(ls -t /tmp/novel_system_*.tar.gz 2>/dev/null | head -1)
if [ -z "$TAR_FILE" ]; then
    echo "❌ 未找到上传的压缩包"
    echo "请先运行 simple_upload.bat 上传代码"
    exit 1
fi
echo "✓ 找到压缩包: $TAR_FILE"

# 创建项目目录
echo ""
echo "创建项目目录..."
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
echo "✓ 目录创建完成"

# 解压代码
echo ""
echo "解压代码..."
tar -xzf "$TAR_FILE" -C /home/novelapp/novel-system
echo "✓ 代码解压完成"

# 清理压缩包
rm -f "$TAR_FILE"

# 创建虚拟环境
echo ""
echo "创建Python虚拟环境..."
cd /home/novelapp/novel-system
python3.10 -m venv venv
echo "✓ 虚拟环境创建完成"

# 激活虚拟环境并安装依赖
echo ""
echo "安装Python依赖..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn eventlet flask -q
echo "✓ 依赖安装完成"

# 创建环境文件（不需要API密钥）
echo ""
echo "创建环境配置文件..."
cat > .env << 'EOF'
# Web服务配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False

# 日志配置
LOG_LEVEL=INFO

# API配置（可选 - 如果需要AI功能再配置）
# ARK_API_KEY=
# ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
# ARK_MODEL_ID=
EOF
echo "✓ 环境配置文件创建完成"

# 测试导入
echo ""
echo "测试应用导入..."
python -c "from web.web_server_refactored import app; print('✓ 应用导入成功')" 2>&1 || {
    echo "❌ 应用导入失败"
    echo "请检查错误日志"
    exit 1
}

echo ""
echo "========================================"
echo "部署完成！"
echo "========================================"
echo ""
echo "接下来可以："
echo ""
echo "1. 手动启动服务（测试）:"
echo "   cd /home/novelapp/novel-system"
echo "   source venv/bin/activate"
echo "   gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app"
echo ""
echo "2. 配置系统服务（生产）:"
echo "   bash /home/novelapp/novel-system/scripts/deploy/setup_service.sh"
echo ""
echo "3. 访问网站:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo ""