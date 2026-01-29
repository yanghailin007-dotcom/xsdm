"""
重新整理视频项目目录为正确结构
结构: 视频项目/{小说名}/{分集}/{角色名}.png
"""
import os
import shutil
from pathlib import Path

def sanitize(name):
    """清理文件名"""
    for char in ['：', ':', '"', '/', '\\', '|', '?', '、', '？', '！']:
        name = name.replace(char, '_')
    return name.strip('_')

# 源目录和目标目录
source = Path('D:/work6.06/视频项目')
target = Path('D:/work6.06/视频项目_新')

# 创建目标目录
target.mkdir(exist_ok=True)

# 定义项目和分集映射
projects = {
    '心声泄露_我成了家族老阴比': {
        '第一集': [],  # 林长生、林青竹
    },
    '吞噬万界_从一把生锈铁剑开始': {
        '默认': [],  # 赤、姜清歌
    },
}

# 扫描所有PNG文件
all_pngs = list(source.rglob('*.png'))
print(f"找到 {len(all_pngs)} 个PNG文件\n")

for png in all_pngs:
    filename = png.name
    full_path = str(png)

    # 判断属于哪个项目和分集
    target_project = None
    target_episode = None
    target_character = None

    # 心声泄露项目 - 第一集
    if '林长生' in filename and '心声' in full_path:
        target_project = '心声泄露_我成了家族老阴比'
        target_episode = '第一集'
        target_character = '林长生'
    elif '林青竹' in filename and '心声' in full_path:
        target_project = '心声泄露_我成了家族老阴比'
        target_episode = '第一集'
        target_character = '林青竹'

    # 吞噬万界项目 - 默认分集
    elif '姜清歌' in filename or 'Jiang_Qingge' in filename:
        target_project = '吞噬万界_从一把生锈铁剑开始'
        target_episode = '默认'
        target_character = '姜清歌'
    elif '_赤_' in filename or '赤_(Chi)' in filename or '(Chi)' in filename:
        target_project = '吞噬万界_从一把生锈铁剑开始'
        target_episode = '默认'
        target_character = '赤'

    if target_project and target_character:
        # 目标路径: 视频项目/{小说名}/{分集}/
        project_dir = target / sanitize(target_project) / sanitize(target_episode)
        project_dir.mkdir(parents=True, exist_ok=True)

        # 目标文件名: {角色名}.png
        base_name = sanitize(target_character)
        target_file = project_dir / f"{base_name}.png"

        # 如果已存在，添加序号
        counter = 1
        while target_file.exists():
            target_file = project_dir / f"{base_name}_{counter}.png"
            counter += 1

        # 复制文件
        shutil.copy2(png, target_file)
        print(f"{target_project}/{target_episode}/{target_character}.png")
    else:
        print(f"跳过: {filename}")

# 显示结果
print(f"\n=== 最终结构 ===")
for proj_dir in sorted(target.iterdir()):
    if proj_dir.is_dir():
        print(f"\n{proj_dir.name}/")
        for ep_dir in sorted(proj_dir.iterdir()):
            if ep_dir.is_dir():
                print(f"  {ep_dir.name}/")
                for f in sorted(ep_dir.glob('*.png')):
                    print(f"    {f.name}")

print(f"\n总文件数: {sum(len(list(p.rglob('*.png'))) for p in target.iterdir() if p.is_dir())}")
