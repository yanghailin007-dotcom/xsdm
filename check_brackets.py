with open('web/templates/pages/v2/fanqie-upload-v2.html', 'r', encoding='utf-8') as f:
    content = f.read()

js_start = content.find('<script>')
js_end = content.find('</script>', js_start)
js_code = content[js_start:js_end]

# 简单计数
paren_open = js_code.count('(')
paren_close = js_code.count(')')
brace_open = js_code.count('{')
brace_close = js_code.count('}')
bracket_open = js_code.count('[')
bracket_close = js_code.count(']')

print(f'Parentheses: open={paren_open}, close={paren_close}, diff={paren_open - paren_close}')
print(f'Braces: open={brace_open}, close={brace_close}, diff={brace_open - brace_close}')
print(f'Brackets: open={bracket_open}, close={bracket_close}, diff={bracket_open - bracket_close}')
