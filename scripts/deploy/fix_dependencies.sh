#!/bin/bash
set -e

echo "========================================"
echo "修复依赖问题"
echo "========================================"
echo ""

cd /home/novelapp/novel-system
source venv/bin/activate

echo "步骤 1/4: 检查Python版本..."
python --version
echo ""

echo "步骤 2/4: 安装兼容的依赖..."
# 使用兼容老版本Python的依赖版本
pip install --upgrade pip
pip install "flask>=2.0,<3.0"
pip install flask-cors
pip install gunicorn eventlet
pip install requests
pip install pyyaml

echo ""
echo "步骤 3/4: 安装其他必要依赖..."
# 安装其他不指定严格版本的依赖
pip install sqlalchemy || echo "sqlalchemy安装失败，跳过"
pip install jinja2 || echo "jinja2安装失败，跳过"
pip install werkzeug || echo "werkzeug安装失败，跳过"
pip install itsdangerous || echo "itsdangerous安装失败，跳过"
pip install click || echo "click安装失败，跳过"
pip install markupsafe || echo "markupsafe安装失败，跳过"

echo ""
echo "步骤 4/4: 测试应用导入..."
python -c "from web.web_server_refactored import app; print('✓ 应用导入成功')"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✓ 依赖修复成功！"
    echo "========================================"
    echo ""
    echo "现在可以启动服务了："
    echo "  cd /home/novelapp/novel-system"
    echo "  source venv/bin/activate"
    echo "  gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app"
    echo ""
else
    echo ""
    echo "❌ 应用仍然无法导入"
    echo "可能需要升级Python版本到3.10+"
    echo ""
fi