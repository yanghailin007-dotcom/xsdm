"""
认证和基础页面路由
"""
from flask import render_template, request, jsonify, session, redirect, url_for
from datetime import datetime

from web.auth import user_auth, login_required
from web.web_config import logger


def register_auth_routes(app):
    """注册认证和基础页面路由"""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """登录页面和登录处理"""
        if request.method == 'POST':
            data = request.json if request.is_json else request.form
            username = (data.get('username') or '').strip() if data else ''
            password = data.get('password') or '' if data else ''

            # 特殊处理：如果用户名是 "test"，允许空密码或任意密码登录（测试模式）
            if username.lower() == 'test':
                session['logged_in'] = True
                session['username'] = username
                session.permanent = True
                logger.info(f"✅ 测试用户登录成功: {username} (密码: {'空' if not password else '***'})")

                if request.is_json:
                    return jsonify({'success': True, 'message': '测试用户登录成功', 'redirect': '/landing'})
                return redirect('/landing')

            # 正常验证流程
            if user_auth.verify_user(username, password):
                session['logged_in'] = True
                session['username'] = username
                session.permanent = True
                logger.info(f"✅ 用户登录成功: {username}")

                if request.is_json:
                    return jsonify({'success': True, 'message': '登录成功', 'redirect': '/landing'})
                return redirect('/landing')
            else:
                logger.info(f"❌ 登录失败: {username}")
                if request.is_json:
                    return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
                return render_template('login.html', error='用户名或密码错误')

        # GET 请求 - 显示登录页面
        if 'logged_in' in session and session['logged_in']:
            return redirect('/landing')
        return render_template('login.html')

    @app.route('/logout', methods=['GET', 'POST'])
    def logout():
        """登出"""
        username = session.get('username', 'unknown')
        session.clear()
        logger.info(f"👋 用户登出: {username}")
        return redirect(url_for('login'))
    
    @app.route('/register', methods=['GET'])
    def register():
        """注册页面"""
        if 'logged_in' in session and session['logged_in']:
            return redirect('/')
        return render_template('register.html')


