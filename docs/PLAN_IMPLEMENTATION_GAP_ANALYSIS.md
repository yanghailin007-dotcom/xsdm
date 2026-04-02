# 规划与实现脱节问题深度分析

## 一、问题核心：规划很丰富，执行很骨感

### 1.1 规划层设计了什么（详细梳理）

```
┌────────────────────────────────────────────────────────────────────────┐
│                         规划层设计架构                                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  L1: StrategicPlanner (战略层 - 200章)                                  │
│      ├── 转折点规划 (5-6个关键节点)                                     │
│      ├── 主角成长阶段 (4-5个阶段)                                       │
│      ├── 情绪大周期 (整体走向)                                          │
│      └── 核心悬念链                                                     │
│                          ↓                                              │
│  L2: TacticalPlanner (战术层 - 30章窗口)                                │
│      ├── 5章情绪循环模板                                                │
│      │   ├── 第1章: 压抑 (强度7-8) - 主角被质疑                         │
│      │   ├── 第2章: 嘲讽 (强度8-9) - 反派嚣张                           │
│      │   ├── 第3章: 反转 (强度8-9) - 主角反击                           │
│      │   ├── 第4章: 震惊 (强度7-8) - 全网刷屏                           │
│      │   └── 第5章: 期待 (强度6-7) - 埋下伏笔                           │
│      ├── 每章详细规划                                                   │
│      │   ├── 情绪类型 + 强度                                            │
│      │   ├── 节拍类型 (铺垫/冲突/反转/渲染/伏笔)                        │
│      │   ├── 主要事件                                                   │
│      │   ├── 钩子类型 + 内容                                            │
│      │   └── 阶段目标对齐                                               │
│      ├── 算法要求                                                       │
│      │   ├── 情绪密度 ≥2.0/千字                                         │
│      │   ├── 爽点密度 ≥1.5/千字                                         │
│      │   └── 对话占比 ≥50%                                              │
│      └── 自检清单                                                       │
│          ├── 情绪词 ≥10个                                               │
│          ├── 爽点时刻 ≥3个                                              │
│          └── 最后50字是钩子                                             │
│                          ↓                                              │
│  L3: ChapterPromptOptimizerV3 (章节层 - 单章)                           │
│      ├── 章节类型检测 (SETUP/FACE_SLAP/REWARD/REVEAL/CRISIS)            │
│      ├── 黄金三章特殊处理 (第1-3章)                                     │
│      ├── 战术大纲约束 (如果有)                                          │
│      ├── 情绪控制指南                                                   │
│      ├── 格式规则                                                       │
│      └── AI自检指南                                                     │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2 实际生成了什么（以第9章为例）

**规划期望**（根据5章循环，第9章应该是）：
```json
{
  "chapter_number": 9,
  "emotion": "反转/爆发",  // (9-1)%5=3 → 反转
  "intensity": 8,
  "beat_type": "反转",
  "event": "楚辰展现实力，开始反击",
  "algorithm_requirements": {
    "emotion_density_target": "≥2.0/千字",
    "appeal_density_target": "≥1.5/千字"
  }
}
```

**实际生成**（根据分析报告）：
```json
{
  "chapter_number": 9,
  "actual_emotion": "压抑",  // ❌ 与规划不符
  "actual_event": "约翰联手鹰酱，准备报复",  // ❌ 反派视角
  "dialogue_ratio": "21%",  // ❌ 远低于50%
  "tomato_score": 59.4,  // ❌ 低于60
  "shuang_density": 1.65,  // ✅ 勉强达标
  "emotion_density": 0.83  // ❌ 远低于2.0
}
```

**差距**：规划要求"反转爆发"，实际生成"反派阴谋铺垫"

---

## 二、脱节的5个根本原因

### 原因1：TacticalPlanner的5章循环位置计算错误 ⭐最核心

**问题代码**（tactical_planner.py:325）：
```python
cycle_pos = i % 5  # i是batch内索引，不是全局章节号
```

**实际执行**：
```
Batch 1 (第1-6章): i=0,1,2,3,4,5 → cycle_pos=0,1,2,3,4,0
Batch 2 (第7-12章): i=0,1,2,3,4,5 → cycle_pos=0,1,2,3,4,0
```

**问题**：每个batch都重新开始计数，导致第7章变成cycle_pos=0（压抑），而不是继续第6章的cycle_pos=4（期待→压抑过渡）

**正确计算**：
```python
# 应该是全局章节号决定循环位置
cycle_pos = (chapter_num - 1) % 5

