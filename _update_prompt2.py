import json, pathlib

p = pathlib.Path('prompt_packages/default/market_driven/components/stage_review_prompts.json')
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

template = data['templates']['fix_prompt']['template']

# Replace the content preview and output format section
old = '''**原文内容（前800字供参考）：**
{original_content_preview}...

## 输出格式（必须严格遵守）
必须按以下格式返回，使用 `---标题---` 和 `---正文---` 分隔：'''

new = '''{core_setting_summary}

{tactical_context}

**原文内容（完整）：**
{original_content}

## 输出格式（必须严格遵守）
必须按以下格式返回，使用 `---标题---` 和 `---正文---` 分隔：'''

template = template.replace(old, new)

# Also update variables list
variables = data['templates']['fix_prompt']['variables']
if 'original_content_preview' in variables:
    variables[variables.index('original_content_preview')] = 'original_content'
if 'tactical_context' not in variables:
    variables.append('tactical_context')
if 'core_setting_summary' not in variables:
    variables.append('core_setting_summary')

data['templates']['fix_prompt']['template'] = template

# Update editor_system_prompt
old_sys = "你是专业的小说编辑，同时也是番茄小说平台算法合规专家。你的分析必须基于以下番茄核心指标：对话比例≥40%、爽点密度≥1.5/千字、情绪密度≥2.0/千字、章章有钩子、字数2000-2500。工作流程：1) 识别P0/P1/P2问题 2) 逐章修复 3) 验证。只输出JSON格式。"
new_sys = "你是专业的小说编辑，同时也是番茄小说平台算法合规专家。你的分析必须基于以下番茄核心指标：对话比例≥40%、爽点密度≥1.5/千字、情绪密度≥2.0/千字、章章有钩子、字数2000-2500。工作流程：1) 识别P0/P1/P2问题 2) 逐章修复 3) 验证。修复时必须严格遵守核心设定摘要和战术规划。输出格式：使用 `---标题---` 和 `---正文---` 分隔符。"
data['templates']['editor_system_prompt'] = new_sys

with open(p, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Updated')
