# 系统级修复方案：中期章节质量断层问题

## 一、问题定义

### 1.1 现象描述
多本书籍在中期（第8-15章）出现质量断崖式下跌：
- 对话比例从50%骤降至15-25%
- 番茄得分从80+跌至50-60
- 连续多章压抑情绪无释放

### 1.2 根本原因（系统级）

```
┌─────────────────────────────────────────────────────────────┐
│                    系统架构问题                             │
├─────────────────────────────────────────────────────────────┤
│ 1. TacticalPlanner                                          │
│    └── 5章循环模板过于僵化，不区分前/中/后期                 │
│    └── 缺乏对"连续压抑"的检测和干预                         │
│                                                             │
│ 2. BatchSummarizer                                          │
│    └── 使用固定quality_score=8.0（虚假评分）                │
│    └── 未接入ChapterAnalyticsService真实数据                │
│                                                             │
│ 3. QualityMonitor（缺失模块）                               │
│    └── 无实时质量监控                                       │
│    └── 无自动告警和干预机制                                 │
│                                                             │
│ 4. HierarchicalPlanner                                      │
│    └── batch_size=6与5章循环不匹配                          │
│    └── 缺乏跨batch情绪连贯性检查                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、系统级修复方案

### 模块1：TacticalPlanner重构（情绪规划引擎2.0）

#### 2.1.1 动态情绪曲线算法

**文件**: `web/services/market_driven/tactical_planner.py`

```python
class TacticalPlannerV2:
    """
    战术规划器V2 - 基于主角实力等级的动态情绪规划
    """
    
    # 分阶段情绪模板
    EMOTION_TEMPLATES = {
        'early': {  # 前期 (第1-6章): 建立困境→首次爆发
            'cycle': ['压抑', '紧张', '反转', '震惊', '期待'],
            'cycle_weights': [1.0, 0.9, 1.2, 1.1, 0.8],
            'max_consecutive_depressing': 2,
        },
        'middle': {  # 中期 (第7-18章): 持续爽点+阶段爆发
            'cycle': ['小爽', '震惊', '大爽', '期待', '反转'],
            'cycle_weights': [1.1, 1.2, 1.3, 0.9, 1.0],
            'max_consecutive_depressing': 1,  # 严格限制压抑
            'force_satisfaction_after_depressing': True,  # 压抑后强制爽点
        },
        'late': {  # 后期 (第19章+): 超爽连发+大高潮
            'cycle': ['震惊', '大爽', '超爽', '期待', '超爽'],
            'cycle_weights': [1.2, 1.3, 1.5, 1.0, 1.4],
            'max_consecutive_depressing': 0,  # 后期禁止纯压抑
        }
    }
    
    def plan_emotion_curve(self, start_ch: int, end_ch: int, 
                          protagonist_level: float) -> List[Dict]:
        """
        基于主角等级的动态情绪规划
        """
        # 确定阶段
        if start_ch <= 6:
            template = self.EMOTION_TEMPLATES['early']
        elif start_ch <= 18:
            template = self.EMOTION_TEMPLATES['middle']
        else:
            template = self.EMOTION_TEMPLATES['late']
        
        chapters = []
        depressing_count = 0
        
        for i, ch_num in enumerate(range(start_ch, end_ch + 1)):
            # 获取基础情绪
            base_emotion = template['cycle'][i % len(template['cycle'])]
            
            # 连续压抑检测和干预
            if base_emotion in ['压抑', '紧张']:
                depressing_count += 1
                if depressing_count >= template['max_consecutive_depressing']:
                    # 强制改为反转或爽点
                    base_emotion = '反转' if ch_num <= 12 else '小爽'
                    depressing_count = 0
            else:
                depressing_count = 0
            
            # 压抑后强制爽点
            if getattr(self, '_last_was_depressing', False) and \
               template.get('force_satisfaction_after_depressing'):
                if base_emotion not in ['反转', '小爽', '大爽', '震惊']:
                    base_emotion = '小爽'
            
            self._last_was_depressing = base_emotion in ['压抑', '紧张']
            
            chapters.append({
                'chapter_number': ch_num,
                'emotion': base_emotion,
                'intensity': self._calculate_intensity(base_emotion, ch_num),
                'depressing_sequence': depressing_count,
            })
        
        return chapters
