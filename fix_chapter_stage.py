#!/usr/bin/env python3
import json

with open('prompt_packages/_base/system_components/chapter_stage.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

old_format = "## ⚠️ 输出格式\n直接输出章节正文，不要分析、不要总结、不要标注。\n字数：2000-2500字"

new_format = """## ⚠️ 输出格式
必须按以下格式返回，使用 ---标题--- 和 ---正文--- 分隔：

---标题---
章节标题（8-14字，概括核心爽点，不要第X章前缀）
---正文---
章节正文内容（2000-2500字，直接写场景，绝对禁止在开头写第X章标题）

⚠️ 格式警告：
- 必须严格按照上述分隔符格式返回
- 标题只放在---标题---后面，不要重复放在正文里
- 正文开头绝对禁止写\"第X章：XXX\""""

data['template'] = data['template'].replace(old_format, new_format)

with open('prompt_packages/_base/system_components/chapter_stage.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('✅ chapter_stage.json 已更新')

# 验证
if '---标题---' in data['template'] and '---正文---' in data['template']:
    print('✅ 验证通过：包含分隔符格式要求')
else:
    print('❌ 验证失败')
