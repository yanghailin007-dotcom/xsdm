# -*- coding: utf-8 -*-
"""
文风训练库页面路由
"""
from flask import Blueprint, render_template, session, redirect, url_for

writing_style_bp = Blueprint('writing_style_pages', __name__)

@writing_style_bp.route('/writing-style-library')
def writing_style_library():
    """文风训练库页面"""
    # 检查登录状态
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('pages/v2/writing-style-library.html')

def register_writing_style_routes(app):
    """注册文风相关路由"""
    app.register_blueprint(writing_style_bp)
