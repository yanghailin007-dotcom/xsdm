import re

with open('web/templates/phase-two-generation-backup.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 提取 project-select-card 相关的 CSS
# 查找 <style> 标签内的内容
style_matches = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)

print(f"Found {len(style_matches)} style blocks")

# 查找包含 project-select-card 的样式块
for i, style in enumerate(style_matches):
    if 'project-select-card' in style:
        print(f"\n=== Style block {i} contains project-select-card ===")
        # 提取相关部分
        lines = style.split('\n')
        for line in lines:
            if 'project-select-card' in line or 'project-title' in line or 'project-stats' in line or 'project-stat' in line:
                print(line.strip())
