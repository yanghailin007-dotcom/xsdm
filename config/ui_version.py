"""
大文娱系统 - UI 版本配置

支持新旧UI并存，渐进式迁移
"""

# ==================== 全局配置 ====================

# 默认UI版本 ("v1" | "v2")
DEFAULT_UI_VERSION = "v1"

# 是否启用 V2 UI
ENABLE_V2 = True

# V2 是否对普通用户可见（False则仅管理员可用）
V2_PUBLIC_ACCESS = True


# ==================== 页面迁移状态 ====================

# 已迁移到 V2 的页面列表
# 这些页面会根据用户设置自动路由到 v2 版本
V2_PAGES = {
    # 页面名称: (v2端点, 是否完成)
    "landing": ("landing_v2", True),
    "index": ("index_v2", False),
    "dashboard": ("dashboard_v2", False),
    "projects": ("projects_v2", False),
    "novel_create": ("novel_create_v2", False),
    "video_create": ("video_create_v2", False),
}

# 强制使用 V2 的页面（即使有 ui=v1 参数）
V2_EXCLUSIVE_PAGES = []

# 强制使用 V1 的页面（即使有 ui=v2 参数）
V1_EXCLUSIVE_PAGES = []


# ==================== 路由映射 ====================

def get_page_version(page_name: str, user_version: str = None) -> str:
    """
    获取页面应该使用的UI版本
    
    Args:
        page_name: 页面名称
        user_version: 用户偏好的版本
        
    Returns:
        "v1" 或 "v2"
    """
    # 检查页面是否在 V2 列表中
    if page_name not in V2_PAGES:
        return "v1"
    
    v2_endpoint, is_ready = V2_PAGES[page_name]
    
    # 如果 V2 版本未完成，使用 V1
    if not is_ready:
        return "v1"
    
    # 如果用户有明确偏好，使用用户偏好
    if user_version in ["v1", "v2"]:
        return user_version
    
    # 使用全局默认
    return DEFAULT_UI_VERSION


def get_template_name(page_name: str, version: str = None) -> str:
    """
    获取模板文件名
    
    Args:
        page_name: 页面名称
        version: UI版本
        
    Returns:
        模板文件路径
    """
    if version == "v2" and page_name in V2_PAGES:
        return f"pages/v2/{page_name}-v2.html"
    return f"{page_name}.html"


# ==================== 用户设置 ====================

# 用户UI版本偏好存储键
USER_UI_VERSION_KEY = "ui_version"

# 支持的UI版本
SUPPORTED_VERSIONS = ["v1", "v2", "auto"]


def validate_version(version: str) -> str:
    """
    验证并规范版本字符串
    
    Args:
        version: 输入的版本字符串
        
    Returns:
        有效的版本字符串
    """
    if version in SUPPORTED_VERSIONS:
        return version
    return DEFAULT_UI_VERSION
