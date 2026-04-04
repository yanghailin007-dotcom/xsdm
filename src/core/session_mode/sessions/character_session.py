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
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 200)

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "character_design",
            default="",
            world_overview=core_worldview.get('world_overview', '待定'),
            power_system=core_worldview.get('power_system', '待定'),
            key_locations=core_worldview.get('key_locations', []),
            world_rules=core_worldview.get('world_rules', []),
            faction_names=[f.get('name') for f in faction_system.get('factions', [])],
            main_conflict=faction_system.get('main_conflict', '待定'),
            faction_power_balance=faction_system.get('faction_power_balance', '待定'),
            core_selling_points=market_analysis.get('core_selling_points', []),
            target_audience=market_analysis.get('target_audience', '待定'),
            total_chapters=total_chapters
        )
        
        if not prompt:
            self.session_logger.error("[CharacterSession] 未找到 character_design 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="character_design")

    def _execute_emotional_growth(self) -> Optional[Dict]:
        """执行步骤2: 情绪蓝图与成长规划"""
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 200)
        characters = self.results.get("character_design", {}).get("characters", {})
        protagonist = characters.get('protagonist', {}) if isinstance(characters, dict) else {}
        if not protagonist and isinstance(characters, list) and characters:
            protagonist = characters[0]

        protagonist_name = protagonist.get('basic_info', {}).get('name', '主角')
        protagonist_goals = protagonist.get('goals', '待定')
        protagonist_abilities = protagonist.get('abilities', '待定')
        power_system = self.novel_data.get("core_worldview", {}).get("power_system", "")

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "emotional_growth",
            default="",
            total_chapters=total_chapters,
            protagonist_name=protagonist_name,
            protagonist_goals=protagonist_goals,
            protagonist_abilities=protagonist_abilities,
            power_system=power_system
        )
        
        if not prompt:
            self.session_logger.error("[CharacterSession] 未找到 emotional_growth 提示词模板")
            return None
            
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
