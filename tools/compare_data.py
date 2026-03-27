import json

# 读取debug_responses中的原始响应
with open('debug_responses/raw_MDC-MDC-3E929DC8_轮次3_1_response_1774449006.txt', 'r', encoding='utf-8') as f:
    raw_content = f.read()
    # 去掉开头的 ```json 和结尾的 ```
    raw_content = raw_content.strip()
    if raw_content.startswith('```json'):
        raw_content = raw_content[7:]
    if raw_content.endswith('```'):
        raw_content = raw_content[:-3]
    raw_data = json.loads(raw_content.strip())

# 读取保存的角色设计
with open('小说项目/具现石油，龙国暴富/phase_one_products/角色设计.json', 'r', encoding='utf-8') as f:
    saved_data = json.load(f)

# 比较两个数据结构
print('=== 比较角色数据结构 ===')
print('原始响应 protagonist keys:', list(raw_data.get('protagonist', {}).keys()))
print('保存文件 protagonist keys:', list(saved_data.get('protagonist', {}).keys()))
print()
print('原始响应 core_allies 数量:', len(raw_data.get('core_allies', [])))
print('保存文件 core_allies 数量:', len(saved_data.get('core_allies', [])))
print()
print('原始响应 main_antagonists keys:', list(raw_data.get('main_antagonists', {}).keys()))
print('保存文件 main_antagonists keys:', list(saved_data.get('main_antagonists', {}).keys()))
print()

# 比较内容是否相同
if raw_data == saved_data:
    print('✓ 数据完全一致！')
else:
    print('✗ 数据不一致！')
    # 找出差异
    for key in raw_data:
        if key not in saved_data:
            print(f'  - 保存文件缺少 key: {key}')
        elif raw_data[key] != saved_data[key]:
            print(f'  - key {key} 的值不同')
    for key in saved_data:
        if key not in raw_data:
            print(f'  - 保存文件多了 key: {key}')
