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
        """NovelCraft - AI 长篇小说辅助工具页面"""
        return render_template('pages/v2/novelcraft.html')
