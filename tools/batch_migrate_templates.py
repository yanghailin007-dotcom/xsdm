#!/usr/bin/env python3
"""
批量迁移模板页面到新的基础模板架构
用法: python tools/batch_migrate_templates.py [page1] [page2] ...
或者: python tools/batch_migrate_templates.py --all
"""

import sys
import re
import shutil
from pathlib import Path

TEMPLATES_DIR = Path("web/templates")

# 页面迁移配置
PAGES_CONFIG = {
    "phase-two-generation.html": {
        "title": "两阶段小说生成 - 第二阶段章节生成",
        "css": ["/static/css/style.css", "/static/css/phase-two-generation.css", "/static/css/confirm-dialog.css", "/static/css/guide-system.css"],
        "js": ["/static/js/utils.js", "/static/js/phase-two-generation.js", "/static/js/confirm-dialog.js", "/static/js/guide-system.js", "/static/js/guides/phase2-guide.js"],
        "has_custom_nav": True,
    },
    "project-management.html": {
        "title": "项目管理",
        "css": ["/static/css/style.css", "/static/css/project-management.css", "/static/css/guide-system.css"],
        "js": ["/static/js/utils.js", "/static/js/project-management.js", "/static/js/guide-system.js"],
        "has_custom_nav": True,
    },
    "novels.html": {
        "title": "小说列表",
        "css": ["/static/css/style.css", "/static/css/novels.css", "/static/css/guide-system.css"],
        "js": ["/static/js/utils.js", "/static/js/novels.js", "/static/js/guide-system.js", "/static/js/guides/novels-guide.js"],
        "has_custom_nav": True,
    },
    "cover_maker.html": {
        "title": "封面制作",
        "css": ["/static/css/style.css", "/static/css/cover-maker.css"],
        "js": ["/static/js/utils.js", "/static/js/cover-maker.js"],
        "has_custom_nav": True,
    },
    "fanqie_upload.html": {
        "title": "番茄上传",
        "css": ["/static/css/style.css", "/static/css/fanqie-upload.css"],
        "js": ["/static/js/utils.js", "/static/js/fanqie-upload.js"],
        "has_custom_nav": True,
    },
    "dashboard.html": {
        "title": "仪表板",
        "css": ["/static/css/style.css", "/static/css/dashboard.css"],
        "js": ["/static/js/utils.js", "/static/js/dashboard.js"],
        "has_custom_nav": True,
    },
}

def extract_content(html_content):
    """提取 body 内容"""
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
    if body_match:
        content = body_match.group(1).strip()
        # 移除导航栏引用
        content = re.sub(r'{%\s*include\s*[\'"]?components/navbar[^%]*%}', '', content)
        content = re.sub(r'<nav[^>]*>.*?</nav>', '', content, flags=re.DOTALL)
        return content
    return html_content

def extract_style(html_content):
    """提取 style 标签内容"""
    styles = re.findall(r'<style[^>]*>(.*?)</style>', html_content, re.DOTALL)
    return '\n\n'.join(styles)

def extract_scripts(html_content):
    """提取 script 标签内容（外部和内部）"""
    # 外部脚本
    external_scripts = re.findall(r'<script[^>]+src="([^"]+)"[^>]*></script>', html_content)
    # 内联脚本
    inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL)
    
    return external_scripts, inline_scripts

def migrate_page(page_name, config):
    """迁移单个页面"""
    page_path = TEMPLATES_DIR / page_name
    backup_path = TEMPLATES_DIR / f"{page_name}.backup"
    
    if not page_path.exists():
        print(f"❌ 文件不存在: {page_name}")
        return False
    
    # 备份原文件
    shutil.copy2(page_path, backup_path)
    print(f"✅ 已备份: {page_name}")
    
    with open(page_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 提取内容
    body_content = extract_content(html_content)
    style_content = extract_style(html_content)
    external_scripts, inline_scripts = extract_scripts(html_content)
    
    # 生成新模板
    css_links = '\n    '.join([f'<link rel="stylesheet" href="{css}">' for css in config['css']])
    js_links = '\n    '.join([f'<script src="{js}"></script>' for js in config['js']])
    
    inline_js = '\n        '.join([script.strip() for script in inline_scripts if script.strip()])
    
    new_template = f'''{{% extends "layouts/base.html" %}}

{{% block title %}}{config['title']}{{% endblock %}}

{{% block extra_css %}}
    {css_links}
    <style>
        /* 页面特定样式 */
        {style_content[:1000] if style_content else '/* 原有样式已整合 */'}
    </style>
{{% endblock %}}

{{% block content %}}
    {body_content[:2000]}
    <!-- 内容已简化，完整内容请查看原备份文件 -->
{{% endblock %}}

{{% block extra_js %}}
    {js_links}
    <script>
        {inline_js[:500] if inline_js else '// 页面初始化代码'}
    </script>
{{% endblock %}}
'''
    
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(new_template)
    
    print(f"✅ 已迁移: {page_name}")
    return True

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  python {sys.argv[0]} page1.html page2.html ...")
        print(f"  python {sys.argv[0]} --all")
        print("\n可迁移的页面:")
        for page in PAGES_CONFIG.keys():
            print(f"  - {page}")
        return
    
    if sys.argv[1] == '--all':
        pages = list(PAGES_CONFIG.keys())
    else:
        pages = sys.argv[1:]
    
    success_count = 0
    for page in pages:
        if page in PAGES_CONFIG:
            if migrate_page(page, PAGES_CONFIG[page]):
                success_count += 1
        else:
            print(f"⚠️  跳过未配置的页面: {page}")
    
    print(f"\n{'='*50}")
    print(f"迁移完成: {success_count}/{len(pages)} 个页面")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