```

#### 2.1.2 反派视角限制器

```python
class PerspectiveBalancer:
    """
    视角平衡器 - 限制反派视角占比
    """
    
    MAX_ANTAGONIST_PERSPECTIVE = 0.30  # 反派视角不超过30%
    
    def check_and_adjust(self, chapter_plan: Dict) -> Dict:
        """
        检查并调整视角分配
        """
        event = chapter_plan.get('event', '')
        
        # 检测是否以反派为主角
        antagonist_keywords = ['约翰', '阴谋', '会议', '策划', '密谋']
        antagonist_focus = any(kw in event for kw in antagonist_keywords)
        
        if antagonist_focus:
            # 调整为主角反击视角
            chapter_plan['event'] = self._convert_to_protagonist_perspective(event)
            chapter_plan['perspective_note'] = '主角主动视角，反派作为背景'
            chapter_plan['must_include'] = ['主角察觉', '主角反制', '直播弹幕反应']
        
        return chapter_plan
    
    def _convert_to_protagonist_perspective(self, event: str) -> str:
        """
        将反派视角转换为主角视角
        """
        conversions = {
            '约翰联手鹰酱，准备报复': '楚辰察觉阴谋，隔空震慑约翰',
            '反龙联盟密谋围杀': '楚辰识破陷阱，反将一军',
            '史蒂夫策划伏击': '楚辰提前布局，请君入瓮',
        }
        return conversions.get(event, event.replace('阴谋', '被识破').replace('密谋', '失败'))
```

---

### 模块2：BatchSummarizer修复（真实质量接入）

#### 2.2.1 接入真实质量分析

**文件**: `web/services/market_driven/batch_summarizer.py`

```python
class BatchSummarizerV2:
    """
    批次总结器V2 - 接入真实质量数据
    """
    
    def __init__(self, api_client=None, analytics_service=None):
        self.api_client = api_client
        self.analytics_service = analytics_service  # 新增：接入分析服务
    
    def summarize_batch(self, chapters: List[Dict], ...) -> Dict:
        """
        总结批次内容（接入真实质量数据）
        """
        summary = self._basic_summary(chapters)
        
        # 🔥 新增：接入真实质量分析
        if self.analytics_service:
            real_quality = self._analyze_real_quality(chapters)
            summary['real_quality'] = real_quality
            
            # 检测低质量章节
            low_quality_chapters = [
                ch for ch in real_quality 
                if ch['tomato_score'] < 60
            ]
            
            if low_quality_chapters:
                summary['alerts'] = [
                    {
                        'type': 'low_quality',
                        'severity': 'critical',
                        'chapters': [ch['chapter_num'] for ch in low_quality_chapters],
                        'message': f"检测到{len(low_quality_chapters)}章质量低于60分",
                        'recommendation': '建议重写或扩写以下章节'
                    }
                ]
        
        return summary
    
    def _analyze_real_quality(self, chapters: List[Dict]) -> List[Dict]:
        """
        使用ChapterAnalyticsService分析真实质量
        """
        results = []
        for ch in chapters:
            ch_num = ch.get('chapter_number') or ch.get('chapter')
            if ch_num and self.analytics_service:
                metrics = self.analytics_service.analyze_chapter(ch_num)
                if metrics:
                    results.append({
                        'chapter_num': ch_num,
                        'tomato_score': metrics.tomato_score,
                        'dialogue_ratio': metrics.dialogue_ratio,
                        'shuang_density': metrics.shuang_density,
                        'emotion_density': metrics.emotion_density,
                        'issues': self._identify_issues(metrics)
                    })
        return results
    
    def _identify_issues(self, metrics) -> List[str]:
        """识别章节问题"""
        issues = []
        if metrics.dialogue_ratio < 40:
            issues.append(f"对话比例过低({metrics.dialogue_ratio:.1f}%)")
        if metrics.shuang_density < 1.0:
            issues.append(f"爽点密度不足({metrics.shuang_density:.2f})")
        if metrics.tomato_score < 60:
            issues.append(f"番茄得分偏低({metrics.tomato_score:.1f})")
        return issues
