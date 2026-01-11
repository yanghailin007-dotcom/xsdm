"""
WSGI入口文件
为Gunicorn等WSGI服务器提供应用入口
"""
import os
import sys
import logging

# 🔥 第一步：在任何其他模块加载之前，立即禁用所有可能打印base64的日志
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests.packages").setLevel(logging.CRITICAL)
logging.getLogger("requests.packages.urllib3").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.util").setLevel(logging.CRITICAL)
logging.getLogger("urllib3.util.retry").setLevel(logging.CRITICAL)

# 清除所有handlers，阻止传播
for logger_name in ['requests', 'urllib3', 'requests.packages.urllib3', 'urllib3.connectionpool']:
    logger = logging.getLogger(logger_name)
    logger.handlers = []
    logger.propagate = False

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.web_server_refactored import create_app

# 创建应用实例
app, manager = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)