第1章: (1-1)%5=0 → 压抑
第2章: (2-1)%5=1 → 嘲讽
第3章: (3-1)%5=2 → 反转
第4章: (4-1)%5=3 → 震惊
第5章: (5-1)%5=4 → 期待
第6章: (6-1)%5=0 → 压抑 (应该是嘲讽或延续)
第7章: (7-1)%5=1 → 嘲讽 (应该是反转)
...
第9章: (9-1)%5=3 → 震惊 (应该是反转)
```

**结论**：即使使用全局章节号，第6章也会回到"压抑"，这就是问题所在——**5章循环模板本身不适合长周期**

---

### 原因2：规划提示词与章节生成提示词之间缺乏"强制性约束"

**规划输出** → **实际生成提示词** 的转换链路：

```
TacticalPlanner规划
    ↓
生成战术蓝图（JSON）
    ↓
HierarchicalPlanner提取batch_plan
    ↓
BatchChapterGenerator调用ChapterPromptOptimizerV3
    ↓
构建提示词时...
    ↓
问题：战术蓝图中的"情绪"和"事件"没有被强制注入到System Prompt
```

**查看实际提示词构建**（chapter_prompt_optimizer_v3.py:1071-1082）：
```python
emotion = blueprint.get('emotion', '')
purpose = blueprint.get('purpose', '')
beat_type = blueprint.get('beat_type', '')

# 这些只是被"参考"，不是强制约束
# System Prompt的主体是从JSON组件加载的通用模板
# 战术蓝图只是"附加信息"
```

**关键缺失**：
```python
# 应该这样强制约束（但实际没有）：
"""
## ⚠️ 强制约束（来自战术规划）
本章必须实现的情绪: {emotion}（强度{intensity}/10）
本章必须完成的事件: {event}
本章必须达到的爽点密度: ≥{appeal_density}/千字

如果生成内容与上述约束不符，必须重新生成！
"""
```

---

### 原因3：AI在生成时"创造性发挥"偏离规划

**实际案例分析**（第9章）：

**战术规划要求**：
```
情绪: 反转/爆发
事件: 楚辰展现实力，开始反击
节拍: 主角从被动转为主动
```

**AI生成时的"发挥"**：
```
实际情绪: 压抑（约翰阴谋）
实际事件: 约翰联手鹰酱，准备报复
实际节拍: 反派主动，主角被动
```

**为什么会这样？**

1. **提示词权重不够**：战术规划只是"建议"，不是"铁律"
2. **训练数据偏差**：AI的训练数据中有大量"反派阴谋铺垫"的模板
3. **上下文延续**：第8章是"楚辰头痛"（压抑），AI自然地延续了压抑情绪

**关键问题**：规划没有考虑"上下文情绪惯性"

---

### 原因4：缺乏实时校验和反馈机制

**当前流程**（无校验）：
```
生成章节 → 保存文件 → 下一章
     ↑___________|
（没有回头检查）
```

**应该有的流程**（带校验）：
```
生成章节 → 质量分析 → 达标？
                ↓
              是 → 保存 → 下一章
                ↓
              否 → 告警 → 修复 → 重新生成
