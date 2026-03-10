"""
Enriched Expectation Mapping Manager - 基于完整阶段计划的期待感生成
优化目标：
1. 利用完整阶段计划信息（情绪曲线、角色弧线、世界观展开）
2. 阶段级批量生成（4次API调用/书）
3. 跨事件关联分析
4. 情绪曲线匹配
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from src.utils.logger import get_logger


@dataclass
class StageExpectationInput:
    """阶段期待感生成输入"""
    stage_name: str
    stage_range: str
    emotional_arc: Dict
    protagonist_growth_theme: str
    worldview_revelation_plan: Dict
    conflict_theme: Dict
    events: List[Dict]
    satisfaction_points: List[Dict]


class EnrichedExpectationManager:
    """增强版期待感管理器"""
    
    def __init__(self, api_client=None):
        self.logger = get_logger("EnrichedExpectationManager")
        self.api_client = api_client
    
    def build_stage_input(self, stage_name: str, stage_plan: Dict) -> Dict:
        """构建增强版的阶段输入"""
        swp = stage_plan.get("stage_writing_plan", {})
        
        # 提取情绪曲线关键信息
        emotional_arc = swp.get("emotional_arc", {})
        emotional_arc_summary = {
            "start_emotion": emotional_arc.get("start_emotion", "未知"),
            "end_emotion": emotional_arc.get("end_emotion", "未知"),
            "arc_description": emotional_arc.get("description", "")
        }
        
        # 提取角色成长主题
        character_arcs = swp.get("character_arcs", {})
        protagonist_growth = character_arcs.get("protagonist_growth", "")
        
        # 提取世界观展开计划
        worldview_plan = swp.get("worldview_revelation", {})
        
        # 提取冲突主题
        conflict_theme = swp.get("conflict_escalation", {})
        
        # 提取爽点设计
        satisfaction_points = swp.get("satisfaction_points", [])
        
        # 增强事件信息
        major_events = swp.get("event_system", {}).get("major_events", [])
        enriched_events = []
        
        for idx, event in enumerate(major_events):
            # 分析事件在情绪曲线中的位置
            position_in_arc = self._map_to_emotional_arc(
                event.get("chapter_range", ""), 
                emotional_arc
            )
            
            # 查找关联事件
            related_events = self._find_related_events(event, major_events, idx)
            
            enriched_event = {
                "event_id": event.get("id") or f"event_{idx}",
                "name": event.get("name", "未命名"),
                "main_goal": event.get("main_goal", ""),
                "emotional_focus": event.get("emotional_focus", ""),
                "chapter_range": event.get("chapter_range", ""),
                "role_in_stage_arc": event.get("role_in_stage_arc", ""),
                "position_in_emotional_arc": position_in_arc,
                "related_events": related_events,
                "is_turning_point": event.get("is_turning_point", False)
            }
            enriched_events.append(enriched_event)
        
        return {
            "stage_name": stage_name,
            "stage_range": stage_plan.get("chapter_range", "未知"),
            "emotional_arc": emotional_arc_summary,
            "protagonist_growth_theme": protagonist_growth,
            "worldview_revelation_plan": worldview_plan,
            "conflict_theme": conflict_theme,
            "satisfaction_points": satisfaction_points,
            "events": enriched_events,
            "design_goals": {
                "expectation_density": "每3-5章至少1个期待释放",
                "type_diversity": "同阶段同类型不超过2个",
                "emotional_coherence": "期待类型匹配情绪曲线",
                "satisfaction_alignment": "期待释放对准爽点章节"
            }
        }
    
    def _map_to_emotional_arc(self, chapter_range: str, emotional_arc: Dict) -> str:
        """映射事件到情绪曲线位置"""
        if not chapter_range:
            return "unknown"
        
        # 解析章节范围
        try:
            import re
            numbers = re.findall(r'\d+', chapter_range)
            if len(numbers) >= 2:
                start_ch = int(numbers[0])
                end_ch = int(numbers[1])
                mid_ch = (start_ch + end_ch) // 2
                
                # 获取阶段总章节范围
                total_start = 1
                total_end = 50  # 默认
                
                if mid_ch <= total_start + (total_end - total_start) * 0.25:
                    return "start"
                elif mid_ch <= total_start + (total_end - total_start) * 0.5:
                    return "rising"
                elif mid_ch <= total_start + (total_end - total_start) * 0.75:
                    return "climax_building"
                else:
                    return "end"
        except:
            pass
        
        return "middle"
    
    def _find_related_events(self, event: Dict, all_events: List[Dict], 
                            current_idx: int) -> List[str]:
        """查找关联事件"""
        related = []
        event_name = event.get("name", "")
        
        # 检查前后事件
        for idx, other in enumerate(all_events):
            if idx == current_idx:
                continue
            
            other_name = other.get("name", "")
            
            # 简单文本匹配（实际可以更复杂）
            if any(keyword in other_name for keyword in event_name.split()[:2]):
                related.append(other.get("id") or f"event_{idx}")
        
        return related[:2]  # 最多返回2个关联事件
    
    def generate_stage_expectations_batch(self, stage_name: str, 
                                          stage_plan: Dict) -> Optional[Dict]:
        """
        批量为一个阶段的所有事件生成期待类型
        
        Args:
            stage_name: 阶段名称
            stage_plan: 阶段详细计划
            
        Returns:
            期待感映射字典
        """
        try:
            # 构建 enriched 输入
            input_data = self.build_stage_input(stage_name, stage_plan)
            
            # 如果没有API客户端，使用本地规则
            if not self.api_client:
                self.logger.info(f"⚠️ 无API客户端，使用本地规则生成 {stage_name} 期待感")
                return self._generate_local_expectations(input_data)
            
            # 调用API批量生成
            self.logger.info(f"🎯 开始为 {stage_name} 批量生成期待感映射...")
            
            prompt = self._build_expectation_prompt(input_data)
            
            result = self.api_client.generate_content_with_retry(
                content_type="expectation_batch_generation",
                user_prompt=prompt,
                purpose=f"为{stage_name}生成期待感映射"
            )
            
            if result and isinstance(result, dict):
                self.logger.info(f"✅ {stage_name} 期待感映射生成成功")
                return result.get("event_expectations", {})
            else:
                self.logger.warning(f"⚠️ {stage_name} API返回格式异常，使用本地规则")
                return self._generate_local_expectations(input_data)
                
        except Exception as e:
            self.logger.error(f"❌ 生成 {stage_name} 期待感映射失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_expectation_prompt(self, input_data: Dict) -> str:
        """构建期待感生成Prompt"""
        
        return f"""# 期待感编排任务

