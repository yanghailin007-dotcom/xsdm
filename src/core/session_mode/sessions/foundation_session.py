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
        
        prompt = f"""
请执行【步骤1：基础规划】

基于小说基础信息和以下创意种子，同时生成【写作风格指南】和【市场分析】。

## 创意种子
{json.dumps(creative_seed, ensure_ascii=False, indent=2)}

## 输出要求
返回合法 JSON，必须包含两个顶层字段：
1. "writing_style_guide": 写作风格指南（包含 core_style, language_characteristics, narration_techniques, dialogue_style, chapter_techniques, key_principles）
2. "market_analysis": 市场分析（包含 target_platform, genre_positioning, core_selling_points, target_audience, competitive_advantages, market_risks, confidence_score）
"""
        return self.send_structured_message(prompt, purpose="foundation_planning")

    def _execute_worldview_factions(self) -> Optional[Dict]:
        """执行步骤2: 世界观与势力系统"""
        foundation = self.results.get("foundation_planning", {})
        writing_style = foundation.get("writing_style_guide", {})
        market = foundation.get("market_analysis", {})
        
        creative_seed = self.novel_data.get("creative_seed") or self.novel_data.get("selected_plan", {})
        core_settings = creative_seed.get("core_settings", {}) if isinstance(creative_seed, dict) else {}

        prompt = f"""
请执行【步骤2：世界观与势力系统】

基于已确定的写作风格和市场定位，设计小说的世界观框架和势力/阵营系统。

## 已确定的写作风格
- 核心风格: {writing_style.get('core_style', '待定')}
- 语言特点: {writing_style.get('language_characteristics', [])}

## 市场定位
- 目标平台: {market.get('target_platform', '番茄小说')}
- 类型定位: {market.get('genre_positioning', '待定')}

## 核心设定参考
- 世界观背景: {core_settings.get('world_background', '待定')}
- 金手指/系统: {core_settings.get('golden_finger', '待定')}

## 输出要求
返回合法 JSON，必须包含两个顶层字段：
1. "core_worldview": 世界观框架（world_overview, power_system, world_rules, key_locations, time_background）
2. "faction_system": 势力系统（factions 列表, main_conflict, faction_power_balance, recommended_starting_faction）

注意：势力系统必须与世界观中的力量体系严格保持一致。
"""
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
