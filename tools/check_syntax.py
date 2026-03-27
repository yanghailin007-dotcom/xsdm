import re

with open('web/templates/project-management.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取所有 script 内容
scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)

print(f"Found {len(scripts)} script blocks\n")

for i, script in enumerate(scripts):
    lines = script.split('\n')
    print(f"=== Script {i+1}: {len(lines)} lines ===")
    
    # 检查每行的引号匹配
    for j, line in enumerate(lines, 1):
        # 计算各种引号
        single_quote = line.count("'")
        double_quote = line.count('"')
        backtick = line.count('`')
        
        # 忽略转义的引号
        escaped_single = line.count("\\'")
        escaped_double = line.count('\\"')
        
        effective_single = single_quote - escaped_single
        effective_double = double_quote - escaped_double
        
        # 如果在模板字符串中，检查 ${} 是否匹配
        if '`' in line:
            # 检查是否有未闭合的 ${
            open_braces = line.count('${')
            close_braces = line.count('}')
            
            # 简单检查：如果这一行有 ${ 但可能有问题
            if '${' in line:
                # 检查是否在新行开始模板字符串但未结束
                if line.count('`') == 1:
                    # 可能是多行模板字符串的开始
                    pass
        
        # 检查可疑模式：逗号后直接跟字符串
        if re.search(r',\s*["\']', line) and not re.search(r',\s*["\'][^"\']*["\']\s*[\+\)]', line):
            if 'data-i18n' not in line and 'onclick' not in line:
                print(f"  Line {j}: Possible issue - comma followed by string")
                print(f"    {line[:100]}")

print("\n=== Checking for template literal issues ===")

# 检查模板字符串嵌套问题
for i, script in enumerate(scripts):
    lines = script.split('\n')
    in_template = False
    template_start_line = 0
    
    for j, line in enumerate(lines, 1):
        backticks = line.count('`')
        
        # 处理转义的 backtick
        escaped_backticks = line.count('\\`')
        effective_backticks = backticks - escaped_backticks
        
        if effective_backticks % 2 == 1:
            if not in_template:
                in_template = True
                template_start_line = j
            else:
                in_template = False
        
        # 如果在模板字符串中，检查 ${} 匹配
        if in_template and '${' in line:
            # 计算这一行中 ${ 和 } 的数量（不包括 ${} 中的）
            open_count = line.count('${')
            # 这需要更复杂的逻辑...

# 查找特定的错误模式
print("\n=== Looking for specific error patterns ===")

# 1. 检查是否有对象属性后面直接跟字符串
pattern1 = r'}\s*["\']'
matches1 = re.findall(pattern1, content)
if matches1:
    print(f"Found {len(matches1)} cases of '}} followed by string'")

# 2. 检查数组/对象后的字符串
for i, script in enumerate(scripts):
    lines = script.split('\n')
    for j, line in enumerate(lines, 1):
        # 检查是否有语法错误模式
        stripped = line.strip()
        
        # 检查是否有不正常的字符串连接
        if re.search(r'["\']\s*["\']', stripped) and '+' not in stripped:
            # 可能是两个字符串字面量相邻
            if 'data-i18n' not in stripped:
                print(f"Script {i+1}, Line {j}: Adjacent strings")
                print(f"  {stripped[:80]}")
