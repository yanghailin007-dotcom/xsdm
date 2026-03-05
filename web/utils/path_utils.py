"""
路径工具模块 - 支持用户隔离的小说项目路径管理
"""
from pathlib import Path
from flask import session
from typing import Optional, List
import os

# 小说项目根目录
NOVEL_PROJECTS_ROOT = Path("小说项目")

# 公共项目目录（旧数据迁移至此）
PUBLIC_PROJECTS_DIR = NOVEL_PROJECTS_ROOT / "_public"


def get_current_username() -> str:
    """获取当前登录用户名"""
    return session.get('username', 'anonymous')


def is_admin(username: str = None) -> bool:
    """检查是否为管理员"""
    if username is None:
        username = get_current_username()
    return username.lower() == 'admin'


def get_novel_projects_root() -> Path:
    """获取小说项目根目录"""
    return NOVEL_PROJECTS_ROOT


def get_user_novel_dir(username: str = None, create: bool = True) -> Path:
    """
    获取指定用户的小说目录
    
    Args:
        username: 用户名，默认当前登录用户
        create: 是否自动创建目录
    
    Returns:
        用户小说目录路径
    """
    if username is None:
        username = get_current_username()
    
    user_dir = NOVEL_PROJECTS_ROOT / username
    
    if create and not user_dir.exists():
        user_dir.mkdir(parents=True, exist_ok=True)
    
    return user_dir


def get_public_projects_dir(create: bool = True) -> Path:
    """
    获取公共项目目录（旧数据存放）
    
    Returns:
        公共项目目录路径
    """
    if create and not PUBLIC_PROJECTS_DIR.exists():
        PUBLIC_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    return PUBLIC_PROJECTS_DIR


def get_novel_project_dir(title: str, username: str = None, create: bool = False) -> Path:
    """
    获取指定小说项目的完整路径
    
    Args:
        title: 小说项目标题
        username: 用户名，默认当前登录用户
        create: 是否自动创建目录
    
    Returns:
        小说项目目录路径
    """
    project_dir = get_user_novel_dir(username, create) / _safe_filename(title)
    
    if create and not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
    
    return project_dir


def find_novel_project(title: str, username: str = None) -> Optional[Path]:
    """
    查找小说项目路径（先查用户目录，再查公共目录）
    
    Args:
        title: 小说项目标题
        username: 用户名，默认当前登录用户
    
    Returns:
        项目路径或None
    """
    if username is None:
        username = get_current_username()
    
    safe_title = _safe_filename(title)
    
    # 1. 先查用户自己的目录
    user_project = get_user_novel_dir(username, create=False) / safe_title
    if user_project.exists():
        return user_project
    
    # 2. 如果是管理员，遍历所有用户目录查找
    if is_admin(username):
        for user_dir in NOVEL_PROJECTS_ROOT.iterdir():
            if user_dir.is_dir() and not user_dir.name.startswith('_'):
                project_dir = user_dir / safe_title
                if project_dir.exists():
                    return project_dir
    
    # 3. 查公共目录（旧数据）
    public_project = get_public_projects_dir(create=False) / safe_title
    if public_project.exists():
        return public_project
    
    # 4. 查根目录（兼容旧路径）
    legacy_project = NOVEL_PROJECTS_ROOT / safe_title
    if legacy_project.exists():
        return legacy_project
    
    return None


def list_user_projects(username: str = None, include_public: bool = True) -> List[dict]:
    """
    列出用户的所有小说项目
    
    Args:
        username: 用户名，默认当前登录用户
        include_public: 是否包含公共项目
    
    Returns:
        项目列表，每项包含 title, path, owner 等信息
    """
    if username is None:
        username = get_current_username()
    
    projects = []
    seen_titles = set()
    
    # 1. 获取用户自己的项目
    user_dir = get_user_novel_dir(username, create=False)
    if user_dir.exists():
        for project_dir in user_dir.iterdir():
            if project_dir.is_dir():
                title = _restore_filename(project_dir.name)
                projects.append({
                    'title': title,
                    'path': str(project_dir),
                    'owner': username,
                    'is_public': False
                })
                seen_titles.add(title)
    
    # 2. 管理员可查看所有项目
    if is_admin(username):
        for user_dir in NOVEL_PROJECTS_ROOT.iterdir():
            if (user_dir.is_dir() and 
                not user_dir.name.startswith('_') and 
                user_dir.name != username):
                
                owner = user_dir.name
                for project_dir in user_dir.iterdir():
                    if project_dir.is_dir():
                        title = _restore_filename(project_dir.name)
                        if title not in seen_titles:
                            projects.append({
                                'title': title,
                                'path': str(project_dir),
                                'owner': owner,
                                'is_public': False
                            })
                            seen_titles.add(title)
    
    # 3. 包含公共项目
    if include_public:
        public_dir = get_public_projects_dir(create=False)
        if public_dir.exists():
            for project_dir in public_dir.iterdir():
                if project_dir.is_dir():
                    title = _restore_filename(project_dir.name)
                    if title not in seen_titles:
                        projects.append({
                            'title': title,
                            'path': str(project_dir),
                            'owner': 'public',
                            'is_public': True
                        })
                        seen_titles.add(title)
    
    return projects


def migrate_legacy_projects() -> dict:
    """
    迁移旧数据到公共目录
    
    Returns:
        迁移统计信息
    """
    stats = {'moved': 0, 'skipped': 0, 'errors': []}
    
    if not NOVEL_PROJECTS_ROOT.exists():
        return stats
    
    public_dir = get_public_projects_dir(create=True)
    
    for item in NOVEL_PROJECTS_ROOT.iterdir():
        # 跳过用户目录、公共目录和特殊目录
        if (item.is_dir() and 
            not item.name.startswith('_') and 
            item.name not in ['admin', 'public']):  # 简单判断，后续会完善
            
            try:
                # 检查是否是项目目录（有 project_info 或 chapters 等特征）
                if _is_project_dir(item):
                    target = public_dir / item.name
                    if target.exists():
                        stats['skipped'] += 1
                    else:
                        item.rename(target)
                        stats['moved'] += 1
            except Exception as e:
                stats['errors'].append(f"{item.name}: {str(e)}")
    
    return stats


def _is_project_dir(path: Path) -> bool:
    """判断是否是小说项目目录（通过特征文件/目录判断）"""
    indicators = [
        'project_info',
        'chapters',
        'characters',
        'worldview',
        'expectation_map.json',
        '.generation'
    ]
    
    for indicator in indicators:
        if (path / indicator).exists():
            return True
    
    return False


def _safe_filename(title: str) -> str:
    """将标题转换为安全的文件名"""
    # 移除或替换不安全字符
    unsafe_chars = '<>:"/\\|?*'
    result = title
    for char in unsafe_chars:
        result = result.replace(char, '_')
    
    # 限制长度
    if len(result) > 200:
        result = result[:200]
    
    return result.strip()


def _restore_filename(filename: str) -> str:
    """从文件名恢复原始标题（简单实现）"""
    # 目前只是原样返回，未来如果需要可以添加编码解码逻辑
    return filename


# 向后兼容的别名函数
get_project_dir = get_novel_project_dir
get_projects_root = get_novel_projects_root
