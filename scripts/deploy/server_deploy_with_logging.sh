#!/bin/bash
set -e

echo "========================================"
echo "服务器端部署脚本 (带日志记录)"
echo "========================================"
echo ""

# 检查是否以root运行
if [ "$USER" != "root" ]; then
    echo "请以root用户运行此脚本"
    exit 1
fi

# 记录开始时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始部署" > /tmp/deploy.log

# 检查压缩包
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 检查上传的压缩包..." | tee -a /tmp/deploy.log
TAR_FILE=$(ls -t /tmp/novel_system_*.tar.gz 2>/dev/null | head -1)
if [ -z "$TAR_FILE" ]; then
    echo "❌ 未找到上传的压缩包" | tee -a /tmp/deploy.log
    echo "请先运行 一键部署_with_logs.bat 上传代码"
    exit 1
fi
echo "✓ 找到压缩包: $TAR_FILE" | tee -a /tmp/deploy.log

# 创建项目目录
echo "" | tee -a /tmp/deploy.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 创建项目目录..." | tee -a /tmp/deploy.log
mkdir -p /home/novelapp/novel-system
mkdir -p /home/novelapp/novel-system/{logs,data,generated_images,temp_fanqie_upload}
echo "✓ 目录创建完成" | tee -a /tmp/deploy.log

# 解压代码
echo "" | tee -a /tmp/deploy.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 解压代码..." | tee -a /tmp/deploy.log
tar -xzf "$TAR_FILE" -C /home/novelapp/novel-system 2>&1 | tee -a /tmp/deploy.log
echo "✓ 代码解压完成" | tee -a /tmp/deploy.log

# 清理压缩包
rm -f "$TAR_FILE"

# 检查虚拟环境
echo "" | tee -a /tmp/deploy.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 检查Python虚拟环境..." | tee -a /tmp/deploy.log
cd /home/novelapp/novel-system

if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..." | tee -a /tmp/deploy.log
    python3.10 -m venv venv
    echo "✓ 虚拟环境创建完成" | tee -a /tmp/deploy.log
    
    # 激活虚拟环境并安装依赖
    echo "" | tee -a /tmp/deploy.log
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 安装Python依赖..." | tee -a /tmp/deploy.log
    source venv/bin/activate
    pip install --upgrade pip -q 2>&1 | tee -a /tmp/deploy.log
    pip install -r requirements.txt -q 2>&1 | tee -a /tmp/deploy.log
    pip install gunicorn eventlet flask -q 2>&1 | tee -a /tmp/deploy.log
    echo "✓ 依赖安装完成" | tee -a /tmp/deploy.log
else
    echo "✓ 虚拟环境已存在" | tee -a /tmp/deploy.log
    source venv/bin/activate
    
    # 检查是否需要更新依赖
    echo "检查依赖更新..." | tee -a /tmp/deploy.log
    pip install --upgrade pip -q 2>&1 | tee -a /tmp/deploy.log
    pip install -r requirements.txt -q 2>&1 | tee -a /tmp/deploy.log
    echo "✓ 依赖检查完成" | tee -a /tmp/deploy.log
fi

# 创建环境文件
echo "" | tee -a /tmp/deploy.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 创建环境配置文件..." | tee -a /tmp/deploy.log
cat > .env << 'EOF'
# Web服务配置
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=False

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=/home/novelapp/novel-system/logs

# API配置（可选 - 如果需要AI功能再配置）
# ARK_API_KEY=
# ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
# ARK_MODEL_ID=
EOF
echo "✓ 环境配置文件创建完成" | tee -a /tmp/deploy.log

# 测试导入
echo "" | tee -a /tmp/deploy.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 测试应用导入..." | tee -a /tmp/deploy.log
python -c "from web.web_server_refactored import app; print('✓ 应用导入成功')" 2>&1 | tee -a /tmp/deploy.log || {
    echo "❌ 应用导入失败" | tee -a /tmp/deploy.log
    echo "请检查错误日志"
    exit 1
}

echo "" | tee -a /tmp/deploy.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 部署完成！" | tee -a /tmp/deploy.log
echo "========================================" | tee -a /tmp/deploy.log
echo "部署完成！" | tee -a /tmp/deploy.log
echo "========================================" | tee -a /tmp/deploy.log
echo "" | tee -a /tmp/deploy.log
echo "接下来可以：" | tee -a /tmp/deploy.log
echo "" | tee -a /tmp/deploy.log
echo "1. 使用启动脚本运行服务：" | tee -a /tmp/deploy.log
echo "   bash /tmp/start_with_logging.sh" | tee -a /tmp/deploy.log
echo "" | tee -a /tmp/deploy.log
echo "2. 访问网站：" | tee -a /tmp/deploy.log
echo "   http://$(hostname -I | awk '{print $1}'):5000" | tee -a /tmp/deploy.log
echo "" | tee -a /tmp/deploy.log
echo "3. 查看日志：" | tee -a /tmp/deploy.log
echo "   tail -f /home/novelapp/novel-system/logs/application.log" | tee -a /tmp/deploy.log
echo "" | tee -a /tmp/deploy.log