#!/bin/bash
set -e

echo "服务器端部署开始..."
echo ""

# 清理旧进程
echo "步骤 1/7: 清理旧进程..."
pkill -f "gunicorn" || true
pkill -f "python.*web_server" || true
pkill -f "flask" || true
fuser -k 5000/tcp 2>/dev/null || true
sleep 2
echo "✓ 进程清理完成"
echo ""

# 清理旧代码
echo "步骤 2/7: 清理旧代码..."
if [ -d "/home/novelapp/novel-system" ]; then
    echo "备份旧代码..."
    mv /home/novelapp/novel-system /home/novelapp/novel-system.backup.$(date +%Y%m%d_%H%M%S) || true
fi
echo "✓ 旧代码已清理"
echo ""

# 检查压缩包
echo "步骤 3/7: 检查上传的压缩包..."
TAR_FILE=$(ls -t /tmp/novel_system_*.tar.gz 2>/dev/null | head -1)
if [ -z "$TAR_FILE" ]; then
    echo "❌ 未找到上传的压缩包"
    exit 1
fi
echo "✓ 找到压缩包: $TAR_FILE"
ls -lh "$TAR_FILE"
echo ""

# 创建项目目录
echo "步骤 4/7: 创建项目目录..."
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
echo "✓ 目录创建完成"
echo ""

# 解压代码
echo "步骤 5/7: 解压代码..."
cd /home/novelapp/novel-system
tar -xzf "$TAR_FILE"
echo "✓ 代码解压完成"
rm -f "$TAR_FILE"
echo ""

# 创建虚拟环境
echo "步骤 6/7: 创建Python虚拟环境..."

# 检测Linux发行版和包管理器
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID=$ID
    echo "检测到操作系统: $PRETTY_NAME"
else
    OS_ID="unknown"
    echo "⚠️  无法检测操作系统类型"
fi

# 先安装python3-venv包（Ubuntu/Debian系统）
if [ "$OS_ID" = "ubuntu" ] || [ "$OS_ID" = "debian" ]; then
    echo "检查python3-venv包..."
    if ! dpkg -l | grep -q python3-venv; then
        echo "安装python3-venv包..."
        sudo apt update -qq
        sudo apt install -y -qq python3-venv python3-dev
        echo "✓ python3-venv安装完成"
    else
        echo "✓ python3-venv已安装"
    fi
fi

# 检查Python版本
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "检测到Python版本: $PYTHON_VERSION"

# 检查是否需要升级Python（需要Python 3.8+）
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "⚠️  Python版本过低（需要3.8+），正在升级到Python 3.10..."
    
    # 根据不同的包管理器使用不同的命令
    if command -v apt &> /dev/null; then
        echo "使用APT包管理器（Ubuntu/Debian）..."
        
        # 更新apt源
        echo "更新apt源..."
        sudo apt update -qq
        
        # 安装必要的工具
        echo "安装依赖工具..."
        sudo apt install -y -qq software-properties-common
        
        # 添加deadsnakes PPA
        echo "添加Python 3.10 PPA源..."
        sudo add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1
        
        # 更新源
        sudo apt update -qq
        
        # 安装Python 3.10
        echo "安装Python 3.10..."
        sudo apt install -y -qq python3.10 python3.10-venv python3.10-dev python3-pip
        
        # 设置python3.10为默认python3
        echo "设置Python 3.10为默认版本..."
        sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
        
    elif command -v yum &> /dev/null; then
        echo "使用YUM包管理器（CentOS/Alibaba Linux）..."
        
        # 检查是否已安装EPEL（阿里云Linux已有epel-aliyuncs-release）
        if ! rpm -q epel-release > /dev/null 2>&1 && ! rpm -q epel-aliyuncs-release > /dev/null 2>&1; then
            echo "安装EPEL仓库..."
            sudo yum install -y -q epel-release || echo "⚠️  EPEL安装失败，可能已存在"
        else
            echo "✓ EPEL仓库已存在"
        fi
        
        # 检查可用的Python版本
        echo "检查可用的Python版本..."
        
        # 查找所有可用的python3版本
        AVAILABLE_PYTHONS=$(compgen -c | grep "^python3\." | sort -u)
        
        if [ -n "$AVAILABLE_PYTHONS" ]; then
            echo "找到可用的Python版本:"
            echo "$AVAILABLE_PYTHONS"
            
            # 优先使用Python 3.8+
            for py_ver in "python3.11" "python3.10" "python3.9" "python3.8"; do
                if command -v $py_ver &> /dev/null; then
                    echo "✓ 发现 $py_ver，使用该版本"
                    sudo alternatives --install /usr/bin/python3 python3 $(which $py_ver) 1
                    break
                fi
            done
        else
            echo "⚠️  未找到Python 3.8+版本，将使用Python 3.6安装兼容依赖"
        fi
        
    else
        echo "❌ 未找到apt或yum包管理器"
        echo "请手动安装Python 3.8+"
        exit 1
    fi
    
    # 验证安装
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "✓ Python配置完成，当前版本: $PYTHON_VERSION"
else
    echo "✓ Python版本符合要求（3.8+）"
