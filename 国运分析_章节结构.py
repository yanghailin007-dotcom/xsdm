# -*- coding: utf-8 -*-
import json
import sys

# 设置输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('小说项目/yanghailin/国运：扮演瞎子，队友白月魁/.chapter_extractions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 60)
print("《国运：扮演瞎子，队友白月魁》前6章结构分析")
print("=" * 60)

# 1. 核心设定梳理
print("\n【一、核心设定检查】")
print("-" * 40)

# 收集所有能力变化
abilities = []
acting_progress = []
for i, ch in enumerate(data[:6]):
    if ch.get('power_progression'):
        pp = ch['power_progression']
        acting_progress.append({
            'chapter': i+1,
            'change': pp.get('power_level_change', 'N/A')
        })
        for a in (pp.get('protagonist_new_abilities') or []):
            abilities.append(f"C{i+1}: {a}")

print(f"\n能力成长轨迹（共{len(abilities)}个节点）:")
for a in abilities:
    print(f"  - {a}")

# 2. 钩子分析
print("\n【二、钩子埋设与回收分析】")
print("-" * 40)

for i, ch in enumerate(data[:6]):
    hooks = ch.get('new_hooks') or []
    resolved = ch.get('resolved_hooks') or []
    
    print(f"\n第{i+1}章:")
    print(f"  新埋钩子: {len(hooks)}个")
    for h in hooks:
        print(f"    [{h.get('priority','?')}] {h.get('type')}")
    print(f"  回收钩子: {len(resolved)}个")

# 3. 情绪曲线检查
print("\n【三、情绪曲线设计】")
print("-" * 40)

emotion_curve = [
    (1, "压抑", 9, "盲者被选，举国绝望"),
    (2, "嘲讽→反转", 8, "击杀F级蟒蛇，初显实力"),
    (3, "震惊", 9, "扮猪吃虎，瞬杀三怪"),
    (4, "震撼", 10, "引天雷秒杀S级凶兽，震惊全球"),
    (5, "期待→压抑", 8, "完成SS级成就，排名狂飙；遭遇S级陷阱"),
    (6, "危机", 8, "击杀B级选手，识破S级陷阱")
]

print("\n情绪设计:")
for ch, emotion, intensity, desc in emotion_curve:
    bar = "*" * (intensity // 2)
    print(f"  C{ch}: [{bar:<5}] {intensity}/10 | {emotion} | {desc}")

# 4. 爽点密度分析
print("\n【四、爽点(打脸/震惊/反转)密度统计】")
print("-" * 40)

shuang_points = [
    (1, "系统绑定", "金手指激活", "中"),
    (2, "击杀蟒蛇", "隐藏实力首次验证", "中"),
    (3, "瞬杀三怪", "扮猪吃虎，震惊直播间", "高"),
    (4, "秒杀S级", "引天雷，全球震惊", "极高"),
    (5, "SS成就", "完成越级杀戮，国运暴涨", "高"),
    (6, "反杀选手", "识破陷阱，击杀B级", "中")
]

print("\n爽点分布:")
for ch, point, effect, level in shuang_points:
    print(f"  C{ch}: [{level}] {point} - {effect}")

# 5. 爽点间隔分析
print("\n【五、爽点节奏分析】")
print("-" * 40)
print("""
第1章: 压抑铺垫 -> 系统激活 (延迟满足)
第2章: 小型验证 (F级击杀) -> 建立期待
第3章: 第一次高潮 (瞬杀三怪) <- 间隔2章
第4章: 超高潮 (S级秒杀) <- 连续高潮
第5章: SS成就 + 新危机 <- 张弛有度
第6章: 连续战斗 <- 节奏过密

分析: 前4章节奏优秀(压抑->小爽->大爽->超爽)
      第5-6章连续战斗，需要加入"情绪缓冲"
""")

# 6. 问题诊断
print("【六、问题诊断】")
print("-" * 40)
print("""
1. [角色关系]白月魁戏份不足
   - 6章中仅有3次态度转变记录
   - 缺乏深度互动和羁绊建立

2. [反派塑造]反龙联盟脸谱化
   - 约翰、佐藤等仅作为"嘲讽工具人"
   - 缺乏有魅力的反派角色

3. [地图探索]场景单一
   - 6章全部在第一区域(沙漠)
   - 缺乏环境变化和探索乐趣

4. [直播互动]水友弹幕套路化
   - "龙国完了->苏白牛逼"循环重复
   - 缺乏有特色的弹幕梗

5. [扮演出戏风险]
   - 多次高压击杀后仍维持"盲人"人设
   - 缺乏合理的"演技维持"情节
""")

# 7. 与番茄头部作品对比
print("【七、与番茄头部国运文对比】")
print("-" * 40)
print("""
维度          | 本作现状      | 头部标准      | 差距
--------------|---------------|---------------|------------------
首章Hook      | ****         | *****        | 系统提示稍晚
金手指爽感    | *****        | ****         | 碾压级
打脸频率      | ****         | *****        | 第6章偏密
角色羁绊      | ***          | ****         | 白月魁戏份少
世界展开      | ***          | ****         | 地图单一
情绪曲线      | ****         | *****        | 中后段偏平

综合评分: 82/100 (良好，有爆款潜力)
""")
