import json, pathlib

p = pathlib.Path('prompt_packages/default/market_driven/components/stage_review_prompts.json')
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

template = data['templates']['fix_prompt']['template']

# Replace output format section by finding markers
idx = template.find('## 输出格式')
if idx != -1:
    before = template[:idx]
    after_idx = template.find('{self_check_list}')
    after = template[after_idx:]
    new_middle = '''## 输出格式（必须严格遵守）
必须按以下格式返回，使用 `---标题---` 和 `---正文---` 分隔：

---标题---
章节标题（8-14字，不含第X章前缀）

---正文---
章节正文内容（段落之间保留换行，不含标题）

**重要：**
- 标题必须放在 `---标题---` 后面
- 正文必须放在 `---正文---` 后面
- 禁止只返回纯文本
- 正文开头禁止写"第X章：XXX"
- 段落之间必须保留换行符

'''
    template = before + new_middle + after
    data['templates']['fix_prompt']['template'] = template
    print('Replaced fix_prompt template via slice')
else:
    print('Could not find output format section')

# Update self_check_list
self_template = data['templates']['self_check_list']['template']
self_template = self_template.replace('统计content字段字数', '统计---正文---部分字数')
self_template = self_template.replace('content字数是否', '正文字数是否')
self_template = self_template.replace('title字段是否正确提取', '标题是否正确提取')
self_template = self_template.replace('content字段是否不包含标题重复', '正文是否不包含标题重复')
self_template = self_template.replace('理想范围：content 2000-2500字', '理想范围：正文 2000-2500字')
self_template = self_template.replace('硬性上限：content绝对不能超过2500字', '硬性上限：正文绝对不能超过2500字')
# Add newline check if not present
if '换行符' not in self_template:
    self_template = self_template.replace(
        '- [ ] 理想范围：正文 2000-2500字',
        '- [ ] 段落之间是否保留了换行符？\n- [ ] 理想范围：正文 2000-2500字'
    )
data['templates']['self_check_list']['template'] = self_template
print('Updated self_check_list')

with open(p, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Saved')
