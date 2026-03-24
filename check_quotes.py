with open('web/templates/pages/v2/fanqie-upload-v2.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查第 700-800 行
lines = content.split('\n')
for i in range(699, min(800, len(lines))):
    line = lines[i]
    # 检查是否有反引号（template literal）
    if '`' in line:
        # 统计反引号数量
        count = line.count('`')
        print(f'Line {i+1}: {count} backticks - {line[:100]}')
