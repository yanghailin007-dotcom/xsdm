import json

def read_debug_response(filepath):
    """读取debug_responses中的原始响应，提取JSON内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 去掉markdown代码块标记
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    
    return json.loads(content.strip())

def read_saved_file(filepath):
    """读取保存的JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_dicts(d1, d2, path=""):
    """递归比较两个字典，返回差异列表"""
    differences = []
    
    if type(d1) != type(d2):
        differences.append(f"{path}: Type mismatch ({type(d1)} vs {type(d2)})")
        return differences
    
    if isinstance(d1, dict):
        keys1 = set(d1.keys())
        keys2 = set(d2.keys())
        
        if keys1 != keys2:
            only_in_1 = keys1 - keys2
            only_in_2 = keys2 - keys1
            if only_in_1:
                differences.append(f"{path}: Keys only in debug: {only_in_1}")
            if only_in_2:
                differences.append(f"{path}: Keys only in saved: {only_in_2}")
        
        for key in keys1 & keys2:
            differences.extend(compare_dicts(d1[key], d2[key], f"{path}.{key}"))
    
    elif isinstance(d1, list):
        if len(d1) != len(d2):
            differences.append(f"{path}: Length mismatch ({len(d1)} vs {len(d2)})")
        else:
            for i, (item1, item2) in enumerate(zip(d1, d2)):
                differences.extend(compare_dicts(item1, item2, f"{path}[{i}]"))
    
    else:
        if d1 != d2:
            differences.append(f"{path}: Value mismatch ({repr(d1)[:50]} vs {repr(d2)[:50]})")
    
    return differences

if __name__ == "__main__":
    debug_file = 'debug_responses/raw_MDC-MDC-3E929DC8_轮次3_1_response_1774449006.txt'
    saved_file = '小说项目/具现石油，龙国暴富/phase_one_products/角色设计.json'
    
    try:
        debug_data = read_debug_response(debug_file)
        saved_data = read_saved_file(saved_file)
        
        differences = compare_dicts(debug_data, saved_data)
        
        if differences:
            print("发现差异:")
            for diff in differences[:20]:  # 只显示前20个差异
                print(f"  - {diff}")
            if len(differences) > 20:
                print(f"  ... 还有 {len(differences) - 20} 个差异")
        else:
            print("数据完全一致！")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
