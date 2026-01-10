@echo off
chcp 65001 >nul
echo ========================================
echo    诊断应用导入问题
echo ========================================
echo.

set KEY_PATH=d:\work6.05\xsdm.pem
set SERVER_IP=8.163.37.124
set SERVER_USER=root

echo 正在连接服务器并诊断问题...
echo.

ssh -i "%KEY_PATH%" -p 22 -o StrictHostKeyChecking=no %SERVER_USER%@%SERVER_IP% "bash -l" << 'ENDSSH'
#!/bin/bash
set -e

echo "=== 步骤1: 检查项目目录 ==="
cd /home/novelapp/novel-system
pwd
ls -la | head -20
echo ""

echo "=== 步骤2: 检查虚拟环境 ==="
if [ -d venv ]; then
    echo "✓ 虚拟环境存在"
    source venv/bin/activate
    python --version
    echo ""
else
    echo "❌ 虚拟环境不存在"
    exit 1
fi

echo "=== 步骤3: 检查Python路径 ==="
echo "Python位置: $(which python)"
echo "当前目录: $(pwd)"
echo ""

echo "=== 步骤4: 检查关键文件 ==="
echo "检查 web_server_refactored.py:"
ls -lh web/web_server_refactored.py 2>&1 || echo "文件不存在"
echo ""
echo "检查 requirements.txt:"
ls -lh requirements.txt 2>&1 || echo "文件不存在"
echo ""

echo "=== 步骤5: 测试模块导入 ==="
echo "尝试导入 web.web_server_refactored..."
python -c "
import sys
print('Python路径:')
for p in sys.path[:3]:
    print(f'  {p}')
print('')
try:
    from web.web_server_refactored import app
    print('✓ 导入成功')
except Exception as e:
    print(f'❌ 导入失败: {type(e).__name__}')
    print(f'错误信息: {str(e)}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "=== 步骤6: 检查已安装的包 ==="
pip list | grep -i flask || echo "Flask未安装"
pip list | grep -i gunicorn || echo "Gunicorn未安装"
echo ""

echo "=== 步骤7: 建议的修复命令 ==="
echo "如果缺少依赖，请运行:"
echo "  cd /home/novelapp/novel-system"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo ""
ENDSSH

echo.
echo ========================================
echo    诊断完成
echo ========================================
echo.
pause