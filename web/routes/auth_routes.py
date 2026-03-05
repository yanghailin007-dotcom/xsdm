"""
认证和基础页面路由
"""
from flask import render_template, request, jsonify, session, redirect, url_for
from datetime import datetime

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
                logger.info(f"🔍 JSON数据: {data}")
            else:
                data = request.form
                logger.info(f"🔍 Form数据: {dict(data)}")
            
            username = (data.get('username') or '').strip() if data else ''
            password = data.get('password') or '' if data else ''
            
            logger.info(f"🔍 提取的用户名: '{username}', 密码长度: {len(password) if password else 0}")

            # 特殊处理：如果用户名是 "test"，允许空密码或任意密码登录（测试模式）
            if username.lower() == 'test':
                # 从数据库获取 test 用户的 ID
                from web.models.user_model import user_model
                user = user_model.get_user_by_username(username)
                user_id = user.get('id') if user else None
                
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user_id
                session.permanent = True
                logger.info(f"✅ 测试用户登录成功: {username} (ID: {user_id})")

                if request.is_json:
                    return jsonify({'success': True, 'message': '测试用户登录成功', 'redirect': '/landing'})
                return redirect('/landing')

            # 正常验证流程
            logger.info(f"🔍 开始验证用户: '{username}'")
            verify_result = user_auth.verify_user(username, password)
            logger.info(f"🔍 验证结果: {verify_result}")
            
            if verify_result:
                # 从数据库获取用户ID
                from web.models.user_model import user_model
                from web.models.point_model import point_model
                user = user_model.get_user_by_username(username)
                user_id = user.get('id') if user else None
                
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user_id
                session.permanent = True
                logger.info(f"✅ 用户登录成功: {username} (ID: {user_id})")
                
                # 检查并补发注册奖励（首次登录）
                if user_id:
                    try:
                        # 检查用户是否已有注册奖励记录
                        transactions = point_model.get_transactions(user_id, page=1, limit=10)
                        has_register_bonus = False
                        bonus_amount = point_model.get_config('register_bonus', 88)
                        if transactions and transactions.get('transactions'):
                            for t in transactions['transactions']:
                                if t.get('source') == 'register_bonus':
                                    has_register_bonus = True
                                    break
                        
                        # 如果没有注册奖励记录，则补发
                        if not has_register_bonus:
                            point_result = point_model.add_points(
                                user_id=user_id,
                                amount=bonus_amount,
                                source='register_bonus',
                                description='新用户注册奖励（首次登录）'
                            )
                            if point_result['success']:
                                logger.info(f"✅ 首次登录发放注册奖励{bonus_amount}点给用户{user_id}")
                            else:
                                logger.error(f"❌ 首次登录发放注册奖励失败: {point_result.get('error')}")
                    except Exception as e:
                        logger.error(f"❌ 检查/发放注册奖励失败: {e}")

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
                
                # 检查用户是否已领取注册奖励（有交易记录表示已领取）
                transactions = point_model.get_transactions(user_id, page=1, limit=10)
                has_claimed_bonus = False
                if transactions and transactions.get('transactions'):
                    for t in transactions['transactions']:
                        if t.get('source') == 'register_bonus':
                            has_claimed_bonus = True
                            break
                
                # 如果没有领取过奖励，显示欢迎弹窗
                if not has_claimed_bonus:
                    welcome_bonus = point_model.get_config('register_bonus', 88)
                    show_welcome = True
                    logger.info(f"✅ 用户 {user_id} 未领取注册奖励，将显示欢迎弹窗")
                    
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
        """第一阶段设定生成页面 - 默认 V2 UI"""
        # 检查是否请求 V1 版本（V2 为默认）
        ui_version = request.args.get('ui', '').lower()
        if ui_version == 'v1':
            logger.info("📄 Loading phase-one-setup.html (V1 UI)")
            return render_template('phase-one-setup.html')
        
        logger.info("📄 Loading phase-one-setup-v2.html (V2 UI - 默认)")
        return render_template('pages/v2/phase-one-setup-v2.html')

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
                'logged_in': True
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
            
            # 检查是否已领取过
            transactions = point_model.get_transactions(user_id, page=1, limit=10)
            if transactions and transactions.get('transactions'):
                for t in transactions['transactions']:
                    if t.get('source') == 'register_bonus':
                        return jsonify({'success': False, 'error': '奖励已领取'}), 400
            
            # 发放注册奖励
            bonus_amount = point_model.get_config('register_bonus', 88)
            point_result = point_model.add_points(
                user_id=user_id,
                amount=bonus_amount,
                source='register_bonus',
                description='新用户注册奖励（首次登录）'
            )
            
            if point_result['success']:
                # 标记已看过弹窗（作为领取记录）
                user_model.mark_welcome_shown(user_id)
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