#!/bin/bash
set -e

echo "========================================"
echo "阿里云Alibaba Cloud Linux 3 部署脚本"
echo "========================================"
echo ""

# 步骤1: 检查可用的Python版本
echo "步骤 1/5: 检查可用的Python版本..."
echo "搜索可用的Python包..."
yum search python3 2>/dev/null | grep -E "python3\.(9|10|11|12)" || true

# 尝试找到可用的Python版本
PYTHON_CMD=""
for py in python3.12 python3.11 python3.10 python3.9 python3.8; do
    if yum list $py 2>/dev/null | grep -q $py; then
        PYTHON_PKG=$py
        PYTHON_CMD=$py
        echo "✓ 找到可用的Python: $py"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "未找到Python 3.8+，尝试使用系统默认的python3"
    PYTHON_PKG="python3"
    PYTHON_CMD="python3"
fi

echo "将使用: $PYTHON_PKG"
echo ""

# 步骤2: 安装Python
echo "步骤 2/5: 安装Python和相关工具..."
yum install -y $PYTHON_PKG $PYTHON_PKG-pip $PYTHON_PKG-devel
echo "✓ Python安装完成"

# 验证安装
$PYTHON_CMD --version
echo ""

# 步骤3: 创建项目目录
echo "步骤 3/5: 创建项目目录..."
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
cd /home/novelapp/novel-system

# 检查是否已解压代码
if [ ! -f "web/web_server_refactored.py" ]; then
    echo "检查压缩包..."
    TAR_FILE=$(ls -t /tmp/novel_system_*.tar.gz 2>/dev/null | head -1)
    if [ -n "$TAR_FILE" ]; then
        echo "解压代码..."
        tar -xzf "$TAR_FILE"
        rm -f "$TAR_FILE"
        echo "✓ 代码解压完成"
    else
        echo "❌ 未找到代码压缩包"
        exit 1
    fi
fi
echo "✓ 项目目录就绪"
echo ""

# 步骤4: 创建虚拟环境
echo "步骤 4/5: 创建虚拟环境并安装依赖..."

# 删除旧虚拟环境
if [ -d venv ]; then
    echo "删除旧的虚拟环境..."
    rm -rf venv
fi

# 创建新虚拟环境
$PYTHON_CMD -m venv venv
echo "✓ 虚拟环境创建完成"

source venv/bin/activate

# 升级pip
pip install --upgrade pip -q

# 安装基础依赖
echo "安装基础依赖..."
pip install flask gunicorn eventlet -q

# 安装项目依赖（不指定严格版本）
if [ -f requirements.txt ]; then
    echo "安装项目依赖（使用兼容版本）..."
    pip install requests flask-cors pyyaml -q
    
    # 尝试安装requirements.txt中的包，忽略版本冲突
    while read -r line; do
        # 跳过注释和空行
        [[ "$line" =~ ^# ]] && continue
        [[ -z "$line" ]] && continue
        
        # 提取包名（忽略版本号）
        pkg_name=$(echo "$line" | cut -d'=' -f1 | cut -d'>' -f1 | cut -d'<' -f1 | xargs)
        
        if [ -n "$pkg_name" ]; then
            echo "安装 $pkg_name..."
            pip install "$pkg_name" -q 2>/dev/null || echo "  $pkg_name 安装失败，跳过"
        fi
    done < requirements.txt
else
    echo "未找到requirements.txt"
fi

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
if python -c "from web.web_server_refactored import create_app; create_app(); print('✓ 应用导入成功')" 2>&1; then
    echo ""
    echo "========================================"
    echo "✓ 部署完成！"
    echo "========================================"
    echo ""
    echo "Python版本: $($PYTHON_CMD --version)"
    IP=$(hostname -I | awk '{print $1}')
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
    echo ""
    exit 1
fi