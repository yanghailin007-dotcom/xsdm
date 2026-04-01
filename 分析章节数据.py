import json

with open('小说项目/yanghailin/国运：扮演瞎子，队友白月魁/.chapter_extractions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"总共 {len(data)} 章数据")

# 统计每章的关键信息
for i, ch in enumerate(data[:6]):
    print(f"\n=== 第{i+1}章 ===")
    print(f"关键事件: {ch['key_event']['title']}")
    print(f"影响等级: {ch['key_event']['impact']}")
    
    nc = ch.get('new_characters') or []
    nh = ch.get('new_hooks') or []
    rh = ch.get('resolved_hooks') or []
    wc = ch.get('world_changes') or []
    
    print(f"新角色: {len(nc)}个")
    print(f"角色变化: {len(ch.get('character_changes') or [])}个")
    print(f"新钩子: {len(nh)}个")
    print(f"已解钩子: {len(rh)}个")
    print(f"世界变化: {len(wc)}个")
    
    if ch.get('power_progression'):
        pp = ch['power_progression']
        na = pp.get('protagonist_new_abilities') or []
        print(f"新能力: {len(na)}个")
        print(f"实力变化: {pp.get('power_level_change', 'N/A')}")
    
    print("---")
    print(f"钩子详情:")
    for h in nh:
        print(f"  - [{h.get('priority','?')}] {h.get('type')}: {h.get('content')[:50]}...")
