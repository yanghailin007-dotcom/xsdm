"""
Character Session - 角色与叙事会话
负责: 核心角色设计 + 情绪蓝图 + 成长规划
"""

import json
from typing import Dict, Optional, Any

from src.core.session_mode.novel_generation_session import NovelGenerationSession


class CharacterSession(NovelGenerationSession):
    """角色与叙事会话"""

    STEPS = ["character_design", "emotional_growth"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results: Dict[str, Any] = {}

    def execute_all_steps(self) -> bool:
        """执行 Character 域的所有步骤"""
        self.session_logger.info("[CharacterSession] 开始执行步骤...")

        # Step 1: 核心角色设计
        step1_result = self._execute_character_design()
        if not step1_result:
            self.session_logger.error("[CharacterSession] 角色设计步骤失败")
            return False
        self.results["character_design"] = step1_result

        # Step 2: 情绪蓝图与成长规划
        step2_result = self._execute_emotional_growth()
        if not step2_result:
            self.session_logger.error("[CharacterSession] 情绪与成长规划步骤失败")
            return False
        self.results["emotional_growth"] = step2_result

        self.session_logger.info("[CharacterSession] 所有步骤执行完成")
        return True

    def _execute_character_design(self) -> Optional[Dict]:
        """执行步骤1: 核心角色设计"""
        # 从上游 brief 或 novel_data 获取世界观和势力信息
        core_worldview = self.novel_data.get("core_worldview", {})
        faction_system = self.novel_data.get("faction_system", {})
        market_analysis = self.novel_data.get("market_analysis", {})

        prompt = f"""
请执行【步骤1：核心角色设计】

基于小说的世界观和势力系统，设计核心角色阵容。

## 世界观信息
- 世界概览: {core_worldview.get('world_overview', '待定')}
- 力量体系: {core_worldview.get('power_system', '待定')}
- 关键地点: {core_worldview.get('key_locations', [])}

## 势力系统信息
- 主要势力: {[f.get('name') for f in faction_system.get('factions', [])]}
- 主要冲突: {faction_system.get('main_conflict', '待定')}

## 设计要求
设计以下角色：
1. 主角（含姓名、性格、背景、目标、能力/金手指、成长弧线）
2. 核心盟友（1-3位）
3. 主要反派/宿敌（1-2位）
4. 导师/引路人（1位）

## 输出要求
返回合法 JSON，顶层字段为 "characters"，包含角色列表。
每个角色需包含: basic_info, personality, background, goals, abilities, relationships, growth_arc
"""
        return self.send_structured_message(prompt, purpose="character_design")

    def _execute_emotional_growth(self) -> Optional[Dict]:
        """执行步骤2: 情绪蓝图与成长规划"""
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 200)
        characters = self.results.get("character_design", {}).get("characters", [])
        protagonist = characters[0] if characters else {}

        prompt = f"""
请执行【步骤2：情绪蓝图与成长规划】

基于核心角色设定，同时设计全书情绪蓝图和主角成长规划。

## 全书信息
- 总章节数: {total_chapters}
- 主角: {protagonist.get('basic_info', {}).get('name', '主角')} 
- 主角目标: {protagonist.get('goals', '待定')}

## 输出要求
返回合法 JSON，必须包含两个顶层字段：
1. "emotional_blueprint": 情绪蓝图
   - emotional_curves: 情绪曲线（每阶段情绪类型、强度、触发点）
   - emotional_hooks: 情绪钩子（悬念、冲突、爽点安排）
   - reader_journey: 读者情感旅程映射

2. "global_growth_plan": 成长规划
   - protagonist_growth: 主角成长阶段
   - power_progression: 力量体系进阶路线
   - milestone_events: 关键里程碑事件
   - stage_goals: 各阶段目标

注意：情绪蓝图和成长规划要相互协调，成长节点的情绪要有起伏变化。
"""
        return self.send_structured_message(prompt, purpose="emotional_growth")

    def export_results(self) -> Dict[str, Any]:
        """导出结果，映射到 novel_data 的字段名"""
        characters = self.results.get("character_design", {})
        emotional = self.results.get("emotional_growth", {})

        return {
            "character_design": characters.get("characters", {}),
            "emotional_blueprint": emotional.get("emotional_blueprint", {}),
            "global_growth_plan": emotional.get("global_growth_plan", {}),
        }
