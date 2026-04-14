import json, pathlib
p = pathlib.Path('prompt_packages/default/market_driven/components/stage_review_prompts.json')
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

fix = data['templates']['fix_prompt']['template']
print("="*60)
print("FIX PROMPT TEMPLATE:")
print("="*60)
print(fix)
print()

word_count = data['templates'].get('word_count_constraints', {}).get('template', '')
print("="*60)
print("WORD COUNT CONSTRAINTS:")
print("="*60)
print(word_count)