fi

# 创建虚拟环境
echo "创建Python虚拟环境..."
python3 -m venv venv
echo "✓ 虚拟环境创建完成"
echo ""

# 安装依赖
echo "安装项目依赖..."
source venv/bin/activate
pip install --upgrade pip -q

# 检查当前Python版本
CURRENT_PYTHON=$(python3 --version | awk '{print $2}')
CURRENT_MAJOR=$(echo $CURRENT_PYTHON | cut -d. -f1)
CURRENT_MINOR=$(echo $CURRENT_PYTHON | cut -d. -f2)

echo "当前Python版本: $CURRENT_PYTHON"

# 根据Python版本选择合适的Flask版本
if [ "$CURRENT_MAJOR" -eq 3 ] && [ "$CURRENT_MINOR" -lt 8 ]; then
    echo "⚠️  Python 3.$CURRENT_MINOR 不支持Flask 2.3.0，使用兼容版本Flask 2.0.3"
    
    # 安装兼容Python 3.6的核心依赖
    pip install flask==2.0.3 -q
    pip install flask-cors==3.0.10 -q
    pip install requests==2.27.1 -q
    pip install python-dotenv==0.19.2 -q
    pip install "openai<1.0.0" -q  # Python 3.6兼容版本
    pip install gunicorn==20.1.0 -q
    pip install eventlet -q
    pip install werkzeug==2.0.3 -q
    
    echo "✓ 依赖安装完成（使用Python 3.6兼容版本）"
else
    # Python 3.8+，可以使用最新版本
    if [ -f requirements.txt ]; then
        echo "安装requirements.txt中的所有依赖..."
        pip install -r requirements.txt -q || {
            echo "⚠️  部分依赖安装失败，安装核心依赖..."
            pip install flask flask-cors requests python-dotenv openai gunicorn eventlet -q
        }
        echo "✓ 依赖安装完成"
    else
        echo "⚠️  未找到requirements.txt，安装核心依赖..."
        pip install flask flask-cors requests python-dotenv openai gunicorn eventlet -q
        echo "✓ 核心依赖安装完成"
    fi
fi
echo ""

# 配置环境变量
echo "配置环境变量..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ .env文件已创建（基于.env.example）"
        echo "⚠️  请手动编辑.env文件配置API密钥"
    else
        echo "⚠️  未找到.env.example"
    fi
else
    echo "✓ .env文件已存在"
fi
echo ""

# 配置Supervisor
echo "步骤 7/7: 配置Supervisor并启动服务..."

# 检查并安装Supervisor
if ! command -v supervisorctl &> /dev/null; then
    echo "安装Supervisor..."
    
    # 根据包管理器选择安装命令
    if command -v apt &> /dev/null; then
        sudo apt install -y supervisor
    elif command -v yum &> /dev/null; then
        sudo yum install -y supervisor || {
            # 如果yum找不到，使用pip安装
            echo "YUM未找到supervisor，使用pip安装..."
            source venv/bin/activate
            pip install supervisor
        }
    fi
    echo "✓ Supervisor安装完成"
else
    echo "✓ Supervisor已安装"
fi

# 创建Supervisor配置目录
echo "创建Supervisor配置目录..."
sudo mkdir -p /etc/supervisor/conf.d
sudo mkdir -p /var/log/supervisor

echo "创建Supervisor配置文件..."
cat > /tmp/supervisor_config.conf << 'EOFCONF'
[program:novel-system]
command=/home/novelapp/novel-system/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 600 --access-logfile /home/novelapp/novel-system/logs/gunicorn-access.log --error-logfile /home/novelapp/novel-system/logs/gunicorn-error.log --log-level info web.wsgi:app
directory=/home/novelapp/novel-system
user=root
autostart=true
autorestart=true
startretries=3
stderr_logfile=/home/novelapp/novel-system/logs/supervisor-stderr.log
stdout_logfile=/home/novelapp/novel-system/logs/supervisor-stdout.log
environment=FLASK_ENV="production"
EOFCONF

sudo mv /tmp/supervisor_config.conf /etc/supervisor/conf.d/novel-system.conf
echo "✓ Supervisor配置完成"

