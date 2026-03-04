"""
UI 版本切换中间件
处理新旧UI版本的路由和切换逻辑
"""

from flask import request, g, current_user
from config.ui_version import (
    DEFAULT_UI_VERSION,
    ENABLE_V2,
    V2_PUBLIC_ACCESS,
    V2_PAGES,
    get_page_version,
    get_template_name,
    validate_version,
    USER_UI_VERSION_KEY,
)


class UIVersionMiddleware:
    """
    UI版本切换中间件
    
    处理逻辑：
    1. URL 参数 ?ui=v2 优先级最高
    2. 用户设置中的 ui_version
    3. 全局默认配置 DEFAULT_UI_VERSION
    4. 根据页面迁移状态自动选择
    """
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化中间件"""
        app.before_request(self.before_request)
        app.context_processor(self.context_processor)
    
    def before_request(self):
        """请求前处理 - 确定UI版本"""
        # 如果 V2 未启用，直接返回
        if not ENABLE_V2:
            g.ui_version = "v1"
            return
        
        ui_version = None
        
        # 1. 检查 URL 参数（最高优先级）
        url_version = request.args.get('ui')
        if url_version:
            ui_version = validate_version(url_version)
        
        # 2. 检查用户设置
        if not ui_version and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            # 从用户设置获取
            user_version = getattr(current_user, 'settings', {}).get(USER_UI_VERSION_KEY)
            if user_version and user_version != "auto":
                ui_version = validate_version(user_version)
        
        # 3. 检查 Cookie
        if not ui_version:
            cookie_version = request.cookies.get('ui_version')
            if cookie_version:
                ui_version = validate_version(cookie_version)
        
        # 4. 使用全局默认
        if not ui_version:
            ui_version = DEFAULT_UI_VERSION
        
        # 5. 检查管理员权限（如果 V2 未开放）
        if ui_version == "v2" and not V2_PUBLIC_ACCESS:
            is_admin = hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and \
                      getattr(current_user, 'is_admin', False)
            if not is_admin:
                ui_version = "v1"
        
        # 存储到请求上下文
        g.ui_version = ui_version
        g.use_v2 = (ui_version == "v2")
    
    def context_processor(self):
        """模板上下文处理器 - 注入UI版本相关变量"""
        return {
            'ui_version': getattr(g, 'ui_version', DEFAULT_UI_VERSION),
            'use_v2': getattr(g, 'use_v2', False),
            'v2_enabled': ENABLE_V2,
        }


def should_use_v2(page_name: str) -> bool:
    """
    判断指定页面是否应该使用 V2 版本
    
    Args:
        page_name: 页面名称
        
    Returns:
        是否使用 V2
    """
    if not ENABLE_V2:
        return False
    
    user_version = getattr(g, 'ui_version', DEFAULT_UI_VERSION)
    page_version = get_page_version(page_name, user_version)
    
    return page_version == "v2"


def render_page(page_name: str, **kwargs):
    """
    智能渲染页面，自动选择 V1/V2 版本
    
    使用示例：
        return render_page('landing', title="首页")
    
    Args:
        page_name: 页面名称
        **kwargs: 模板变量
        
    Returns:
        Response 对象
    """
    from flask import render_template
    
    version = getattr(g, 'ui_version', DEFAULT_UI_VERSION)
    template = get_template_name(page_name, version)
    
    return render_template(template, **kwargs)
