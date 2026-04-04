"""
Foundation Session - 创作基线会话
负责: 写作风格 + 市场分析 + 世界观 + 势力系统
"""

import json
from typing import Dict, Optional, Any

from src.core.session_mode.novel_generation_session import NovelGenerationSession


class FoundationSession(NovelGenerationSession):
    """创作基线会话"""

    STEPS = ["foundation_planning", "worldview_with_factions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results: Dict[str, Any] = {}

    def execute_all_steps(self) -> bool:
        """执行 Foundation 域的所有步骤"""
        self.session_logger.info("[FoundationSession] 开始执行步骤...")

        # Step 1: 基础规划（写作风格 + 市场分析）
        step1_result = self._execute_foundation_planning()
        if not step1_result:
            self.session_logger.error("[FoundationSession] 基础规划步骤失败")
            return False
        self.results["foundation_planning"] = step1_result

        # Step 2: 世界观与势力系统
        step2_result = self._execute_worldview_factions()
        if not step2_result:
            self.session_logger.error("[FoundationSession] 世界观与势力步骤失败")
            return False
        self.results["worldview_factions"] = step2_result

        self.session_logger.info("[FoundationSession] 所有步骤执行完成")
        return True

    def _execute_foundation_planning(self) -> Optional[Dict]:
        """执行步骤1: 基础规划"""
        creative_seed = self.novel_data.get("creative_seed") or self.novel_data.get("selected_plan", {})
        category = self.novel_data.get("category", "未分类")
        
        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "foundation_planning",
            default="",
            creative_seed=json.dumps(creative_seed, ensure_ascii=False, indent=2),
            category=category
        )
        
        if not prompt:
            self.session_logger.error("[FoundationSession] 未找到 foundation_planning 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="foundation_planning")

    def _execute_worldview_factions(self) -> Optional[Dict]:
        """执行步骤2: 世界观与势力系统"""
        foundation = self.results.get("foundation_planning", {})
        writing_style = foundation.get("writing_style_guide", {})
        market = foundation.get("market_analysis", {})
        
        creative_seed = self.novel_data.get("creative_seed") or self.novel_data.get("selected_plan", {})
        core_settings = creative_seed.get("core_settings", {}) if isinstance(creative_seed, dict) else {}

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "worldview_factions",
            default="",
            core_style=writing_style.get('core_style', '待定'),
            language_characteristics=writing_style.get('language_characteristics', []),
            key_principles=writing_style.get('key_principles', []),
            target_platform=market.get('target_platform', '番茄小说'),
            genre_positioning=market.get('genre_positioning', '待定'),
            core_selling_points=market.get('core_selling_points', []),
            world_background=core_settings.get('world_background', '待定'),
            golden_finger=core_settings.get('golden_finger', '待定'),
            core_selling_points_ref=core_settings.get('core_selling_points', [])
        )
        
        if not prompt:
            self.session_logger.error("[FoundationSession] 未找到 worldview_factions 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="worldview_factions")

    def export_results(self) -> Dict[str, Any]:
        """导出结果，映射到 novel_data 的字段名"""
        foundation = self.results.get("foundation_planning", {})
        worldview = self.results.get("worldview_factions", {})
        
        return {
            "writing_style_guide": foundation.get("writing_style_guide", {}),
            "market_analysis": foundation.get("market_analysis", {}),
            "core_worldview": worldview.get("core_worldview", {}),
            "faction_system": worldview.get("faction_system", {}),
        }
