import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('web/templates/pages/v2/chapter-generation.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: volRegex
content = content.replace(
    'const volRegex = /^#{1,3}\\s*绗琝s*(\\d+)\\s*鍗?g;',
    'const volRegex = /^#{1,3}\\s*第\\s*(\\d+)\\s*卷/g;'
)

# Fix 2: headingRegex
content = content.replace(
    'const headingRegex = /### 绗?[涓€浜屼笁鍥涗簲鍏竷鍏節鍗佺櫨鍗冧竾浜縗d]+)绔燶s*(.*?)\\n/g;',
    'const headingRegex = /### 第([一二三四五六七八九十百千万亿\\d]+)章\\s*(.*?)\\n/g;'
)

# Fix 3: regex on line 2568
content = content.replace(
    'const regex = /### 绗?[涓€浜屼笁鍥涗簲鍏竷鍏節鍗佺櫨鍗冧竾浜縗d]+)绔燶s*(.*?)\\n/;',
    'const regex = /### 第([一二三四五六七八九十百千万亿\\d]+)章\\s*(.*?)\\n/;'
)

# Fix 4: comment on line 1543
content = content.replace(
    '// 椤圭洰/鍗峰彿/妯″瀷/绔犺妭璁剧疆鍒囨崲鏃惰嚜鍔ㄤ繚瀛?+ 鍔犺浇缁嗙翰',
    '// 项目/卷号/模型/章节设置切换时自动保存 + 加载细纲'
)

# Fix 5: comment on line 1623
content = content.replace(
    '// 鍖归厤 \"# 绗琗鍗风矖绾? 鎴?\"## 绗琗鍗? 鎴?\"### 绗琗鍗?',
    '// 匹配 \"# 第X卷粗纲\" 或 \"## 第X卷\" 或 \"### 第X卷\"'
)

# Check remaining
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if '绗' in line or '鍗' in line or '涓' in line:
        print(f'Line {i}: {line.rstrip()[:120]}')

with open('web/templates/pages/v2/chapter-generation.html', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print('Done')
