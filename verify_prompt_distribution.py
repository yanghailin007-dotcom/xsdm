# -*- coding: utf-8 -*-
"""
验证 System Prompt 和 User Prompt 的分布情况
分析V2六层架构中各层的内容和长度
"""

import sys
sys.path.insert(0, '.')

def analyze_v2_prompts():
    """分析V2架构提示词分布"""
    
    print("=" * 80)
    print("V2 六层架构 System Prompt vs User Prompt 分析")
    print("=" * 80)
    
    # 直接测试V2架构的提示词
    from web.services.market_driven.v2_architecture import PromptAssemblerV2, AssemblyContext
    
    assembler = PromptAssemblerV2("国运文")
    context = AssemblyContext(
        novel_title="开局扮演杀神白起",
        chapter_num=7,
        protagonist_name="苏辰",
        chapter_type="打脸章"
    )
    
    # 组装完整提示词
    full_prompt = assembler.assemble(context)
    
    print(f"\n✓ V2 提示词组装成功")
    print(f"  总长度: {len(full_prompt)} 字符")
    print(f"  总行数: {full_prompt.count(chr(10))} 行")
    
    # 分析各层
    print("\n" + "-" * 80)
    print("【六层架构内容分析】")
    print("-" * 80)
    
    layers = [
        ("Layer 1", "【Layer 1】核心设定"),
        ("Layer 2", "【Layer 2】战术规划"),
        ("Layer 3", "【Layer 3】题材技法"),
        ("Layer 4", "【Layer 4】文风技法"),
        ("Layer 5", "【Layer 5】AI约束"),
        ("Layer 6", "【Layer 6】自检清单")
    ]
    
    layer_contents = {}
    
    for layer_name, marker in layers:
        start = full_prompt.find(marker)
        if start != -1:
            # 找到该层结束位置（下一个Layer标记或文件末尾）
            end = len(full_prompt)
            for _, next_marker in layers:
                next_pos = full_prompt.find(next_marker, start + 1)
                if next_pos != -1 and next_pos < end:
                    end = next_pos
            
            content = full_prompt[start:end]
            layer_contents[layer_name] = content
            
            print(f"\n{layer_name}:")
            print(f"  长度: {len(content)} 字符")
            print(f"  占比: {len(content)/len(full_prompt)*100:.1f}%")
            
            # 显示前150字符摘要
            summary = content.replace('\n', ' ')[:150]
            print(f"  摘要: {summary}...")
    
    # 建议的System vs User分布
    print("\n" + "=" * 80)
    print("【建议的 System vs User Prompt 分配】")
    print("=" * 80)
    
    # 策略1: Layer 1-4 作为 System, Layer 5-6 作为 User
    system_layers_1 = ["Layer 1", "Layer 2", "Layer 3", "Layer 4"]
    user_layers_1 = ["Layer 5", "Layer 6"]
    
    print("\n策略1 (推荐):")
    print("  System Prompt (角色+规划+题材+文风):")
    system_len_1 = sum(len(layer_contents.get(l, "")) for l in system_layers_1)
    for layer in system_layers_1:
        content = layer_contents.get(layer, "")
        print(f"    - {layer}: {len(content)} 字符")
    print(f"  System Prompt 总计: {system_len_1} 字符 ({system_len_1/len(full_prompt)*100:.1f}%)")
    
    print("\n  User Prompt (约束+自检):")
    user_len_1 = sum(len(layer_contents.get(l, "")) for l in user_layers_1)
    for layer in user_layers_1:
        content = layer_contents.get(layer, "")
        print(f"    - {layer}: {len(content)} 字符")
    print(f"  User Prompt 总计: {user_len_1} 字符 ({user_len_1/len(full_prompt)*100:.1f}%)")
    
    # 策略2: 只有Layer 3作为System, 其他作为User
    print("\n" + "-" * 80)
    print("\n策略2 (保守):")
    print("  System Prompt (仅题材技法 - 核心分离):")
    system_len_2 = len(layer_contents.get("Layer 3", ""))
    print(f"    - Layer 3: {system_len_2} 字符")
    print(f"  System Prompt 总计: {system_len_2} 字符 ({system_len_2/len(full_prompt)*100:.1f}%)")
    
    print("\n  User Prompt (其他所有层):")
    user_len_2 = len(full_prompt) - system_len_2
    print(f"  User Prompt 总计: {user_len_2} 字符 ({user_len_2/len(full_prompt)*100:.1f}%)")
    
    # 与API限制对比
    print("\n" + "=" * 80)
    print("【与API限制对比】")
    print("=" * 80)
    
    print("\nOpenAI API建议:")
    print("  System Prompt: 理想 < 4000 字符, 最大 < 8000 字符")
    print("  User Prompt: 理想 < 8000 字符, 最大 < 12000 字符")
    print("  总计: 建议 < 12000 字符")
    
    print("\n策略1检查结果:")
    print(f"  System: {system_len_1} 字符 {'✓' if system_len_1 < 4000 else '⚠ 偏长' if system_len_1 < 8000 else '✗ 过长'}")
    print(f"  User: {user_len_1} 字符 {'✓' if user_len_1 < 8000 else '⚠ 偏长' if user_len_1 < 12000 else '✗ 过长'}")
    print(f"  总计: {len(full_prompt)} 字符 {'✓' if len(full_prompt) < 12000 else '⚠ 偏长'}")
    
    print("\n策略2检查结果:")
    print(f"  System: {system_len_2} 字符 {'✓ 理想' if system_len_2 < 4000 else '⚠'}")
    print(f"  User: {user_len_2} 字符 {'✓' if user_len_2 < 8000 else '⚠ 偏长' if user_len_2 < 12000 else '✗ 过长'}")
    print(f"  总计: {len(full_prompt)} 字符 {'✓' if len(full_prompt) < 12000 else '⚠ 偏长'}")
    
    # 关键内容检查
    print("\n" + "=" * 80)
    print("【关键内容检查】")
    print("=" * 80)
    
    checks = [
        ("国运文弹幕要求", "弹幕数量≥8条", "Layer 3"),
        ("情绪曲线", "虐(4)→急(7)→爽(9)→悬(7)", "Layer 5"),
        ("自检清单", "【Layer 6】自检清单", "Layer 6"),
        ("禁止起承转合", "严禁使用传统的", "Layer 5"),
    ]
    
    for check_name, keyword, expected_layer in checks:
        found = keyword in full_prompt
        layer_found = expected_layer in str([k for k, v in layer_contents.items() if keyword in v])
        print(f"  {check_name}: {'✓' if found else '✗'} (在{expected_layer if layer_found else '未知'})")
    
    # 输出到文件以便查看
    with open("docs/v2_prompt_analysis.txt", "w", encoding="utf-8") as f:
        f.write("V2 六层架构提示词分析\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"总长度: {len(full_prompt)} 字符\n")
        f.write(f"总行数: {full_prompt.count(chr(10))} 行\n\n")
        f.write("各层详情:\n")
        for layer_name, content in layer_contents.items():
            f.write(f"\n{layer_name}: {len(content)} 字符\n")
            f.write("-" * 40 + "\n")
            f.write(content[:500] + "...\n" if len(content) > 500 else content + "\n")
    
    print("\n" + "=" * 80)
    print("详细分析已保存到: docs/v2_prompt_analysis.txt")
    print("=" * 80)

if __name__ == "__main__":
    analyze_v2_prompts()
