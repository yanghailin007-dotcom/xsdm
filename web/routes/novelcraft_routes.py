"""
NovelCraft 页面路由
"""
from flask import render_template
from web.auth import login_required


def register_novelcraft_routes(app):
    """注册 NovelCraft 页面路由"""
    
    @app.route('/novelcraft', methods=['GET'])
    @login_required
    def novelcraft_page():
        """对话式设定生成页面（替换原小说工坊）"""
        return render_template('pages/v2/conversation-planning.html')
