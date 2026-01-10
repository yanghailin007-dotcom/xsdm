"""
WSGI入口文件
为Gunicorn等WSGI服务器提供应用入口
"""
import os
import sys

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.web_server_refactored import create_app

# 创建应用实例
app, manager = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)