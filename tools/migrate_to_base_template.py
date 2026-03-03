#!/usr/bin/env python3
"""
迁移工具：将现有页面迁移到基础模板继承架构

使用方法：
    python tools/migrate_to_base_template.py web/templates/index.html
    
或使用 --dry-run 预览变更：
    python tools/migrate_to_base_template.py web/templates/index.html --dry-run
"""

import re
import sys
import argparse
from pathlib import Path


def extract_content(html_content: str) -> dict:
    """从现有HTML中提取关键部分"""
    result = {
        'title': '大文娱系统',
        'extra_css': [],
        'content': '',
        'extra_js': [],
    }
    
    # 提取 title
    title_match = re.search(r'<title>(.*?)</title>', html_content, re.DOTALL)
    if title_match:
        result['title'] = title_match.group(1).strip()
    
    # 提取 body 内容（简化处理）
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
    if body_match:
        body_content = body_match.group(1).strip()
        
        # 尝试移除导航栏（简化逻辑）
        # 实际使用时可能需要根据具体情况调整
        result['content'] = body_content
    
    # 提取额外的CSS链接
    css_matches = re.findall(r'<link[^>]*href="([^"]*\.css)"[^>]*>', html_content)
    result['extra_css'] = [css for css in css_matches if 'common.css' not in css]
    
    # 提取额外的JS脚本
    js_matches = re.findall(r'<script[^>]*src="([^"]*\.js)"[^>]*>', html_content)
    result['extra_js'] = [js for js in js_matches if js not in ['confirm-dialog.js', 'user-info.js']]
    
    return result


def generate_new_template(extracted: dict, original_file: str) -> str:
    """生成新的模板内容"""
    
    # CSS 块
    css_block = ''
    if extracted['extra_css']:
        css_block = '{% block extra_css %}\n'
        for css in extracted['extra_css']:
            css_block += f'    <link rel="stylesheet" href="{{{{ url_for(\'static\', filename=\'{css}\') }}}}">\n'
        css_block += '{% endblock %}'
    
    # JS 块
    js_block = ''
    if extracted['extra_js']:
        js_block = '{% block extra_js %}\n'
        for js in extracted['extra_js']:
            js_block += f'    <script src="{{{{ url_for(\'static\', filename=\'{js}\') }}}}"></script>\n'
        js_block += '{% endblock %}'
    
    template = f'''{{% extends "base.html" %}}

{{% block title %}}{extracted['title']}{{% endblock %}}

{css_block}

{{% block content %}}
<!-- TODO: 需要手动清理以下内容，移除导航栏、页脚等公共部分 -->
{extracted['content']}
{{% endblock %}}

{js_block}
'''
    return template


def migrate_file(file_path: Path, dry_run: bool = False) -> None:
    """迁移单个文件"""
    print(f"\n{'='*60}")
    print(f"处理文件: {file_path}")
    print(f"{'='*60}")
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # 检查是否已经继承 base.html
        if '{% extends' in content:
            print(f"⚠️  文件已经使用模板继承，跳过")
            return
        
        extracted = extract_content(content)
        new_content = generate_new_template(extracted, str(file_path))
        
        if dry_run:
            print("\n--- 预览变更 ---")
            print(new_content[:2000])
            print("... (仅显示前2000字符)")
        else:
            # 备份原文件
            backup_path = file_path.with_suffix('.html.backup')
            file_path.rename(backup_path)
            print(f"✅ 已备份原文件到: {backup_path}")
            
            # 写入新文件
            file_path.write_text(new_content, encoding='utf-8')
            print(f"✅ 已生成新模板: {file_path}")
            print("\n⚠️  注意：需要手动清理 content 块中的导航栏、页脚等公共部分")
    
    except Exception as e:
        print(f"❌ 错误: {e}")


def main():
    parser = argparse.ArgumentParser(description='迁移模板到基础模板架构')
    parser.add_argument('files', nargs='+', help='要迁移的HTML文件')
    parser.add_argument('--dry-run', action='store_true', help='预览变更而不实际执行')
    
    args = parser.parse_args()
    
    for file_path in args.files:
        path = Path(file_path)
        if not path.exists():
            print(f"❌ 文件不存在: {file_path}")
            continue
        migrate_file(path, args.dry_run)


if __name__ == '__main__':
    main()
