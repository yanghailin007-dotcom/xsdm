content = open('web/services/market_driven/chapter_prompt_optimizer_v2.py', 'r', encoding='utf-8').read()

# 修复f-string嵌套问题
old_text = '''if catchphrases:
                parts.append(f"\\n标志性台词：{' | '.join([f'\\"{c}\\"' for c in catchphrases[:3]])}")'''

new_text = '''if catchphrases:
                quotes = ' | '.join(['"' + str(c) + '"' for c in catchphrases[:3]])
                parts.append(f"\\n标志性台词：{quotes}")'''

if old_text in content:
    content = content.replace(old_text, new_text)
    open('web/services/market_driven/chapter_prompt_optimizer_v2.py', 'w', encoding='utf-8').write(content)
    print('Fixed f-string nesting!')
else:
    print('Pattern not found, checking file...')
    # 打印第165-175行看看
    lines = content.split('\n')
    for i, line in enumerate(lines[164:175], 165):
        print(f"{i}: {repr(line)}")
