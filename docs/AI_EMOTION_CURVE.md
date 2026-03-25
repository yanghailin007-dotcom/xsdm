# AI生成个性化情绪曲线

## 核心改进

### 旧方案（固定模板）
```python
# 所有神豪文都用同一个模板
神豪文模板 = [
    {"ch": 1, "emotion": "压抑", "intensity": 9, ...},
    {"ch": 2, "emotion": "希望", "intensity": 6, ...},
    ...
]
# 问题：千篇一律，不能适应具体题材
```

### 新方案（AI个性化生成）
```python
# 一阶段产物中包含AI生成的情绪曲线
phase_one_products = {
    "emotion_curve": [
        {"ch": 1, "emotion": "压抑", "intensity": 9, 
         "beat_type": "钩子", "event": "被裁员+负债+女友分手", 
         "purpose": "外卖员绝望开局"},
        {"ch": 2, "emotion": "希望", "intensity": 6,
         "beat_type": "转折", "event": "神级扮演系统绑定",
         "purpose": "可以选择扮演诸天人物"},
        {"ch": 3, "emotion": "爽快", "intensity": 7,
         "beat_type": "爽点", "event": "扮演李逍遥，首次御剑",
         "purpose": "禁地首杀，全国震惊"},
        ...  # 根据具体题材个性化生成
    ]
}
```

## 实现流程

```
一阶段产物生成
    ↓
PhaseOneGenerator.generate_all_products()
    ├─ 原有产物：世界观、角色、势力...
    └─ 新增产物：emotion_curve（AI生成）
        ↓
    EmotionCurveGenerator.generate_curve()
        ↓
    AI分析题材特点 → 生成个性化情绪曲线
        ↓
保存到 phase_one_products["emotion_curve"]

二阶段章节生成
    ↓
BatchChapterGenerator.generate_with_state_manager()
    ↓
create_emotion_flow(phase_one_products=phase_one_products)
    ↓
优先加载AI生成的情绪曲线
    ↓
每章生成时传入对应的情绪节拍
```

## AI生成Prompt示例

```python
CURVE_GENERATION_PROMPT = """
为一部{genre}小说设计情绪曲线（心电图模式）。

题材：{genre}
核心套路：{core_formula}
总章节数：{total_chapters}章
主角：{protagonist_name}，{protagonist_identity}

【关键节拍要求】
基于套路分析，以下章节必须有特定情绪：
- 第1章：必须是"压抑→震惊"（绝望开局+系统觉醒）
- 第3章左右：必须有"爽快"（第一次打脸）
- 第8-10章：必须有"震惊"（身份小曝光）
...

【设计原则】
1. 像心电图一样起伏，不能平
2. 不能连续3章强度低于6
3. 每3-5章必须有一个爽点或震惊
4. 大高潮(9)后必须有1章缓冲(5-6)
5. 章章有钩子或爽点或期待

【输出格式】
{
  "curve": [
    {"ch": 1, "emotion": "压抑", "intensity": 9, 
     "beat_type": "钩子", "event": "具体事件", "purpose": "作用"},
    ...
  ]
}

注意：
- 根据题材特点个性化设计
- 不要套用固定模板
- event字段要具体
"""
```

## 个性化示例

### 神豪文-花钱返利类
```json
[
  {"ch": 1, "emotion": "压抑", "intensity": 9, 
   "beat_type": "钩子", "event": "被宝马男撞，负债50万，女友分手",
   "purpose": "外卖员绝望开局，让读者代入"},
  
  {"ch": 2, "emotion": "希望", "intensity": 6,
   "beat_type": "转折", "event": "花钱返利系统觉醒，首单10倍返利",
   "purpose": "点燃希望，展示系统机制"},
  
  {"ch": 3, "emotion": "爽快", "intensity": 6,
   "beat_type": "爽点", "event": "4S店买电动车打脸销售",
   "purpose": "第一次花钱打脸，小试牛刀"},
  
  {"ch": 5, "emotion": "爽快", "intensity": 7,
   "beat_type": "爽点", "event": "高档餐厅偶遇前女友，一掷千金打脸",
   "purpose": "前女友后悔，经典爽点"},
  ...
]
```

### 国运文-扮演类
```json
[
  {"ch": 1, "emotion": "紧张", "intensity": 8,
   "beat_type": "钩子", "event": "失业外卖员被选中代表龙国",
   "purpose": "全国直播，压力山大"},
  
  {"ch": 2, "emotion": "希望", "intensity": 7,
   "beat_type": "转折", "event": "绑定神级扮演系统，首次扮演李逍遥",
   "purpose": "可以选择诸天人物，期待感"},
  
  {"ch": 3, "emotion": "爽快", "intensity": 8,
   "beat_type": "爽点", "event": "御剑飞行首杀禁地生物，全球震惊",
   "purpose": "国运具现，龙国沸腾"},
  
  {"ch": 5, "emotion": "震惊", "intensity": 9,
   "beat_type": "震惊", "event": "扮演酒剑仙，具现百年陈酿，全国酒香",
   "purpose": "首次具现资源，全国疯狂"},
  ...
]
```

## 优势对比

| 方面 | 固定模板 | AI个性化生成 |
|------|---------|-------------|
| 适应性 | ❌ 千篇一律 | ✅ 根据题材调整 |
| 事件设计 | ❌ 通用描述 | ✅ 具体事件 |
| 节奏变化 | ❌ 固定模式 | ✅ 灵活变化 |
| 创新性 | ❌ 容易雷同 | ✅ 更有新意 |
| 稳定性 | ✅ 稳定可靠 | ⚠️ 依赖AI质量 |
| 生成成本 | ✅ 无成本 | ⚠️ 需要AI调用 |

## 回退机制

如果AI生成失败，自动使用固定模板：
```python
def _generate_emotion_curve(self, genre, tropes, plan):
    try:
        # 尝试AI生成
        curve = generate_emotion_curve_with_ai(...)
        return curve
    except:
        # AI失败，使用默认模板
        logger.warning("AI生成失败，使用默认模板")
        return self._get_default_emotion_curve(total_chapters)
```

## 使用方式

```python
# 1. 一阶段生成产物（包含AI情绪曲线）
phase_one = generator.generate_all_products(genre, tropes, plan)

# 2. 二阶段使用AI情绪曲线
emotion_flow = create_emotion_flow(
    novel_title="我的小说",
    genre="神豪文-花钱返利类", 
    total_chapters=100,
    phase_one_products=phase_one  # 传入一阶段产物
)

# 3. 查看AI生成的曲线
print(emotion_flow.get_curve_visualization())

# 4. 生成章节时自动使用
for ch in range(1, 31):
    beat = emotion_flow.get_beat(ch)
    # beat包含AI设计的：emotion, intensity, event, purpose
```

## 总结

**固定模板**：简单可靠，适合快速测试
**AI个性化**：更灵活创新，适合生产环境

**推荐**：优先使用AI生成，失败时回退到模板
