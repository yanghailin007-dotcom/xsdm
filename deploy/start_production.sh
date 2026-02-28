#!/bin/bash
# 生产环境启动脚本

# 设置项目路径
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 检查虚拟环境
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "错误：虚拟环境不存在，请先运行安装脚本"
    exit 1
fi

# 检查环境变量文件
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "错误：.env 文件不存在，请从 .env.production.example 复制并配置"
    exit 1
fi

# 激活虚拟环境
source "$PROJECT_DIR/.venv/bin/activate"

# 验证关键环境变量
python3 << EOF
import os
import sys
from dotenv import load_dotenv

load_dotenv('$PROJECT_DIR/.env')

required_vars = ['GEMINI_API_KEY', 'DEEPSEEK_API_KEY']
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"错误：缺少必要的环境变量: {', '.join(missing)}")
    sys.exit(1)

print("环境变量验证通过")
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

# 启动 Gunicorn
echo "启动 Novel Generator 服务..."
cd "$PROJECT_DIR"
exec gunicorn \
    -w 4 \
    -b 127.0.0.1:5000 \
    --timeout 300 \
    --access-logfile "$LOG_DIR/access.log" \
    --error-logfile "$LOG_DIR/error.log" \
    --capture-output \
    --enable-stdio-inheritance \
    web.wsgi:application