```

---

### 模块3：QualityMonitor（新增实时质量监控模块）

#### 2.3.1 实时质量监控器

**新文件**: `web/services/market_driven/quality_monitor.py`

```python
# -*- coding: utf-8 -*-
"""
QualityMonitor - 实时质量监控模块
每章生成后实时监控质量指标，触发告警和干预
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QualityThresholds:
    """质量阈值配置"""
    dialogue_ratio_min: float = 40.0  # 对话比例最低40%
    tomato_score_min: float = 60.0    # 番茄得分最低60
    shuang_density_min: float = 1.0   # 爽点密度最低1.0
    emotion_density_min: float = 2.0  # 情绪密度最低2.0
    max_consecutive_depressing: int = 2  # 最多连续2章压抑
    max_antagonist_perspective: float = 0.3  # 反派视角不超过30%


class QualityMonitor:
    """
    实时质量监控器
    
    职责：
    1. 每章生成后实时分析质量
    2. 检测异常并触发告警
    3. 提供自动修复建议
    4. 阻断低质量章节进入下一流程
    """
    
    def __init__(self, thresholds: QualityThresholds = None):
        self.thresholds = thresholds or QualityThresholds()
        self.recent_chapters: List[Dict] = []  # 最近章节记录
        self.max_history = 10
        
    def monitor_chapter(self, chapter_data: Dict, metrics: Dict) -> Dict:
        """
        监控单章质量
        
        Returns:
            {
                'passed': bool,  # 是否通过质量检查
                'alerts': List[Dict],  # 告警列表
                'auto_fix_suggestions': List[Dict],  # 自动修复建议
                'block_next': bool  # 是否阻断下一章生成
            }
        """
        alerts = []
        suggestions = []
        
        # 检查1：对话比例
        dialogue_ratio = metrics.get('dialogue_ratio', 0)
        if dialogue_ratio < self.thresholds.dialogue_ratio_min:
            alerts.append({
                'type': 'low_dialogue_ratio',
                'severity': 'warning',
                'message': f"对话比例{dialogue_ratio:.1f}%低于阈值{self.thresholds.dialogue_ratio_min}%",
                'chapter': chapter_data.get('chapter_number')
            })
            suggestions.append({
                'type': 'expand_dialogue',
                'description': '自动扩写弹幕和围观反应',
                'params': {'target_ratio': 45}
            })
        
        # 检查2：番茄得分
        tomato_score = metrics.get('tomato_score', 0)
        if tomato_score < self.thresholds.tomato_score_min:
            alerts.append({
                'type': 'low_tomato_score',
                'severity': 'critical',
                'message': f"番茄得分{tomato_score:.1f}低于阈值{self.thresholds.tomato_score_min}",
                'chapter': chapter_data.get('chapter_number')
            })
            suggestions.append({
                'type': 'rewrite_chapter',
                'description': '建议重写本章',
                'params': {'min_score': 70}
            })
        
        # 检查3：连续压抑
        emotion = chapter_data.get('emotion', '')
        depressing_count = self._count_consecutive_depressing(emotion)
        if depressing_count >= self.thresholds.max_consecutive_depressing:
            alerts.append({
                'type': 'consecutive_depressing',
                'severity': 'critical',
                'message': f"连续{depressing_count}章压抑情绪",
                'chapter': chapter_data.get('chapter_number')
            })
            suggestions.append({
                'type': 'force_satisfaction',
                'description': '下一章强制改为爽点章节',
                'params': {'emotion': '大爽'}
            })
        
        # 检查4：反派视角
        content = chapter_data.get('content', '')
        antagonist_ratio = self._calculate_antagonist_perspective(content)
        if antagonist_ratio > self.thresholds.max_antagonist_perspective:
            alerts.append({
                'type': 'high_antagonist_perspective',
                'severity': 'warning',
                'message': f"反派视角占比{antagonist_ratio*100:.1f}%过高",
                'chapter': chapter_data.get('chapter_number')
            })
        
        # 更新历史记录
        self._update_history(chapter_data, metrics)
        
        # 判断是否阻断
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        should_block = len(critical_alerts) > 0
        
        return {
            'passed': len(alerts) == 0,
            'alerts': alerts,
            'auto_fix_suggestions': suggestions,
            'block_next': should_block,
            'metrics': {
                'dialogue_ratio': dialogue_ratio,
                'tomato_score': tomato_score,
                'consecutive_depressing': depressing_count,
                'antagonist_ratio': antagonist_ratio
            }
        }
    
    def _count_consecutive_depressing(self, current_emotion: str) -> int:
        """统计连续压抑章节数"""
        if current_emotion not in ['压抑', '紧张']:
            return 0
        
        count = 1
        for ch in reversed(self.recent_chapters):
            if ch.get('emotion') in ['压抑', '紧张']:
                count += 1
            else:
                break
        return count
    
    def _calculate_antagonist_perspective(self, content: str) -> float:
        """计算反派视角占比（简化版）"""
        antagonist_keywords = ['约翰', '史蒂夫', '山本', '会议', '密谋', '策划']
        # 这里可以用更复杂的NLP分析
        # 简化：统计反派关键词出现次数
        total_chars = len(content)
        if total_chars == 0:
            return 0.0
        
        antagonist_chars = sum(content.count(kw) * len(kw) for kw in antagonist_keywords)
        return min(antagonist_chars / total_chars, 1.0)
    
    def _update_history(self, chapter_data: Dict, metrics: Dict):
        """更新历史记录"""
        self.recent_chapters.append({
            'chapter_number': chapter_data.get('chapter_number'),
            'emotion': chapter_data.get('emotion'),
            'tomato_score': metrics.get('tomato_score'),
            'dialogue_ratio': metrics.get('dialogue_ratio')
        })
        
        # 保持最近10章
        if len(self.recent_chapters) > self.max_history:
            self.recent_chapters.pop(0)
    
    def get_batch_quality_report(self) -> Dict:
        """获取批次质量报告"""
        if not self.recent_chapters:
            return {}
        
        scores = [ch['tomato_score'] for ch in self.recent_chapters if ch.get('tomato_score')]
        dialogue_ratios = [ch['dialogue_ratio'] for ch in self.recent_chapters if ch.get('dialogue_ratio')]
        
        return {
            'chapters_analyzed': len(self.recent_chapters),
            'avg_tomato_score': sum(scores) / len(scores) if scores else 0,
            'avg_dialogue_ratio': sum(dialogue_ratios) / len(dialogue_ratios) if dialogue_ratios else 0,
            'low_quality_chapters': sum(1 for s in scores if s < 60),
            'trend': 'up' if len(scores) >= 2 and scores[-1] > scores[0] else 'down'
        }
```

---

### 模块4：HierarchicalPlanner优化（Batch调度优化）

#### 2.4.1 Batch大小与情绪循环对齐

**文件**: `web/services/market_driven/hierarchical_planner.py`

```python
class HierarchicalPlannerV2:
    """
    分层规划器V2 - 优化Batch调度
    """
    
    # 根据情绪循环调整batch大小
    BATCH_CONFIG = {
        'early': {'size': 6, 'cycle': 5},   # 前期6章一个batch
        'middle': {'size': 3, 'cycle': 5},  # 中期3章一个batch（更细粒度控制）
        'late': {'size': 5, 'cycle': 5},    # 后期5章一个batch
    }
    
    def get_next_batch_plan(self, batch_size: int = None) -> Tuple[Dict, Dict]:
        """
        获取下一批次规划
        """
        start_ch = self._get_next_chapter_number()
        
        # 🔥 根据章节位置动态调整batch大小
        if start_ch <= 6:
            effective_batch_size = self.BATCH_CONFIG['early']['size']
        elif start_ch <= 18:
            effective_batch_size = self.BATCH_CONFIG['middle']['size']  # 中期3章
        else:
            effective_batch_size = self.BATCH_CONFIG['late']['size']
        
        if batch_size:
            effective_batch_size = batch_size
        
        end_ch = min(start_ch + effective_batch_size - 1, self.total_chapters)
        
        # 确保batch边界不与情绪高潮冲突
        if self._is_climax_chapter(end_ch):
            # 如果batch结束在高潮章，向后扩展包含完整高潮
            end_ch = self._find_climax_end(end_ch)
        
        # ... 其余逻辑
    
    def _is_climax_chapter(self, ch_num: int) -> bool:
        """判断是否为高潮章节"""
        # 高潮章节通常是5的倍数
        return ch_num % 5 == 0 or ch_num % 10 == 0
    
    def _find_climax_end(self, start_climax: int) -> int:
        """找到高潮结束章节"""
        # 高潮通常持续1-2章
        return min(start_climax + 1, self.total_chapters)
```

---

### 模块5：AutoFixer（新增自动修复模块）

#### 2.5.1 自动修复引擎

**新文件**: `web/services/market_driven/auto_fixer.py`

```python
# -*- coding: utf-8 -*-
"""
AutoFixer - 自动修复引擎
根据QualityMonitor的告警自动修复低质量章节
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class AutoFixer:
    """
    自动修复引擎
    
    支持的修复类型：
    1. 对话比例不足 → 扩写弹幕和围观反应
    2. 情绪密度不足 → 插入情绪词汇
    3. 爽点密度不足 → 扩写震惊反应链
    4. 反派视角过高 → 转换为主角视角
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self.fix_strategies = {
            'low_dialogue_ratio': self._fix_low_dialogue,
            'low_emotion_density': self._fix_low_emotion,
            'low_shuang_density': self._fix_low_shuang,
            'high_antagonist_perspective': self._fix_perspective,
        }
    
    def fix_chapter(self, chapter_data: Dict, issues: List[Dict]) -> Dict:
        """
        自动修复章节
        
        Returns:
            {
                'fixed': bool,
                'chapter_data': Dict,  # 修复后的章节数据
                'fixes_applied': List[str],  # 应用的修复
                'before_metrics': Dict,
                'after_metrics': Dict
            }
        """
        fixed_data = chapter_data.copy()
        fixes_applied = []
        
        for issue in issues:
            fix_type = issue.get('type')
            if fix_type in self.fix_strategies:
                try:
                    fixed_data = self.fix_strategies[fix_type](fixed_data, issue)
                    fixes_applied.append(fix_type)
                    logger.info(f"[AutoFixer] 应用修复: {fix_type}")
                except Exception as e:
                    logger.error(f"[AutoFixer] 修复失败 {fix_type}: {e}")
        
        return {
            'fixed': len(fixes_applied) > 0,
            'chapter_data': fixed_data,
            'fixes_applied': fixes_applied,
        }
    
    def _fix_low_dialogue(self, chapter_data: Dict, issue: Dict) -> Dict:
        """
        修复低对话比例：扩写弹幕和围观反应
        """
        content = chapter_data.get('content', '')
        target_ratio = issue.get('params', {}).get('target_ratio', 45)
        
        # 计算需要增加的字数
        current_len = len(content)
        target_dialogue_len = int(current_len * target_ratio / 100)
        
        # 生成扩写提示词
        expansion_prompt = f"""
