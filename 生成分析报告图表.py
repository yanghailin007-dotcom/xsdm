# -*- coding: utf-8 -*-
import json
import os
import sys
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

print("正在生成分析报告图表...")

# 数据准备
chapters = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6']

# 1. 对话比例对比
dialogue_ratio = [11.1, 14.2, 21.4, 15.6, 21.5, 16.3]
tomato_standard = [50] * 6

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('《国运：扮演瞎子，队友白月魁》前6章质量分析', fontsize=16, fontweight='bold')

# 图1: 对话比例
ax1 = axes[0, 0]
x = range(len(chapters))
width = 0.35
ax1.bar([i - width/2 for i in x], dialogue_ratio, width, label='本作', color='steelblue')
ax1.bar([i + width/2 for i in x], tomato_standard, width, label='番茄标准(50%)', color='orange', alpha=0.7)
ax1.set_ylabel('对话比例(%)')
ax1.set_title('对话比例对比')
ax1.set_xticks(x)
ax1.set_xticklabels(chapters)
ax1.legend()
ax1.axhline(y=50, color='r', linestyle='--', alpha=0.5)

# 图2: 爽点密度
ax2 = axes[0, 1]
shuang_density = [0.3, 0.8, 0.8, 2.9, 1.4, 0.4]
ax2.plot(chapters, shuang_density, 'o-', linewidth=2, markersize=8, color='green', label='本作爽点密度')
ax2.axhline(y=1.5, color='r', linestyle='--', alpha=0.7, label='番茄标准(1.5/千字)')
ax2.fill_between(chapters, shuang_density, alpha=0.3)
ax2.set_ylabel('爽点密度(次/千字)')
ax2.set_title('爽点密度走势')
ax2.legend()

# 图3: 情绪词分布
ax3 = axes[1, 0]
emotion_data = {
    '震惊': [0, 1, 1, 3, 0, 0],
    '恐惧': [1, 1, 3, 2, 1, 0],
    '压抑': [9, 1, 2, 1, 0, 2],
    '爽感': [0, 1, 2, 0, 0, 0],
    '兴奋': [0, 2, 0, 1, 0, 0]
}
bottom = [0] * 6
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
for i, (emotion, values) in enumerate(emotion_data.items()):
    ax3.bar(chapters, values, bottom=bottom, label=emotion, color=colors[i])
    bottom = [b + v for b, v in zip(bottom, values)]
ax3.set_ylabel('情绪词出现次数')
ax3.set_title('情绪词分布')
ax3.legend(loc='upper right', fontsize=8)

# 图4: 综合评分雷达图
ax4 = axes[1, 1]
categories = ['核心设定', '金手指爽感', '节奏把控', '对话互动', '情绪调动', '钩子设计']
values = [90, 95, 75, 55, 70, 65]
values += values[:1]  # 闭合

angles = [n / float(len(categories)) * 2 * 3.14159 for n in range(len(categories))]
angles += angles[:1]

ax4 = plt.subplot(2, 2, 4, polar=True)
ax4.plot(angles, values, 'o-', linewidth=2, color='purple')
ax4.fill(angles, values, alpha=0.25, color='purple')
ax4.set_xticks(angles[:-1])
ax4.set_xticklabels(categories)
ax4.set_ylim(0, 100)
ax4.set_title('综合评分雷达图 (总分:77.25)', y=1.08)

plt.tight_layout()
plt.savefig('国运小说_质量分析报告.png', dpi=150, bbox_inches='tight')
print("图表已保存: 国运小说_质量分析报告.png")

# 生成情绪曲线图
fig2, ax = plt.subplots(figsize=(12, 5))
emotion_curve = [9, 8, 9, 10, 8, 8]
emotion_labels = ['压抑', '嘲讽→反转', '震惊', '震撼', '期待→压抑', '危机']

ax.plot(chapters, emotion_curve, 'o-', linewidth=3, markersize=12, color='red')
ax.fill_between(chapters, emotion_curve, alpha=0.3, color='red')

# 添加情绪标签
for i, (ch, val, label) in enumerate(zip(chapters, emotion_curve, emotion_labels)):
    ax.annotate(label, (i, val), textcoords="offset points", xytext=(0,10), ha='center', fontsize=9)

ax.set_ylabel('情绪强度(0-10)')
ax.set_title('前6章情绪曲线设计')
ax.set_ylim(0, 12)
ax.axhline(y=7, color='gray', linestyle='--', alpha=0.5, label='高潮阈值')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('国运小说_情绪曲线.png', dpi=150, bbox_inches='tight')
print("图表已保存: 国运小说_情绪曲线.png")

print("\n分析完成！")
