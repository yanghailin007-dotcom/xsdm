"""
FoundationSetupSession - 基础设定会话（混合模式第一步）

合并传统13步模式的前4步：
  1. writing_style_guide  (写作风格指南)
  2. market_analysis      (市场分析)
  3. core_worldview       (世界观)
  4. faction_system       (势力系统)

设计原则：
- Prompt 与传统模式完全一致（直接复用传统模式中的 prompt 字符串构造逻辑）
- 输出字段与传统模式完全一致
- 保存路径与传统模式完全一致
- 后续步骤（character_design  onwards）保持传统模式不变
"""

import json
from typing import Dict, Optional, Any

from src.core.session_mode.novel_generation_session import NovelGenerationSession


class FoundationSetupSession(NovelGenerationSession):
    """
    基础设定会话
    负责生成写作风格、市场分析、世界观、势力系统四个前置产物。
    """

    STEPS = ["writing_style", "market_analysis", "worldview", "faction_system"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results: Dict[str, Any] = {}

    def execute_all_steps(self) -> bool:
        """执行 FoundationSetup 域的所有步骤"""
        self.session_logger.info("[FoundationSetupSession] 开始执行基础设定...")

        # Step 1 & 2: 合并生成写作风格 + 市场分析
        step1_result = self._generate_foundation_planning_combined()
        if not step1_result:
            self.session_logger.error("[FoundationSetupSession] 写作风格+市场分析生成失败")
            return False
        self.results.update(step1_result)
        self.session_logger.info("[FoundationSetupSession] 写作风格+市场分析生成成功")

        # Step 3 & 4: 合并生成世界观 + 势力系统
        step2_result = self._generate_worldview_and_factions_combined()
        if not step2_result:
            self.session_logger.error("[FoundationSetupSession] 世界观+势力系统生成失败")
            return False
        self.results.update(step2_result)
        self.session_logger.info("[FoundationSetupSession] 世界观+势力系统生成成功")

        self.session_logger.info("[FoundationSetupSession] 所有基础设定步骤执行完成")
        return True

    def export_results(self) -> Dict[str, Any]:
        """导出与传统模式完全一致的字段结构"""
        return {
            "writing_style_guide": self.results.get("writing_style_guide", {}),
            "market_analysis": self.results.get("market_analysis", {}),
            "core_worldview": self.results.get("core_worldview", {}),
            "faction_system": self.results.get("faction_system", {}),
        }

    # ------------------------------------------------------------------
    # Step 1 & 2: 写作风格 + 市场分析（合并生成）
    # Prompt 与 ContentGenerator.generate_foundation_planning 完全一致
    # ------------------------------------------------------------------
    def _generate_foundation_planning_combined(self) -> Optional[Dict]:
        category = self.novel_data.get("category", "未分类")
        creative_seed = self.novel_data.get("creative_seed") or self.novel_data.get("selected_plan", {})
        selected_plan = self.novel_data.get("selected_plan", {})
        novel_title = self.novel_data.get("novel_title", "")
        novel_synopsis = self.novel_data.get("novel_synopsis", "")

        user_prompt = f"""
请为以下小说同时生成【写作风格指南】和【市场分析】两部分内容。

## 小说信息
小说标题: {novel_title}
小说简介: {novel_synopsis}
小说分类: {category}
小说创意: {creative_seed}
核心主题: {selected_plan.get('core_direction', '')}
目标读者: {selected_plan.get('target_audience', '')}

## 输出格式要求（严格遵守）

你必须返回一个 JSON 对象，且必须包含以下两个顶层字段：
1. "writing_style_guide" - 写作风格指南
2. "market_analysis" - 市场分析

正确的返回格式示例：
```json
{{
    "writing_style_guide": {{
        "core_style": "核心风格描述...",
        "language_characteristics": ["特点1", "特点2", "特点3"],
        "narration_techniques": ["技巧1", "技巧2"],
        "dialogue_style": "对话风格描述...",
        "chapter_techniques": ["技巧1", "技巧2"],
        "key_principles": ["原则1", "原则2", "原则3"]
    }},
    "market_analysis": {{
        "target_platform": "番茄小说",
        "genre_positioning": "类型定位描述",
        "core_selling_points": ["卖点1", "卖点2", "卖点3"],
        "target_audience": "目标读者画像...",
        "competitive_advantages": ["优势1", "优势2"],
        "market_risks": ["风险1", "风险2"],
        "confidence_score": 8
    }}
}}
```

## 内容要求

### writing_style_guide 字段内容：
- core_style: 核心风格定位（简洁描述，100字以内）
- language_characteristics: 语言特点（列表，3-5个关键词）
- narration_techniques: 叙事技巧（列表，2-3个要点）
- dialogue_style: 对话风格（简洁描述）
- chapter_techniques: 章节技巧（列表）
- key_principles: 核心原则（列表，3-5条）

### market_analysis 字段内容：
- target_platform: 目标平台（如：番茄小说）
- genre_positioning: 类型定位
- core_selling_points: 核心卖点（列表，3-5条，必须具体且有吸引力）
- target_audience: 目标读者画像（详细描述）
- competitive_advantages: 竞争优势（列表）
- market_risks: 市场风险（列表）
- confidence_score: 信心评分（1-10分）

【重要】必须严格按照上述 JSON 格式返回，包含 writing_style_guide 和 market_analysis 两个顶层字段，否则无法解析。
"""

        result = self.send_structured_message(user_prompt, purpose="foundation_planning")

        if not result or not isinstance(result, dict):
            self.session_logger.error("[FoundationSetupSession] foundation_planning API 返回无效")
            return None

        has_wsg = 'writing_style_guide' in result and isinstance(result['writing_style_guide'], dict)
        has_ma = 'market_analysis' in result and isinstance(result['market_analysis'], dict)

        if not has_wsg or not has_ma:
            self.session_logger.warning(
                f"[FoundationSetupSession] 返回格式不完整: has_wsg={has_wsg}, has_ma={has_ma}"
            )
            return None

        # 防御性填充 writing_style_guide 缺失字段
        wsg = result['writing_style_guide']
        for key, default in [
            ('language_characteristics', ["简洁明了", "生动形象", "节奏感强"]),
            ('narration_techniques', ["第三人称限知", "快节奏推进"]),
            ('chapter_techniques', ["每章留悬念", "情绪起伏明显"]),
            ('key_principles', ["保持风格一致性", "注意节奏控制", "强化读者代入感"]),
        ]:
            if key not in wsg:
                wsg[key] = default
        for key in ['core_style', 'dialogue_style']:
            if key not in wsg:
                wsg[key] = "待补充"

        return {
            "writing_style_guide": wsg,
            "market_analysis": result['market_analysis'],
        }

    # ------------------------------------------------------------------
    # Step 3 & 4: 世界观 + 势力系统（合并生成）
    # Prompt 与 ContentGenerator.generate_worldview_with_factions 完全一致
    # ------------------------------------------------------------------
    def _generate_worldview_and_factions_combined(self) -> Optional[Dict]:
        novel_title = self.novel_data.get("novel_title", "")
        novel_synopsis = self.novel_data.get("novel_synopsis", "")
        selected_plan = self.novel_data.get("selected_plan", {})
        market_analysis = self.results.get("market_analysis") or self.novel_data.get("market_analysis", {})

        core_settings = selected_plan.get("core_settings", {})
        story_development = selected_plan.get("story_development", {})
        world_background = core_settings.get("world_background", "")
        golden_finger = core_settings.get("golden_finger", "")
        core_selling_points = core_settings.get("core_selling_points", [])
        protagonist_position = story_development.get("protagonist_position", "")
        main_plot = story_development.get("main_plot", [])

        user_prompt = f"""
## 小说信息
- **小说标题**: {novel_title}
- **小说简介**: {novel_synopsis}
- **市场分析**: {json.dumps(market_analysis, ensure_ascii=False)}
- **核心设定**:
  - 世界观背景: {world_background}
  - 金手指/系统: {golden_finger}
  - 核心爽点: {', '.join(core_selling_points) if isinstance(core_selling_points, list) else core_selling_points}
  - 主角定位: {protagonist_position}
  - 主线脉络: {', '.join(main_plot) if isinstance(main_plot, list) else main_plot}

## 输出格式要求（严格遵守）

你必须返回一个 JSON 对象，且必须包含以下两个顶层字段：
1. "core_worldview" - 世界观框架
2. "faction_system" - 势力系统

正确的返回格式示例：
```json
{{
    "core_worldview": {{
        "world_overview": "世界整体描述...",
        "power_system": "力量体系详细说明...",
        "world_rules": ["规则1", "规则2"],
        "key_locations": ["地点1", "地点2", "地点3"],
        "time_background": "时间背景描述"
    }},
    "faction_system": {{
        "factions": [
            {{
                "name": "势力名称",
                "description": "势力描述",
                "goals": "势力目标",
                "strengths": "优势",
                "weaknesses": "劣势",
                "relationships": "与其他势力的关系"
            }}
        ],
        "main_conflict": "主要冲突描述",
        "faction_power_balance": "力量对比描述",
        "recommended_starting_faction": "推荐初始势力"
    }}
}}
```

## 内容要求

### core_worldview 字段内容：
- world_overview: 世界概览（整体描述，200字以内）
- power_system: 力量体系（修炼/能力系统详细说明）
- world_rules: 世界规则（运行法则和限制，列表）
- key_locations: 关键地点（列表，3-5个重要场景）
- time_background: 时间背景

### faction_system 字段内容：
- factions: 势力列表（3-7个主要势力），每个包含：
  - name: 势力名称
  - description: 势力描述
  - goals: 势力目标
  - strengths: 优势
  - weaknesses: 劣势
  - relationships: 与其他势力的关系
- main_conflict: 主要冲突（势力间核心矛盾）
- faction_power_balance: 势力力量对比
- recommended_starting_faction: 推荐主角初始势力

## 设计要求
1. **逻辑自洽**：势力系统必须与世界观设定（尤其是力量体系）保持一致
2. **冲突驱动**：势力间关系要有明确的矛盾点和冲突潜力
3. **主角切入点**：提供主角如何融入这个世界的清晰路径
4. **创新性**：避免常见套路，追求独特性和新颖性

【重要】必须严格按照上述 JSON 格式返回，包含 core_worldview 和 faction_system 两个顶层字段，否则无法解析。
"""

        result = self.send_structured_message(user_prompt, purpose="worldview_with_factions")

        if not result or not isinstance(result, dict):
            self.session_logger.error("[FoundationSetupSession] worldview_with_factions API 返回无效")
            return None

        has_cw = 'core_worldview' in result and isinstance(result['core_worldview'], dict)
        has_fs = 'faction_system' in result and isinstance(result['faction_system'], dict)

        if not has_cw:
            self.session_logger.error("[FoundationSetupSession] 返回缺少 core_worldview")
            return None

        if not has_fs:
            self.session_logger.warning("[FoundationSetupSession] 返回缺少 faction_system，使用默认")
            result['faction_system'] = {
                "factions": [],
                "main_conflict": "待定",
                "faction_power_balance": "待定",
                "recommended_starting_faction": "待定"
            }

        return {
            "core_worldview": result['core_worldview'],
            "faction_system": result['faction_system'],
        }