请基于以下完整的阶段计划，为每个事件设计最契合的期待感类型。

## 阶段信息
```json
{json.dumps(input_data, ensure_ascii=False, indent=2)}
```

## 20种期待类型说明

### 基础类型（6种）
1. **SHOWCASE** - 展示橱窗：提前展示奖励或能力的强大
2. **SUPPRESSION_RELEASE** - 压抑释放：制造阻碍后释放爽感
3. **NESTED_DOLL** - 套娃期待：大期待包着小期待
4. **EMOTIONAL_HOOK** - 情绪钩子：打脸、认同、身份揭秘
5. **POWER_GAP** - 实力差距：期待变强的过程
6. **MYSTERY_FORESHADOW** - 伏笔揭秘：埋下线索后揭晓

### 扩展类型（14种）
7. **PIG_EATS_TIGER** - 扮猪吃虎：隐藏实力后打脸
8. **SHOW_OFF_FACE_SLAP** - 装逼打脸：展示实力打脸
9. **IDENTITY_REVEAL** - 身份反转：隐藏身份揭晓
10. **BEAUTY_FAVOR** - 美人恩：女主好感进展
11. **FORTUITOUS_ENCOUNTER** - 机缘巧合：意外获得奇遇
12. **COMPETITION** - 比试切磋：宗门大比等
13. **AUCTION_TREASURE** - 拍卖会争宝
14. **SECRET_REALM_EXPLORATION** - 秘境探险
15. **ALCHEMY_CRAFTING** - 炼丹炼器
16. **FORMATION_BREAKING** - 阵法破解
17. **SECT_MISSION** - 宗门任务
18. **CROSS_WORLD_TELEPORT** - 跨界传送
19. **CRISIS_RESCUE** - 危机救援
20. **MASTER_INHERITANCE** - 师恩传承

## 编排原则

