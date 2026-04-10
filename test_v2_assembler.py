# -*- coding: utf-8 -*-
"""
测试 V2 提示词组装器
"""

import sys
sys.path.insert(0, 'web/services/market_driven')

from v2_architecture.prompt_assembler_v2 import PromptAssemblerV2, AssemblyContext

print("=" * 80)
print("测试 V2 提示词组装器")
print("=" * 80)

# 测试国运文+打脸章
print("\n\n【测试：国运文 + 打脸章】")
print("-" * 80)

assembler = PromptAssemblerV2("国运文")

context = AssemblyContext(
    novel_title="开局扮演杀神白起",
    chapter_num=7,
    protagonist_name="苏辰",
    chapter_type="打脸章"
)

prompt = assembler.assemble(context)

# 输出前2000字符
print(prompt[:2000])
print("...")
print(f"\n总长度: {len(prompt)} 字符")

# 验证关键内容
print("\n验证:")
checks = [
    ("Layer 1", "【Layer 1】核心设定"),
    ("Layer 3", "【Layer 3】题材技法"),
    ("情绪曲线", "虐(4)→急(7)→爽(9)→悬(7)"),
    ("Layer 6", "【Layer 6】自检清单"),
    ("弹幕要求", "弹幕数量≥8条"),
]

for name, keyword in checks:
    found = keyword in prompt
    print(f"  {name}: {'OK' if found else 'FAIL'}")

# 保存到文件
with open("docs/demo_v2_国运文.txt", "w", encoding="utf-8") as f:
    f.write(prompt)
print("\n已保存到: docs/demo_v2_国运文.txt")

# 测试神豪文
print("\n\n【测试：神豪文 + 收获章】")
print("-" * 80)

assembler2 = PromptAssemblerV2("神豪文")
context2 = AssemblyContext(
    novel_title="开局消费百亿",
    chapter_num=7,
    protagonist_name="陈默",
    chapter_type="收获章"
)

prompt2 = assembler2.assemble(context2)

print(f"总长度: {len(prompt2)} 字符")

# 验证关键内容
print("\n验证:")
checks2 = [
    ("Layer 1", "【Layer 1】核心设定"),
    ("金钱规范", "精确到小数点后2位"),
    ("返利提示", "恭喜宿主消费"),
    ("无弹幕", "弹幕数量≥8条" not in prompt2),
]

for name, check in checks2:
    if isinstance(check, str):
        found = check in prompt2
    else:
        found = check  # boolean
    print(f"  {name}: {'OK' if found else 'FAIL'}")

# 保存到文件
with open("docs/demo_v2_神豪文.txt", "w", encoding="utf-8") as f:
    f.write(prompt2)
print("\n已保存到: docs/demo_v2_神豪文.txt")

print("\n" + "=" * 80)
print("测试完成！")
print("=" * 80)