# 启动Supervisor服务（如果未运行）
# Ubuntu 24.04使用supervisor服务名
SUPERVISOR_SERVICE="supervisor"
if ! systemctl list-unit-files | grep -q "^${SUPERVISOR_SERVICE}.service"; then
    SUPERVISOR_SERVICE="supervisord"
fi

if ! sudo systemctl is-active --quiet ${SUPERVISOR_SERVICE}; then
    echo "启动Supervisor服务..."
    sudo systemctl start ${SUPERVISOR_SERVICE}
    sudo systemctl enable ${SUPERVISOR_SERVICE}
    echo "✓ Supervisor服务已启动"
fi

# 检查wsgi.py文件
if [ ! -f "web.wsgi" ]; then
    echo "⚠️  未找到web.wsgi文件，尝试创建..."
    cat > web.wsgi << 'EOF'
from web.web_server_refactored import app
if __name__ == "__main__":
    app.run()
EOF
    echo "✓ web.wsgi文件已创建"
fi

# 测试应用导入
echo "测试应用导入..."
source venv/bin/activate
if python -c "from web.web_server_refactored import app; print('✓ 应用导入成功')" 2>&1; then
    echo "✓ 应用可以正常导入"
else
    echo "⚠️  应用导入失败，但继续尝试启动"
fi

# 重新加载配置
echo "重新加载Supervisor配置..."
sudo supervisorctl reread || true
sudo supervisorctl update || true
echo ""

# 启动应用
echo "启动应用服务..."
sudo supervisorctl start novel-system || {
    echo "⚠️  Supervisor启动失败，尝试手动启动..."
    echo "使用nohup在后台启动..."
    nohup venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.wsgi:app > logs/gunicorn.log 2>&1 &
    sleep 3
    echo "✓ 应用已手动启动（使用nohup）"
    
    # 检查是否启动成功
    if ps aux | grep -v grep | grep gunicorn > /dev/null; then
        echo "✓ 应用正在运行"
        echo ""
        echo "========================================"
        echo "✓ 部署完成！（使用nohup后台运行）"
        echo "========================================"
        echo ""
        echo "服务信息:"
        echo "  状态: 运行中（nohup后台模式）"
        echo "  端口: 5000"
        echo ""
        echo "访问地址:"
        echo "  本地: http://localhost:5000"
        echo "  公网: http://8.163.37.124:5000"
        echo ""
        echo "管理命令:"
        echo "  查看进程: ps aux | grep gunicorn"
        echo "  停止服务: pkill -f gunicorn"
        echo "  查看日志: tail -f /home/novelapp/novel-system/logs/gunicorn.log"
        echo ""
        exit 0
    else
        echo "❌ 应用启动失败"
        echo ""
        echo "调试步骤:"
        echo "1. 检查应用:"
        echo "   cd /home/novelapp/novel-system"
        echo "   source venv/bin/activate"
        echo "   python -c \"from web.web_server_refactored import app\""
        echo ""
        echo "2. 手动测试启动:"
        echo "   gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.wsgi:app"
        echo ""
        exit 1
    fi
}

sleep 3

# 检查服务状态
if sudo supervisorctl status novel-system 2>/dev/null | grep -q "RUNNING"; then
    echo ""
    echo "========================================"
    echo "✓ 部署完成！"
    echo "========================================"
    echo ""
    echo "服务信息:"
    echo "  状态: 运行中"
    echo "  端口: 5000"
    echo ""
    echo "访问地址:"
    echo "  本地: http://localhost:5000"
    echo "  公网: http://8.163.37.124:5000"
    echo ""
    echo "常用命令:"
    echo "  查看状态: sudo supervisorctl status novel-system"
    echo "  查看日志: sudo supervisorctl tail -f novel-system"
    echo "  重启服务: sudo supervisorctl restart novel-system"
    echo "  停止服务: sudo supervisorctl stop novel-system"
    echo "  查看Supervisor状态: sudo systemctl status supervisord"
    echo ""
else
    echo ""
    echo "❌ 服务启动失败"
    echo ""
    echo "调试信息:"
    echo "1. 检查Supervisor状态:"
    echo "   sudo systemctl status supervisord"
    echo ""
    echo "2. 查看Supervisor日志:"
    echo "   sudo tail -f /var/log/supervisor/supervisord.log"
    echo ""
    echo "3. 查看应用日志:"
    echo "   tail -f /home/novelapp/novel-system/logs/gunicorn-error.log"
    echo ""
    echo "4. 手动测试启动:"
    echo "   cd /home/novelapp/novel-system"
    echo "   source venv/bin/activate"
    echo "   gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.wsgi:app"
    echo ""
    exit 1
fi