```

**关键缺失**：
1. ChapterAnalyticsService没有被调用
2. BatchSummarizer使用的是虚假的quality_score=8.0
3. 没有自动修复机制

---

### 原因5：中期阶段没有自适应调整策略

**5章循环模板的问题**：

```
前期(1-5章): 压抑→嘲讽→反转→震惊→期待 ✓ 适用（建立困境）
中期(6-10章): 压抑→嘲讽→反转→震惊→期待 ✗ 不适用（应该持续爽点）
后期(15章+): 压抑→嘲讽→反转→震惊→期待 ✗ 严重不适用（应该超爽连发）
```

**中期读者心理**：
- 已经知道主角很强
- 期待看到主角持续装逼
- 不想再看到主角受委屈

**模板没有区分阶段**，导致中期出现不合理的"压抑"章节。

---

## 三、系统性修复方案（细致到代码级别）

### 修复1：分阶段动态情绪模板（解决原因1和5）

**文件**: `web/services/market_driven/tactical_planner.py`

```python
class TacticalPlanner:
    """
    战术规划器 - 分阶段动态情绪规划
    """
    
    # 分阶段情绪模板 - 这才是正确的规划
    PHASE_TEMPLATES = {
        'early': {
            'chapter_range': (1, 6),
            'cycle': ['压抑', '紧张', '反转', '震惊', '期待', '小爽'],
            'description': '建立困境，首次爆发',
            'rules': {
                'allow_consecutive_depressing': True,  # 允许压抑延续
                'min_satisfaction_frequency': 3,  # 每3章必须有爽点
            }
        },
        'middle': {
            'chapter_range': (7, 18),
            'cycle': ['小爽', '震惊', '大爽', '期待', '反转'],  # ❗ 压抑被移除
            'description': '持续爽点，阶段高潮',
            'rules': {
                'allow_consecutive_depressing': False,  # 禁止压抑延续
                'force_satisfaction_after_tension': True,  # 紧张后必须爽点
                'min_dialogue_ratio': 40,  # 强制对话比例
            }
        },
        'late': {
            'chapter_range': (19, 200),
            'cycle': ['震惊', '大爽', '超爽', '期待', '超爽'],
            'description': '超爽连发，大高潮',
            'rules': {
                'forbidden_emotions': ['压抑', '紧张'],  # 完全禁止
                'min_satisfaction_density': 2.5,  # 更高爽点密度
            }
        }
    }
    
    def get_emotion_for_chapter(self, ch_num: int) -> Dict:
        """
        根据章节号获取情绪规划
        """
        # 确定阶段
        phase = None
        for phase_name, config in self.PHASE_TEMPLATES.items():
            start, end = config['chapter_range']
            if start <= ch_num <= end:
                phase = phase_name
                break
        
        if not phase:
            phase = 'late'
        
        config = self.PHASE_TEMPLATES[phase]
        cycle = config['cycle']
        
        # 计算在周期中的位置
        # 使用相对于阶段起始的偏移
        phase_start = config['chapter_range'][0]
        pos_in_phase = (ch_num - phase_start) % len(cycle)
        
        emotion = cycle[pos_in_phase]
        
        # 应用阶段规则
        if ch_num > 6 and emotion in ['压抑', '紧张']:
            # 中期以后禁止压抑
            logger.warning(f"第{ch_num}章原定情绪{emotion}被强制改为'小爽'")
            emotion = '小爽'
        
        return {
            'chapter': ch_num,
            'phase': phase,
            'emotion': emotion,
            'rules': config['rules'],
        }
```

---

### 修复2：强制约束注入（解决原因2）

**文件**: `web/services/market_driven/chapter_prompt_optimizer_v3.py`

```python
def _build_system_prompt_with_constraints(self, chapter_num: int, 
                                           blueprint: Dict) -> str:
    """
    构建带强制约束的System Prompt
    """
    # 基础提示词
    base_prompt = self._build_base_system_prompt()
    
    # 🔥 关键：从战术蓝图提取强制约束
    constraints = []
    
    if blueprint:
        emotion = blueprint.get('emotion')
        intensity = blueprint.get('intensity')
        event = blueprint.get('event')
        beat_type = blueprint.get('beat_type')
        
        # 强制约束1：情绪
        if emotion:
            constraints.append(f"""
### ⚠️ 强制约束1：情绪基调
**本章必须是【{emotion}】情绪（强度{intensity}/10）**
- 全文必须围绕此情绪展开
- 禁止偏离到其他情绪
- 如果规划是"反转"，必须出现主角反击的爽点
""")
        
        # 强制约束2：事件
        if event:
            constraints.append(f"""
### ⚠️ 强制约束2：核心事件
**本章必须完成事件：{event}**
- 事件必须在章内完整呈现
- 禁止偏离到无关剧情
- 禁止用反派视角替代主角视角
""")
        
        # 强制约束3：算法指标
        algo_req = blueprint.get('algorithm_requirements', {})
        emotion_density = algo_req.get('emotion_density_target', '≥2.0/千字')
        appeal_density = algo_req.get('appeal_density_target', '≥1.5/千字')
        
        constraints.append(f"""
### ⚠️ 强制约束3：算法指标（必须达标）
- 情绪密度：{emotion_density}
- 爽点密度：{appeal_density}
- 对话占比：≥50%

**不达标的内容将被判定为不合格！**
""")
    
    # 组合提示词：约束在前，基础在后
    # 这样约束部分权重更高
    constraint_section = "\n".join(constraints)
    
    full_prompt = f"""{constraint_section}

{'='*60}
{base_prompt}
"""
    
    return full_prompt