def register_page_routes(app):
    """注册基础页面路由"""
    
    @app.route('/favicon.ico')
    def favicon():
        """处理 favicon 请求，返回 logo.png"""
        from flask import send_from_directory
        import os
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logo.png')
        if os.path.exists(logo_path):
            return send_from_directory(os.path.dirname(logo_path), 'logo.png', mimetype='image/png')
        # 如果 logo.png 不存在，返回 204
        from flask import Response
        return Response(status=204)
    
    @app.route('/landing', methods=['GET'])
    def landing():
        """大文娱系统首页"""
        logger.info("📄 Loading landing.html")
        return render_template('landing.html')
    
    @app.route('/', methods=['GET'])
    @login_required
    def index():
        """小说创意生成入口"""
        logger.info(f"📄 Loading index.html from template folder: {app.template_folder}")
        return render_template('index.html')
    
    @app.route('/home', methods=['GET'])
    def home():
        """首页 - 根据登录状态决定跳转"""
        if session.get('logged_in'):
            logger.info("📄 User logged in, loading index.html")
            return render_template('index.html')
        else:
            logger.info("📄 User not logged in, redirecting to login")
            return redirect(url_for('login'))

    @app.route('/novels', methods=['GET'])
    @login_required
    def novels_view():
        """作品列表页面"""
        return render_template('novels.html')

    @app.route('/novel', methods=['GET'])
    @login_required
    def novel_view():
        """小说阅读页面"""
        return render_template('novel_view.html')

    @app.route('/dashboard', methods=['GET'])
    @login_required
    def dashboard():
        """仪表板"""
        return render_template('dashboard.html')

    @app.route('/test_layout_improvements.html', methods=['GET'])
    @login_required
    def test_layout_improvements():
        """布局改进测试页面"""
        return render_template('test_layout_improvements.html')

    @app.route('/test_large_modal_fix.html', methods=['GET'])
    @login_required
    def test_large_modal_fix():
        """大弹窗功能测试页面"""
        from flask import send_from_directory
        from web.web_config import BASE_DIR
        return send_from_directory(str(BASE_DIR), 'test_large_modal_fix.html')

    @app.route('/cover-generator', methods=['GET'])
    @login_required
    def cover_generator():
        """小说封面生成器页面"""
        return render_template('cover_maker.html')

    @app.route('/cover-maker', methods=['GET'])
    @login_required
    def cover_maker():
        """小说封面制作页面"""
        return render_template('cover_maker.html')

    @app.route('/fanqie-upload', methods=['GET'])
    @login_required
    def fanqie_upload():
        """番茄小说一键上传页面"""
        return render_template('fanqie_upload.html')
    
    @app.route('/phase-one-setup', methods=['GET'])
    @login_required
    def phase_one_setup():
        """第一阶段设定生成页面"""
        return render_template('phase-one-setup.html')

    @app.route('/phase-one-setup-new', methods=['GET'])
    @login_required
    def phase_one_setup_new():
        """第一阶段设定生成页面（新版）"""
        return render_template('phase-one-setup-new.html')

    @app.route('/phase-two-generation', methods=['GET'])
    @login_required
    def phase_two_generation():
        """第二阶段章节生成页面"""
        return render_template('phase-two-generation.html')

    @app.route('/project-management', methods=['GET'])
    @login_required
    def project_management():
        """项目管理页面"""
        return render_template('project-management.html')
    
    @app.route('/storyline', methods=['GET'])
    @login_required
    def storyline_view():
        """故事线时间线页面"""
        return render_template('storyline.html')
    
    @app.route('/chapter-view', methods=['GET'])
    @login_required
    def chapter_view():
        """章节内容查看页面"""
        return render_template('chapter-view.html')
    
    @app.route('/video-generation', methods=['GET'])
    @login_required
    def video_generation():
        """视频生成页面"""
        return render_template('video-generation.html')

    @app.route('/short-drama-studio', methods=['GET'])
    @login_required
    def short_drama_studio():
        """短剧工作台页面"""
        return render_template('short-drama-studio.html')

    @app.route('/video-generation-debug', methods=['GET'])
    @login_required
    def video_generation_debug():
        """视频生成调试工具页面"""
        return render_template('video_generation_debug.html')
    
    @app.route('/character-portrait', methods=['GET'])
    @login_required
    def character_portrait():
        """人物剧照生成页面"""
        return render_template('character-portrait.html')
    
    @app.route('/portrait-studio', methods=['GET'])
    @login_required
    def portrait_studio():
        """人物剧照工作室页面"""
        return render_template('portrait-studio.html')

    @app.route('/short-drama', methods=['GET'])
    @login_required
    def short_drama():
        """短剧风格改造页面"""
        return render_template('short-drama.html')

    @app.route('/still-image-library', methods=['GET'])
    @login_required
    def still_image_library():
        """图像素材库页面"""
        return render_template('still-image-library.html')
    
    @app.route('/library', methods=['GET'])
    @login_required
    def library_redirect():
        """素材库页面（兼容旧链接）"""
        return redirect('/still-image-library')
    
    @app.route('/video-studio', methods=['GET'])
    @login_required
    def video_studio():
        """视频工作室页面"""
        return render_template('video-studio.html')
    
    @app.route('/project-viewer/<project_title>', methods=['GET'])
    @login_required
    def project_viewer(project_title):
        """项目可视化页面"""
        from urllib.parse import unquote
        project_title = unquote(project_title)
        return render_template('project-viewer.html', project_title=project_title)
    
    @app.route('/worldview-viewer/<project_title>', methods=['GET'])
    @login_required
    def worldview_viewer(project_title):
        """世界观查看器页面（简化版）"""
        from urllib.parse import unquote
        project_title = unquote(project_title)
        return render_template('worldview-viewer.html', project_title=project_title)

    # ========== 新的视频制作中心路由 ==========

    @app.route('/video', methods=['GET'])
    @login_required
    def video_center():
        """视频制作中心首页"""
        return render_template('video/index.html')

    @app.route('/video/project', methods=['GET'])
    @login_required
    def video_project_center():
        """项目管理器"""
        return render_template('video/project.html')

    @app.route('/video/project/<project_id>', methods=['GET'])
    @login_required
    def video_project_detail(project_id):
        """项目详情"""
        return render_template('video/project.html', project_id=project_id)

    @app.route('/video/portrait', methods=['GET'])
    @login_required
    def video_portrait():
        """剧照工作台"""
        return render_template('video/portrait.html')

    @app.route('/video/studio', methods=['GET'])
    @login_required
    def video_studio_new():
        """视频工作台（新版）"""
        return render_template('video/studio.html')

    @app.route('/video/workflow', methods=['GET'])
    @login_required
    def video_workflow():
        """流程控制器"""
        return render_template('video/workflow.html')

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        """404 处理"""
        return jsonify({"error": "页面未找到"}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """500 处理"""
        return jsonify({"error": "服务器内部错误"}), 500