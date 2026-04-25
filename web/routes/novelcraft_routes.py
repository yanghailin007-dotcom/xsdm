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

    @app.route('/chapter-generation', methods=['GET'])
    @login_required
    def chapter_generation_page():
        """正文生成页面"""
        return render_template('pages/v2/chapter-generation.html')

    @app.route('/volume-outline-generation', methods=['GET'])
    @login_required
    def volume_outline_generation_page():
        """分卷细纲生成页面"""
        return render_template('pages/v2/volume-outline-generation.html')
