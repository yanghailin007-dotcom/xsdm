# -*- coding: utf-8 -*-
"""
修复项目中角色图片的URL路径
"""
import json
import os
from pathlib import Path

def fix_character_image_urls(project_dir):
    """修复项目中的角色图片URL"""
    project_info_file = project_dir / '项目信息.json'

    if not project_info_file.exists():
        print(f"[ERROR] 项目信息文件不存在: {project_info_file}")
        return False

    # 读取项目信息
    with open(project_info_file, 'r', encoding='utf-8') as f:
        project_data = json.load(f)

    project_id = project_data.get('id')
    if not project_id:
        print(f"[ERROR] 无法获取项目ID")
        return False

    # 检查visualAssets
    visual_assets = project_data.get('visualAssets', {})
    characters = visual_assets.get('characters', {})

    if not characters:
        print(f"[INFO] 项目中没有角色图片")
        return True

    # 修复每个角色的URL
    fixed_count = 0
    for char_name, char_data in characters.items():
        local_path = char_data.get('localPath', '')
        reference_url = char_data.get('referenceUrl', '')

        if not local_path:
            print(f"[WARN] 角色 {char_name} 没有localPath")
            continue

        # 从localPath提取正确的URL
        if 'generated_images' in local_path:
            # 提取从generated_images开始的相对路径
            rel_path = local_path.split('generated_images')[-1].replace('\\', '/')
            if rel_path.startswith('/'):
                rel_path = rel_path[1:]
            correct_url = f"/generated_images/{rel_path}"

            if reference_url != correct_url:
                print(f"[FIX] 修复角色 {char_name}:")
                print(f"   旧URL: {reference_url}")
                print(f"   新URL: {correct_url}")
                char_data['referenceUrl'] = correct_url
                fixed_count += 1

    if fixed_count > 0:
        # 保存修复后的项目信息
        with open(project_info_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        print(f"[SUCCESS] 已修复 {fixed_count} 个角色的URL，项目信息已保存")
        return True
    else:
        print(f"[INFO] 所有角色URL都是正确的，无需修复")
        return True

def main():
    """主函数"""
    base_dir = Path(__file__).parent
    video_projects_dir = base_dir / '视频项目'

    if not video_projects_dir.exists():
        print(f"[ERROR] 视频项目目录不存在: {video_projects_dir}")
        return

    # 遍历所有项目
    for project_dir in video_projects_dir.iterdir():
        if project_dir.is_dir():
            print(f"\n[PROJECT] 检查项目: {project_dir.name}")
            fix_character_image_urls(project_dir)

if __name__ == '__main__':
    main()
