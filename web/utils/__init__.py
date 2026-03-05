"""
Web 工具模块
"""
from .path_utils import (
    get_novel_projects_root,
    get_user_novel_dir,
    get_public_projects_dir,
    get_novel_project_dir,
    find_novel_project,
    list_user_projects,
    migrate_legacy_projects,
    is_admin,
    get_current_username,
    NOVEL_PROJECTS_ROOT,
    PUBLIC_PROJECTS_DIR
)

__all__ = [
    'get_novel_projects_root',
    'get_user_novel_dir',
    'get_public_projects_dir',
    'get_novel_project_dir',
    'find_novel_project',
    'list_user_projects',
    'migrate_legacy_projects',
    'is_admin',
    'get_current_username',
    'NOVEL_PROJECTS_ROOT',
    'PUBLIC_PROJECTS_DIR'
]
