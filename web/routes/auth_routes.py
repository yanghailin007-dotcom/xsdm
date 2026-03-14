"""
认证和基础页面路由
"""
from flask import render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta

from web.auth import user_auth, login_required
from web.web_config import logger
from functools import wraps


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function


def register_auth_routes(app):
    """注册认证和基础页面路由"""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """登录页面和登录处理"""
        if request.method == 'POST':
            logger.info(f"🔍 登录请求 - is_json: {request.is_json}, content-type: {request.content_type}")
            
            if request.is_json:
                data = request.json
                logger.info(f"🔍 收到 JSON 登录请求")
            else:
                data = request.form
                logger.info(f"🔍 Form数据: {dict(data)}")
            
            username = (data.get('username') or '').strip() if data else ''
            password = data.get('password') or '' if data else ''
            
            logger.info(f"🔍 登录用户: '{username}'")

            # 特殊处理：如果用户名是 "test"，允许空密码或任意密码登录（测试模式）
            if username.lower() == 'test':
                # 从数据库获取 test 用户的 ID
                from web.models.user_model import user_model
                user = user_model.get_user_by_username(username)
                user_id = user.get('id') if user else None
                
                # 处理"记住我"选项
                remember = data.get('remember', False)
                if isinstance(remember, str):
                    remember = remember.lower() in ('true', '1', 'yes', 'on')
                
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user_id
                session.permanent = True
                
                # 设置会话过期时间
                if remember:
                    session['remember'] = True
                    app.permanent_session_lifetime = timedelta(days=30)
                else:
                    app.permanent_session_lifetime = timedelta(days=1)
                
                logger.info(f"✅ 测试用户登录成功: {username} (ID: {user_id}, 记住我: {remember})")

                if request.is_json:
                    return jsonify({'success': True, 'message': '测试用户登录成功', 'redirect': '/landing'})
                return redirect('/landing')

            # 正常验证流程
            logger.info(f"🔍 开始验证用户: '{username}'")
            verify_result = user_auth.verify_user(username, password)
            logger.info(f"🔍 验证结果: {verify_result}")
            
            if verify_result:
                # 从数据库获取用户ID和管理员状态
                from web.models.user_model import user_model
                from web.models.point_model import point_model
                user = user_model.get_user_by_username(username)
                user_id = user.get('id') if user else None
                is_admin = user.get('is_admin', 0) if user else 0
                
                # 处理"记住我"选项
                remember = data.get('remember', False)
                if isinstance(remember, str):
                    remember = remember.lower() in ('true', '1', 'yes', 'on')
                
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user_id
                session['is_admin'] = bool(is_admin)
                session.permanent = True
                
                # 如果选择了"记住我"，设置会话过期时间为30天，否则为1天
                if remember:
                    session['remember'] = True
                    app.permanent_session_lifetime = timedelta(days=30)
                    logger.info(f"✅ 用户登录成功: {username} (ID: {user_id}, is_admin: {is_admin}, 记住我: 30天)")
                else:
                    app.permanent_session_lifetime = timedelta(days=1)
                    logger.info(f"✅ 用户登录成功: {username} (ID: {user_id}, is_admin: {is_admin}, 会话: 1天)")
                
                # 为用户创建小说项目目录（如果不存在）
                try:
                    from web.utils.path_utils import get_user_novel_dir
                    user_novel_dir = get_user_novel_dir(username, create=True)
                    logger.info(f"📁 用户小说目录: {user_novel_dir}")
                except Exception as e:
                    logger.warning(f"⚠️ 创建用户小说目录失败: {e}")
                
                # 注：注册奖励改为在用户关闭欢迎弹窗时领取，不再自动发放

                if request.is_json:
                    # 🔑 JWT Token 认证 - 生成 Token
                    from web.jwt_auth import generate_tokens
                    from web.models.point_model import point_model
                    
                    points = point_model.get_user_points(user_id)
                    tokens = generate_tokens(
                        user_id=user_id,
                        username=username,
                        is_admin=bool(is_admin),
                        extra_data={
                            'points_balance': points.get('balance', 0),
                            'avatar': user.get('avatar', '/static/images/avatar-default.png')
                        }
                    )
                    
                    return jsonify({
                        'success': True, 
                        'message': '登录成功',
                        'redirect': '/landing',
                        # 🔑 返回 Token 信息（用于多账号切换）
                        'user_id': user_id,
                        'username': username,
                        'is_admin': bool(is_admin),
                        'points_balance': points.get('balance', 0),
                        **tokens
                    })
                return redirect('/landing')
            else:
                logger.info(f"❌ 登录失败: {username}")
                if request.is_json:
                    return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
                return render_template('login.html', error='用户名或密码错误')

        # GET 请求 - 显示登录页面
        # 允许 mode=add-account 参数绕过登录检查（用于添加多账户）
        if 'logged_in' in session and session['logged_in']:
            if request.args.get('mode') != 'add-account':
                return redirect('/landing')
        
        # V2 版本切换支持
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('login.html')
        return render_template('pages/v2/login-v2.html')

    @app.route('/logout', methods=['GET', 'POST'])
    def logout():
        """登出"""
        username = session.get('username', 'unknown')
        session.clear()
        logger.info(f"👋 用户登出: {username}")
        return redirect(url_for('login'))
    
    # ==================== JWT Token API ====================
    
    @app.route('/api/auth/refresh', methods=['POST'])
    def refresh_token():
        """刷新 Access Token
        请求: { refresh_token: "xxx" }
        响应: { access_token: "xxx", refresh_token: "xxx", expires_in: 7200 }
        """
        from web.jwt_auth import decode_token, generate_tokens
        
        data = request.get_json()
        if not data or not data.get('refresh_token'):
            return jsonify({'success': False, 'error': 'Missing refresh_token'}), 400
        
        refresh_token = data['refresh_token']
        
        # 验证 Refresh Token
        payload, error = decode_token(refresh_token, 'refresh')
        
        if error:
            return jsonify({
                'success': False, 
                'error': error['message'],
                'code': error['code']
            }), 401
        
        user_id = payload['user_id']
        username = payload['username']
        
        # 从数据库获取最新用户信息
        from web.models.user_model import user_model
        from web.models.point_model import point_model
        
        user = user_model.get_user_by_username(username)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        points = point_model.get_user_points(user_id)
        
        # 生成新的 Token 对
        tokens = generate_tokens(
            user_id=user_id,
            username=username,
            is_admin=bool(user.get('is_admin', 0)),
            extra_data={
                'points_balance': points.get('balance', 0),
                'avatar': user.get('avatar', '/static/images/avatar-default.png')
            }
        )
        
        logger.info(f"🔑 Token 刷新: {username} (user_id: {user_id})")
        
        return jsonify({
            'success': True,
            **tokens
        })
    
    @app.route('/api/auth/verify', methods=['GET'])
    def verify_token():
        """验证 Access Token 是否有效"""
        from web.jwt_auth import decode_token, get_token_from_request
        
        token = get_token_from_request()
        if not token or token == '__session__':
            # 检查 Session 兼容模式
            if session.get('logged_in'):
                return jsonify({
                    'success': True,
                    'user_id': session.get('user_id'),
                    'username': session.get('username'),
                    'is_admin': session.get('is_admin', False),
                    'source': 'session'
                })
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        payload, error = decode_token(token, 'access')
        
        if error:
            return jsonify({
                'success': False,
                'error': error['message'],
                'code': error['code']
            }), 401
        
        return jsonify({
            'success': True,
            'user_id': payload['user_id'],
            'username': payload['username'],
            'is_admin': payload.get('is_admin', False),
            'extra': payload.get('extra', {})
        })
    
    @app.route('/api/auth/switch-account', methods=['POST'])
    def switch_account():
        """切换账户 - 用于多账户管理器
        请求: { user_id: "xxx" }
        响应: { success: true, username: "xxx" }
        """
        from web.models.user_model import user_model
        from web.models.point_model import point_model
        
        data = request.get_json()
        if not data or not data.get('user_id'):
            return jsonify({'success': False, 'error': 'Missing user_id'}), 400
        
        target_user_id = data['user_id']
        
        # 获取目标用户信息
        user = user_model.get_user_by_id(target_user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # 获取用户点数
        points = point_model.get_user_points(target_user_id)
        
        # 更新 session 为新账户
        session['logged_in'] = True
        session['username'] = user['username']
        session['user_id'] = target_user_id
        session['is_admin'] = bool(user.get('is_admin', 0))
        session.permanent = True
        
        logger.info(f"🔄 账户切换: {user['username']} (user_id: {target_user_id})")
        
        return jsonify({
            'success': True,
            'user_id': target_user_id,
            'username': user['username'],
            'is_admin': bool(user.get('is_admin', 0)),
            'points_balance': points.get('balance', 0)
        })
    
    @app.route('/register', methods=['GET'])
    def register():
        """注册页面"""
        if 'logged_in' in session and session['logged_in']:
            return redirect('/')
        
        # V2 版本切换支持
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('register.html')
        return render_template('pages/v2/register-v2.html')


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
        """大文娱系统首页 - 默认 V2 UI，支持切换回 V1"""
        # 检查是否请求 V1 版本（V2 为默认）
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            logger.info("📄 Loading landing.html (V1 UI)")
            return render_template('landing.html')
        
        # 检查是否需要显示欢迎弹窗（未领取注册奖励的用户）
        show_welcome = False
        welcome_bonus = 0
        if session.get('logged_in') and session.get('user_id'):
            try:
                from web.models.user_model import user_model
                from web.models.point_model import point_model
                user_id = session['user_id']
                
                # 🔥 双重检查1：检查是否已标记看过欢迎弹窗
                if user_model.has_seen_welcome(user_id):
                    logger.info(f"用户 {user_id} 已看过欢迎弹窗，跳过显示")
                    show_welcome = False
                else:
                    # 🔥 双重检查2：检查交易记录
                    transactions = point_model.get_transactions(user_id, page=1, limit=10)
                    has_claimed_bonus = False
                    if transactions and transactions.get('transactions'):
                        for t in transactions['transactions']:
                            if t.get('source') == 'register_bonus':
                                has_claimed_bonus = True
                                # 如果已有交易记录但未标记，补充标记
                                user_model.mark_welcome_shown(user_id)
                                logger.info(f"用户 {user_id} 已有交易记录，补充标记")
                                break
                    
                    # 如果没有领取过奖励，显示欢迎弹窗
                    if not has_claimed_bonus:
                        welcome_bonus = point_model.get_config('register_bonus', 88)
                        show_welcome = True
                        logger.info(f"✅ 用户 {user_id} 未领取注册奖励，将显示欢迎弹窗")
                    else:
                        logger.info(f"用户 {user_id} 已有交易记录，不显示弹窗")
                    
            except Exception as e:
                logger.error(f"❌ 检查欢迎弹窗状态失败: {e}")
        
        logger.info(f"📄 Loading landing-v2.html (V2 UI - 默认), show_welcome={show_welcome}")
        return render_template('pages/v2/landing-v2.html', 
                               show_welcome=show_welcome, 
                               welcome_bonus=welcome_bonus)
    
    @app.route('/landing-v2-test', methods=['GET'])
    def landing_v2_test():
        """V2 UI 测试页面"""
        return render_template('landing-v2-test.html')
    
    @app.route('/', methods=['GET'])
    @login_required
    def index():
        """小说创意生成入口 - 默认 V2 UI"""
        # 检查是否请求 V1 版本（V2 为默认）
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            logger.info("📄 Loading index.html (V1 UI)")
            return render_template('index.html')
        
        logger.info("📄 Loading index-v2.html (V2 UI - 默认)")
        return render_template('pages/v2/index-v2.html')
    
    @app.route('/home', methods=['GET'])
    def home():
        """首页 - 默认 V2 UI，支持切换回 V1"""
        if session.get('logged_in'):
            # 检查是否请求 V1 版本（V2 为默认）
            ui_version = request.args.get('ui', '').lower()
            if ui_version == 'v1':
                logger.info("📄 Loading index.html (V1 UI)")
                return render_template('index.html')
            
            logger.info("📄 Loading index-v2.html (V2 UI - 默认)")
            return render_template('pages/v2/index-v2.html')
        else:
            logger.info("📄 User not logged in, redirecting to login")
            return redirect(url_for('login'))

    @app.route('/novels', methods=['GET'])
    @login_required
    def novels_view():
        """作品列表页面 - 默认 V2 UI"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('novels.html')
        return render_template('pages/v2/novels-v2.html')

    @app.route('/novel', methods=['GET'])
    @login_required
    def novel_view():
        """小说阅读页面 - 默认 V2 UI"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('novel_view.html')
        return render_template('pages/v2/novel-v2.html')

    @app.route('/dashboard', methods=['GET'])
    @login_required
    def dashboard():
        """仪表板"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('dashboard.html')
        return render_template('pages/v2/dashboard-v2.html')

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
        """第一阶段设定生成页面 - Glassmorphism UI v3.0"""
        # 检查是否请求旧版本
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            logger.info("📄 Loading phase-one-setup.html (V1 UI)")
            return render_template('phase-one-setup.html')
        elif ui_version == 'v2':
            logger.info("📄 Loading phase-one-setup-v2.html (V2 UI)")
            return render_template('pages/v2/phase-one-setup-v2.html')
        
        logger.info("📄 Loading phase-one-setup-new.html (Glassmorphism UI v3.0 - 默认)")
        return render_template('phase-one-setup-new.html')

    @app.route('/phase-one-setup-new', methods=['GET'])
    @login_required
    def phase_one_setup_new():
        """第一阶段设定生成页面（新版）"""
        return render_template('phase-one-setup-new.html')

    @app.route('/phase-two-generation', methods=['GET'])
    @login_required
    def phase_two_generation():
        """第二阶段章节生成页面 - Glassmorphism UI v2.0"""
        logger.info("📄 Loading phase-two-generation.html (Glassmorphism UI v2.0)")
        return render_template('phase-two-generation.html')

    @app.route('/phase-two-demo', methods=['GET'])
    @login_required
    def phase_two_demo():
        """第二阶段UI设计演示页面 - Glassmorphism Design System"""
        logger.info("📄 Loading phase-two-demo.html (UI Demo)")
        return render_template('pages/v2/phase-two-demo.html')

    @app.route('/project-management', methods=['GET'])
    @login_required
    def project_management():
        """项目管理页面 - 默认 V2 UI"""
        # 检查是否请求 V1 版本（V2 为默认）
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            logger.info("📄 Loading project-management.html (V1 UI)")
            return render_template('project-management.html')
        
        logger.info("📄 Loading project-management-v2.html (V2 UI - 默认)")
        return render_template('pages/v2/project-management-v2.html')
    
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

    @app.route('/portrait-studio-v2', methods=['GET'])
    @login_required
    def portrait_studio_v2():
        """人物剧照工作室页面 - 无限画布版本（Konva.js）"""
        return render_template('portrait-studio-new.html')

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

    @app.route('/admin/points-config', methods=['GET'])
    @login_required
    @admin_required
    def admin_points_config():
        """点数配置管理页面（管理员）"""
        return render_template('admin/points-config.html')

    @app.route('/help', methods=['GET'])
    def help_center():
        """帮助中心页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('help.html')
        return render_template('pages/v2/help-v2.html')

    @app.route('/terms', methods=['GET'])
    def terms():
        """使用条款页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('terms.html')
        return render_template('pages/v2/terms-v2.html')

    @app.route('/privacy', methods=['GET'])
    def privacy():
        """隐私政策页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('privacy.html')
        return render_template('pages/v2/privacy-v2.html')

    @app.route('/contact', methods=['GET'])
    def contact():
        """联系我们页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('contact.html')
        return render_template('pages/v2/contact-v2.html')

    @app.route('/recharge', methods=['GET'])
    @login_required
    def recharge():
        """充值页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('recharge.html')
        return render_template('pages/v2/recharge-v2.html')

    @app.route('/points', methods=['GET'])
    @login_required
    def points():
        """余额管理页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('recharge.html')
        return render_template('pages/v2/recharge-v2.html')

    @app.route('/payment/success', methods=['GET'])
    @login_required
    def payment_success():
        """支付成功页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('payment-success.html')
        return render_template('pages/v2/payment-success-v2.html')

    @app.route('/settings', methods=['GET'])
    @login_required
    def settings():
        """偏好设置页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('settings.html')
        return render_template('pages/v2/settings-v2.html')

    @app.route('/account', methods=['GET'])
    @login_required
    def account():
        """账户管理页面"""
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            return render_template('account.html')
        return render_template('pages/v2/account-v2.html')

    @app.route('/api/current-user', methods=['GET'])
    def get_current_user():
        """获取当前登录用户信息"""
        if session.get('logged_in'):
            return jsonify({
                'success': True,
                'username': session.get('username', 'unknown'),
                'user_id': session.get('user_id'),
                'logged_in': True,
                'is_admin': session.get('is_admin', False)
            })
        return jsonify({
            'success': False,
            'logged_in': False
        }), 401

    @app.route('/api/account/change-password', methods=['POST'])
    @login_required
    def change_password():
        """修改密码"""
        try:
            data = request.json
            current_password = data.get('current_password', '')
            new_password = data.get('new_password', '')
            
            if not current_password or not new_password:
                return jsonify({'success': False, 'error': '请填写所有必填字段'}), 400
            
            if len(new_password) < 6:
                return jsonify({'success': False, 'error': '新密码至少需要6位'}), 400
            
            username = session.get('username')
            
            # 验证当前密码
            if not user_auth.verify_user(username, current_password):
                return jsonify({'success': False, 'error': '当前密码错误'}), 401
            
            # 更新密码
            if user_auth.update_password(username, new_password):
                logger.info(f"🔐 用户 {username} 修改密码成功")
                return jsonify({'success': True, 'message': '密码修改成功'})
            else:
                return jsonify({'success': False, 'error': '密码修改失败'}), 500
                
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            return jsonify({'success': False, 'error': '服务器错误'}), 500

    # 清除首次登录标记
    @app.route('/api/claim-register-bonus', methods=['POST'])
    @login_required
    def claim_register_bonus():
        """用户关闭欢迎弹窗时领取注册奖励"""
        try:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': '未登录'}), 401
                
            from web.models.user_model import user_model
            from web.models.point_model import point_model
            
            # 🔥 双重检查：先检查是否已标记看过弹窗（快速路径）
            if user_model.has_seen_welcome(user_id):
                logger.info(f"用户 {user_id} 已标记看过欢迎弹窗，跳过重复奖励")
                return jsonify({'success': False, 'error': '奖励已领取'}), 400
            
            # 🔥 再次检查交易记录（确保数据一致性）
            transactions = point_model.get_transactions(user_id, page=1, limit=10)
            if transactions and transactions.get('transactions'):
                for t in transactions['transactions']:
                    if t.get('source') == 'register_bonus':
                        # 如果已有交易记录但未标记，则补充标记
                        user_model.mark_welcome_shown(user_id)
                        logger.info(f"用户 {user_id} 已有交易记录，标记为已看过")
                        return jsonify({'success': False, 'error': '奖励已领取'}), 400
            
            # 🔥 先标记已看过（防止并发重复领取）
            # 即使后续发放失败，也不会重复发放
            user_model.mark_welcome_shown(user_id)
            
            # 发放注册奖励
            bonus_amount = point_model.get_config('register_bonus', 88)
            point_result = point_model.add_points(
                user_id=user_id,
                amount=bonus_amount,
                source='register_bonus',
                description='新用户注册奖励（首次登录）'
            )
            
            if point_result['success']:
                logger.info(f"✅ 用户 {user_id} 领取注册奖励 {bonus_amount} 点")
                return jsonify({
                    'success': True, 
                    'message': f'成功领取 {bonus_amount} 点创作点数',
                    'amount': bonus_amount
                })
            else:
                logger.error(f"❌ 发放注册奖励失败: {point_result.get('error')}")
                return jsonify({'success': False, 'error': '发放奖励失败'}), 500
                
        except Exception as e:
            logger.error(f"领取注册奖励失败: {e}")
            return jsonify({'success': False, 'error': '服务器错误'}), 500

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        """404 处理"""
        return jsonify({"error": "页面未找到"}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """500 处理"""
        return jsonify({"error": "服务器内部错误"}), 500