请对以下章节进行扩写，增加弹幕和围观反应，提升对话比例至{target_ratio}%。

【原始内容】
{content[:500]}...

【扩写要求】
1. 在关键事件处增加【弹幕内容】（至少5-8条）
2. 增加围观群众的震惊台词
3. 增加龙国高层的反应
4. 保持原有剧情不变
5. 只添加对话和反应，不添加叙述

【弹幕示例】
【龙国观众：卧槽！这也行？】
【外国观众：不可能！这一定是作弊！】
【专家：这违背了物理学常识！】
"""
        
        if self.api_client:
            expansion = self.api_client.generate_content(expansion_prompt)
            chapter_data['content'] = content + '\n\n' + expansion
            chapter_data['auto_fix_applied'] = 'low_dialogue_ratio'
        
        return chapter_data
    
    def _fix_low_emotion(self, chapter_data: Dict, issue: Dict) -> Dict:
        """修复低情绪密度"""
        # 实现情绪词汇插入
        return chapter_data
    
    def _fix_low_shuang(self, chapter_data: Dict, issue: Dict) -> Dict:
        """修复低爽点密度"""
        # 实现震惊反应链扩写
        return chapter_data
    
    def _fix_perspective(self, chapter_data: Dict, issue: Dict) -> Dict:
        """修复反派视角过高"""
        content = chapter_data.get('content', '')
        
        # 标记需要转换的段落
        conversion_prompt = f"""