```

---

### 修复3：情绪惯性检测与修正（解决原因3）

**新文件**: `web/services/market_driven/emotion_coherence_checker.py`

```python
# -*- coding: utf-8 -*-
"""
情绪连贯性检查器
检测并修正AI生成时的情绪惯性偏差
"""

class EmotionCoherenceChecker:
    """
    情绪连贯性检查器
    
    功能：
    1. 检测生成内容是否与规划情绪一致
    2. 检测情绪惯性（延续上一章的不合理情绪）
    3. 提供修正建议
    """
    
    # 情绪关键词映射
    EMOTION_KEYWORDS = {
        '压抑': ['绝望', '无力', '屈辱', '悲愤', '心如刀割', '窒息', '痛苦'],
        '反转': ['反击', '爆发', '展现', '实力', '秒杀', '碾压', '震惊'],
        '大爽': ['畅快', '解气', '痛快', '满足', '扬眉吐气', '狂喜'],
    }
    
    def __init__(self):
        self.previous_chapter_emotion = None
    
    def check_coherence(self, content: str, planned_emotion: str) -> Dict:
        """
        检查情绪连贯性
        
        Returns:
            {
                'coherent': bool,
                'actual_emotion': str,
                'deviation': str,
                'fix_suggestion': str
            }
        """
        # 检测实际情绪
        actual_emotion = self._detect_actual_emotion(content)
        
        # 判断是否一致
        coherent = self._is_emotion_match(actual_emotion, planned_emotion)
        
        # 检测情绪惯性
        inertia_issue = self._check_emotion_inertia(
            actual_emotion, 
            self.previous_chapter_emotion,
            planned_emotion
        )
        
        result = {
            'coherent': coherent,
            'planned_emotion': planned_emotion,
            'actual_emotion': actual_emotion,
            'inertia_issue': inertia_issue,
        }
        
        if not coherent or inertia_issue:
            result['fix_suggestion'] = self._generate_fix_suggestion(
                planned_emotion, actual_emotion, content
            )
        
        # 更新历史
        self.previous_chapter_emotion = actual_emotion
        
        return result
    
    def _detect_actual_emotion(self, content: str) -> str:
        """检测内容实际表达的情绪"""
        scores = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = sum(content.count(kw) for kw in keywords)
            scores[emotion] = score
        
        # 返回得分最高的情绪
        return max(scores, key=scores.get) if scores else '未知'
    
    def _is_emotion_match(self, actual: str, planned: str) -> bool:
        """判断情绪是否匹配"""
        # 允许近似的情绪
        emotion_groups = {
            '压抑组': ['压抑', '绝望', '无力'],
            '爽点组': ['反转', '大爽', '小爽', '震惊'],
        }
        
        for group in emotion_groups.values():
            if actual in group and planned in group:
                return True
        
        return actual == planned
    
    def _check_emotion_inertia(self, actual: str, previous: str, 
                                planned: str) -> bool:
        """检查是否存在不合理的情绪惯性"""
        if not previous:
            return False
        
        # 如果规划要求改变情绪，但实际延续了上一章
        if planned != previous and actual == previous:
            return True
        
        return False
    
    def _generate_fix_suggestion(self, planned: str, actual: str, 
                                  content: str) -> str:
        """生成修正建议"""
        suggestions = {
            '压抑→反转': """
检测到情绪偏离：规划为"反转"，实际为"压抑"

修正建议：
1. 删除反派视角的会议讨论
2. 增加主角察觉后的反击准备
3. 在章节后半部分安排主角展现实力
4. 增加【弹幕】反应来放大爽点
""",
            '延续惯性': """
检测到情绪惯性：延续了上一章的情绪，未按规划转变

修正建议：
1. 在章节中间设置转折点
2. 使用"就在这时..."等转折词
3. 主角从被动变主动的心理描写
4. 增加系统提示触发转变
"""
        }
        
        key = f"{actual}→{planned}"
        return suggestions.get(key, "请检查情绪是否符合规划要求")
