import re

with open('web/api/short_drama_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换第一个同步函数中的角色名处理
old_code1 = '''                char_name = char.get('name')
                # 清理角色名中的非法字符
                char_name = _sanitize_filename(char_name)
                if char_name and char_name not in characters_assets:'''

new_code1 = '''                char_name = char.get('name')
                # 保留原始名称用于显示
                original_name = char_name
                # 清理角色名中的非法字符（仅用于内部键）
                safe_name = _sanitize_filename(char_name)
                if safe_name and safe_name not in characters_assets:'''

if old_code1 in content:
    content = content.replace(old_code1, new_code1, 1)  # 只替换第一个
    print('First replacement done')
else:
    print('First pattern not found')

# 替换 characters_assets[char_name] = {
old_code2 = '''                    characters_assets[char_name] = {
                        'id': str(uuid.uuid4())[:8],
                        'name': char_name,'''

new_code2 = '''                    characters_assets[safe_name] = {
                        'id': str(uuid.uuid4())[:8],
                        'name': original_name,'''

if old_code2 in content:
    content = content.replace(old_code2, new_code2, 1)
    print('Second replacement done')
else:
    print('Second pattern not found')

with open('web/api/short_drama_api.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('File saved')