### 1. 情绪曲线匹配
- **压抑期** → MYSTERY_FORESHADOW(埋线), POWER_GAP(期待变强)
- **上升期** → SHOWCASE(展示), FORTUITOUS_ENCOUNTER(奇遇)
- **爆发期** → SUPPRESSION_RELEASE(释放), IDENTITY_REVEAL(揭秘)
- **收尾期** → CRISIS_RESCUE(救援), MASTER_INHERITANCE(传承)

### 2. 事件关联设计
- 事件A的释放可以是事件B的种植
- 设计"期待链"：A种植 → B发酵 → C释放

### 3. 爽点对齐
- satisfaction_points中的爽点，前置3章必须有对应期待

### 4. 类型多样化
- 同阶段同类型不超过2个
- 相邻事件期待类型尽量不重复

## 输出格式

```json
{{
  "stage_expectation_strategy": "本阶段整体期待策略简述（50字内）",
  "event_expectations": [
    {{
      "event_id": "事件ID",
      "expectation_type": "TYPE_NAME",
      "reasoning": "选择理由（基于情绪曲线/事件关联/世界观展开）",
      "planting_chapter": 1,
      "target_chapter": 4,
      "linked_events": ["关联事件ID"]
    }}
  ]
}}
```

请确保：
1. 每个事件都有合理的期待类型
2. 种植章节 ≤ 事件开始章节
3. 目标释放章节 ≥ 事件结束章节
4. 关联事件确实有关联逻辑
"""
    
    def _generate_local_expectations(self, input_data: Dict) -> Dict:
        """本地规则生成（无API时降级）"""
        from web.api.phase_generation_api import select_expectation_type
        
        event_expectations = {}
        stage_name = input_data.get("stage_name", "")
        
        # 阶段偏好映射
        stage_preferences = {
            "opening_stage": ["FORTUITOUS_ENCOUNTER", "SHOWCASE", "POWER_GAP"],
            "development_stage": ["POWER_GAP", "MYSTERY_FORESHADOW", "NESTED_DOLL"],
            "climax_stage": ["SUPPRESSION_RELEASE", "IDENTITY_REVEAL", "PIG_EATS_TIGER"],
            "ending_stage": ["CRISIS_RESCUE", "MASTER_INHERITANCE", "SHOWCASE"]
        }
        
        preferences = stage_preferences.get(stage_name, ["SHOWCASE", "NESTED_DOLL"])
        
        for event in input_data.get("events", []):
            event_id = event.get("event_id")
            
            # 使用本地规则选择
            exp_type = select_expectation_type({
                "name": event.get("name"),
                "main_goal": event.get("main_goal"),
                "emotional_focus": event.get("emotional_focus"),
                "role_in_stage_arc": event.get("role_in_stage_arc")
            })
            
            # 如果没有选到，使用阶段偏好
            if not exp_type:
                import random
                exp_type = random.choice(preferences)
            
            # 解析章节范围
            chapter_range = event.get("chapter_range", "1-5")
            try:
                import re
                numbers = re.findall(r'\d+', chapter_range)
                if len(numbers) >= 2:
                    start_ch = int(numbers[0])
                    end_ch = int(numbers[1])
                else:
                    start_ch = 1
                    end_ch = 5
            except:
                start_ch = 1
                end_ch = 5
            
            event_expectations[event_id] = {
                "expectation_type": exp_type.value if hasattr(exp_type, 'value') else str(exp_type),
                "planting_chapter": start_ch,
                "target_chapter": end_ch,
                "reasoning": f"基于{stage_name}阶段偏好选择"
            }
        
        return event_expectations


# 便捷函数
def generate_enriched_expectation_maps(stage_plans: Dict, api_client=None) -> Dict:
    """
    为所有阶段生成增强版期待感映射
    
    Args:
        stage_plans: 所有阶段的详细计划
        api_client: API客户端（可选）
        
    Returns:
        所有阶段的期待感映射
    """
    manager = EnrichedExpectationManager(api_client)
    all_expectation_maps = {}
    
    for stage_name, stage_plan in stage_plans.items():
        expectation_map = manager.generate_stage_expectations_batch(
            stage_name, stage_plan
        )
        if expectation_map:
            all_expectation_maps[stage_name] = expectation_map
    
    return all_expectation_maps