```

---

### 修复4：实时质量校验闭环（解决原因4）

**文件**: `web/services/market_driven/batch_chapter_generator.py`（修改生成流程）

```python
class BatchChapterGenerator:
    """
    批次章节生成器 - 带质量校验闭环
    """
    
    def generate_chapter_with_validation(self, ch_num: int, 
                                         blueprint: Dict) -> Dict:
        """
        生成章节并校验质量
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            # 1. 生成章节
            chapter = self._generate_single_chapter(ch_num, blueprint)
            
            # 2. 质量分析
            metrics = self._analyze_quality(chapter)
            
            # 3. 情绪连贯性检查
            coherence = self.emotion_checker.check_coherence(
                chapter['content'],
                blueprint.get('emotion', '')
            )
            
            # 4. 判断是否达标
            passed = self._validate_chapter(metrics, coherence, blueprint)
            
            if passed:
                logger.info(f"第{ch_num}章生成达标")
                return chapter
            
            # 5. 未达标，生成修复提示
            logger.warning(f"第{ch_num}章第{attempt+1}次生成未达标，准备修复")
            
            fix_prompt = self._generate_fix_prompt(metrics, coherence, blueprint)
            
            # 6. 修复后重新生成
            if attempt < max_retries - 1:
                chapter = self._regenerate_with_fix(chapter, fix_prompt)
        
        # 超过重试次数，返回最后一次结果（带告警）
        logger.error(f"第{ch_num}章生成{max_retries}次仍未达标，使用最后结果")
        chapter['quality_alert'] = True
        return chapter
    
    def _validate_chapter(self, metrics: Dict, coherence: Dict, 
                          blueprint: Dict) -> bool:
        """校验章节是否达标"""
        checks = []
        
        # 检查1：番茄得分
        checks.append(metrics.get('tomato_score', 0) >= 60)
        
        # 检查2：对话比例
        checks.append(metrics.get('dialogue_ratio', 0) >= 40)
        
        # 检查3：情绪连贯性
        checks.append(coherence.get('coherent', False))
        
        # 检查4：是否违反规划
        checks.append(not coherence.get('inertia_issue', False))
        
        return all(checks)
    
    def _generate_fix_prompt(self, metrics: Dict, coherence: Dict, 
                             blueprint: Dict) -> str:
        """生成修复提示词"""
        fixes = []
        
        if metrics.get('tomato_score', 0) < 60:
            fixes.append("提升整体质量，增加爽点和震惊反应")
        
        if metrics.get('dialogue_ratio', 0) < 40:
            fixes.append("增加弹幕和围观反应，提升对话比例")
        
        if not coherence.get('coherent', False):
            planned = coherence.get('planned_emotion')
            actual = coherence.get('actual_emotion')
            fixes.append(f"情绪偏离：规划{planned}，实际{actual}，请按规划情绪重写")
        
        return "\n".join(fixes)
```

---

## 四、一句话总结

> **规划与实现脱节的根本原因是：1）TacticalPlanner使用batch内索引计算情绪循环位置，导致每batch重新开始；2）5章循环模板没有区分前/中/后期，中期出现不合理的压抑；3）战术蓝图的约束只是"建议"而非"强制"，AI生成时容易偏离；4）缺乏实时质量校验和自动修复机制。**

**最核心修复**：
1. 分阶段情绪模板（前期压抑→中期爽点→后期超爽）
2. 强制约束注入（System Prompt前置强制约束）
3. 情绪惯性检测（防止AI偏离规划）
4. 实时校验闭环（不达标自动修复）

---

*分析完成时间：2026-04-02*