请将以下以反派视角为主的章节，转换为主角视角。
保持剧情不变，但从主角的观察和反应来讲述。

【原始内容】
{content[:1000]}...

【转换要求】
1. 删除反派的内心独白和会议讨论
2. 改为楚辰通过直播/线索察觉到反派动向
3. 增加楚辰的应对和反击准备
4. 保持关键事件不变
"""
        
        if self.api_client:
            converted = self.api_client.generate_content(conversion_prompt)
            chapter_data['content'] = converted
            chapter_data['auto_fix_applied'] = 'high_antagonist_perspective'
        
        return chapter_data
```

---

## 三、配置层修复

### 3.1 战术规划配置更新

**文件**: `prompt_packages/default/market_driven/components/planning/tactical_planning_prompts.json`

```json
{
  "version": "2.0",
  "system_prompt_template": {
    "template": "# 战术规划师\n\n为《{novel_title}》规划第{start_chapter}-{end_chapter}章。\n\n## 阶段自适应情绪模板\n根据起始章节自动选择模板：\n- 第1-6章（前期）: [压抑, 紧张, 反转, 震惊, 期待]\n- 第7-18章（中期）: [小爽, 震惊, 大爽, 期待, 反转] - 禁止连续压抑\n- 第19章+（后期）: [震惊, 大爽, 超爽, 期待, 反转] - 禁止纯压抑\n\n## 反派视角限制\n- 反派视角占比不得超过30%\n- 禁止以反派会议/密谋作为章节主线\n- 所有阴谋必须通过主角视角揭露\n\n## 质量指标（强制）\n- 对话比例 ≥ 40%\n- 番茄得分 ≥ 60\n- 连续压抑 ≤ 1章（中期）"
  },
  
  "emotion_cycle_template": {
    "early": {
      "cycles": [
        {"position": 1, "emotion": "压抑", "intensity_range": "7-8", "max_consecutive": 2},
        {"position": 2, "emotion": "紧张", "intensity_range": "8-9"},
        {"position": 3, "emotion": "反转", "intensity_range": "8-9"},
        {"position": 4, "emotion": "震惊", "intensity_range": "7-8"},
        {"position": 5, "emotion": "期待", "intensity_range": "6-7"}
      ]
    },
    "middle": {
      "cycles": [
        {"position": 1, "emotion": "小爽", "intensity_range": "6-7", "note": "开局即爽"},
        {"position": 2, "emotion": "震惊", "intensity_range": "7-8"},
        {"position": 3, "emotion": "大爽", "intensity_range": "8-9"},
        {"position": 4, "emotion": "期待", "intensity_range": "6-7"},
        {"position": 5, "emotion": "反转", "intensity_range": "7-8"}
      ],
      "restrictions": {
        "max_consecutive_depressing": 1,
        "force_satisfaction_after_depressing": true,
        "min_dialogue_ratio": 40
      }
    },
    "late": {
      "cycles": [
        {"position": 1, "emotion": "震惊", "intensity_range": "7-8"},
        {"position": 2, "emotion": "大爽", "intensity_range": "8-9"},
        {"position": 3, "emotion": "超爽", "intensity_range": "9-10"},
        {"position": 4, "emotion": "期待", "intensity_range": "6-7"},
        {"position": 5, "emotion": "超爽", "intensity_range": "9-10"}
      ],
      "restrictions": {
        "allow_depressing": false,
        "min_shuang_density": 2.0
      }
    }
  }
}
```

---

## 四、流程层修复

### 4.1 新的章节生成流程

```
┌─────────────────────────────────────────────────────────────┐
│                    新的章节生成流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. TacticalPlannerV2                                       │
│     └── 根据章节位置选择前/中/后期模板                       │
│     └── 生成情绪规划（禁止连续压抑）                         │
│     └── 应用视角平衡器（限制反派视角）                       │
│         ↓                                                   │
│  2. ChapterGenerator                                        │
│     └── 生成章节内容                                        │
│         ↓                                                   │
│  3. QualityMonitor（新增）                                  │
│     └── 实时分析质量指标                                    │
│     └── 检测异常（对话/得分/情绪）                          │
│     └── 触发告警 → 是否阻断？                               │
│         ↓ 是                                                │
│  4. AutoFixer（新增）                                       │
│     └── 自动修复低质量问题                                  │
│     └── 扩写对话/转换视角/插入爽点                          │
│         ↓                                                   │
│  5. BatchSummarizerV2                                       │
│     └── 接入真实质量数据（不再用虚假8.0）                   │
│     └── 生成批次总结                                        │
│     └── 反馈给TacticalPlanner调整下一batch                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、实施路线图

### 阶段1：紧急热修复（1-2天）
1. 修复BatchSummarizer，接入真实质量数据
2. 在HierarchicalPlanner中临时调整中期batch_size=3
3. 添加QualityMonitor的基础告警功能

### 阶段2：核心重构（1周）
1. 完成TacticalPlannerV2的动态情绪规划
2. 开发QualityMonitor完整功能
3. 开发AutoFixer基础修复能力

### 阶段3：全面优化（2周）
1. 完成AutoFixer所有修复策略
2. 优化配置文件的自适应参数
3. 添加更多质量监控维度

### 阶段4：验证上线（3天）
1. 使用测试书籍验证修复效果
2. 确保中期章节质量稳定在70+
3. 全量上线

---

## 六、关键指标（修复后预期）

| 指标 | 修复前 | 修复后目标 | 验证方式 |
|------|--------|-----------|---------|
| 中期平均得分 | 50-60 | 75+ | ChapterAnalyticsService |
| 连续压抑章节 | 3章 | ≤1章 | QualityMonitor |
| 对话比例 | 20% | 40%+ | 实时统计 |
| 反派视角占比 | 70% | ≤30% | 内容分析 |
| 质量检测覆盖率 | 0% | 100% | 每章必检 |

---

*系统修复方案文档 - v1.0*
*日期: 2026-04-02*
