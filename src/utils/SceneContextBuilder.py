"""场景生成上下文构建器 - 统一的背景信息构建

所有场景生成（单章、多章、一次性生成）都应该使用相同的背景信息。
"""

from typing import Dict, Optional
from src.utils.logger import get_logger


class SceneContextBuilder:
    """场景生成上下文构建器 - 提供统一的上下文构建方法"""

    def __init__(self):
        self.logger = get_logger("SceneContextBuilder")

    def build_comprehensive_context(self, medium_event: Dict, major_event: Dict,
                                    novel_data: Dict, stage_name: str) -> str:
        """构建场景生成的综合上下文（所有场景生成方式共用）

        包含：
        1. 角色信息（主角、重要配角）
        2. 世界观设定（修炼体系、世界规则）
        3. 重大事件完整信息
        4. 阶段上下文

        Args:
            medium_event: 当前中型事件
            major_event: 所属重大事件
            novel_data: 小说数据
            stage_name: 阶段名称

        Returns:
            格式化的上下文字符串
        """
        context_parts = []

        # 1. 角色信息
        character_design = novel_data.get("character_design", {})
        if character_design:
            character_context = self.build_character_context(character_design)
            if character_context:
                context_parts.append(character_context)

        # 2. 世界观设定
        core_worldview = novel_data.get("core_worldview", {})
        if core_worldview:
            worldview_context = self.build_worldview_context(core_worldview)
            if worldview_context:
                context_parts.append(worldview_context)

        # 3. 重大事件完整信息
        if major_event:
            major_event_context = self.build_major_event_context(major_event)
            if major_event_context:
                context_parts.append(major_event_context)

        # 4. 阶段上下文
        if stage_name:
            stage_context = self.build_stage_context(stage_name, medium_event, novel_data)
            if stage_context:
                context_parts.append(stage_context)

        return "\n\n".join(context_parts) if context_parts else ""

    def build_character_context(self, character_design: Dict) -> str:
        """构建角色信息上下文"""
        if not character_design:
            return ""

        parts = ["## 角色信息（必须严格遵守）"]

        # 主角信息
        main_character = character_design.get("main_character", {})
        if main_character:
            parts.append("### 主角")
            parts.append(f"- **姓名**: {main_character.get('name', '未命名')}")

            # 身份
            identity = main_character.get('identity', '')
            if not identity:
                identity = main_character.get('background', '')
            parts.append(f"- **身份**: {identity or '未知'}")

            # 核心性格
            core_personality = main_character.get('core_personality', '')
            if core_personality:
                parts.append(f"- **核心性格**: {core_personality}")

            # 核心性格-行为矩阵
            soul_matrix = main_character.get("soul_matrix", [])
            if soul_matrix:
                parts.append("- **核心性格-行为矩阵**:")
                for trait in soul_matrix:
                    trait_str = trait.get("trait", "")
                    behavior_str = trait.get("behavior", "")
                    if trait_str or behavior_str:
                        parts.append(f"  - [{trait_str}] → {behavior_str}")

            # 生活特征
            living_characteristics = main_character.get("living_characteristics", {})
            if isinstance(living_characteristics, dict):
                physical_presence = living_characteristics.get("physical_presence", "")
                if physical_presence:
                    parts.append(f"- **外形特征**: {physical_presence}")

                distinctive_traits = living_characteristics.get("distinctive_traits", "")
                if distinctive_traits:
                    parts.append(f"- **特征**: {distinctive_traits}")

            # 修炼信息
            cultivation = main_character.get("cultivation", {})
            if cultivation:
                realm = cultivation.get("current_realm", "未知")
                technique = cultivation.get("main_technique", "无")
                parts.append(f"- **修为**: {realm}")
                if technique != "无":
                    parts.append(f"- **主修功法**: {technique}")

            # 对话风格
            dialogue_style = main_character.get("dialogue_style_example", "")
            if dialogue_style:
                parts.append(f"- **对话风格**: {dialogue_style}")

            # 成长弧线
            growth_arc = main_character.get("growth_arc", "")
            if growth_arc:
                parts.append(f"- **成长弧线**: {growth_arc}")

        # 重要配角
        important_chars = character_design.get("important_characters", [])
        if important_chars:
            parts.append("\n### 重要配角")
            for char in important_chars:
                char_name = char.get("name", "未命名")
                char_role = char.get("role", "未知角色")
                parts.append(f"- **{char_name}**: {char_role}")

                # 核心性格 traits
                core_traits = char.get("core_traits", [])
                if isinstance(core_traits, list) and core_traits:
                    traits_str = "、".join([t.get("core_trait", "") for t in core_traits if t.get("core_trait")])
                    if traits_str:
                        parts.append(f"  - 性格: {traits_str}")

                # 初始状态
                initial_state = char.get("initial_state", {})
                if isinstance(initial_state, dict):
                    desc = initial_state.get("description", "")
                    if desc:
                        parts.append(f"  - 描述: {desc}")

                    cultivation = initial_state.get("cultivation_level", "")
                    if cultivation:
                        parts.append(f"  - 修为: {cultivation}")

        return "\n".join(parts)

    def build_worldview_context(self, core_worldview: Dict) -> str:
        """构建世界观设定上下文"""
        if not core_worldview:
            return ""

        parts = ["## 世界观设定（必须严格遵守）"]

        # 时代背景 era
        era = core_worldview.get("era", "")
        if era:
            parts.append(f"- **时代背景**: {era}")

        # 核心矛盾 core_conflict
        core_conflict = core_worldview.get("core_conflict", "")
        if core_conflict:
            parts.append(f"- **核心矛盾**: {core_conflict}")

        # 世界观概述 overview
        overview = core_worldview.get("overview", "")
        if overview:
            parts.append(f"- **世界观概述**: {overview}")

        # 热门元素 hot_elements
        hot_elements = core_worldview.get("hot_elements", [])
        if hot_elements:
            if isinstance(hot_elements, list) and len(hot_elements) > 0:
                elements_str = "、".join(hot_elements[:10])  # 限制数量
                parts.append(f"- **热门元素**: {elements_str}")

        # 力量体系 power_system
        power_system = core_worldview.get("power_system", "")
        if power_system:
            # 限制长度，避免过长
            if len(power_system) > 500:
                power_system = power_system[:500] + "..."
            parts.append(f"- **力量体系**: {power_system}")

        # 社会结构 social_structure
        social_structure = core_worldview.get("social_structure", "")
        if social_structure:
            if len(social_structure) > 300:
                social_structure = social_structure[:300] + "..."
            parts.append(f"- **社会结构**: {social_structure}")

        # 兼容旧字段：world_type, cultivation_system, power_rules, sects_and_factions
        world_type = core_worldview.get("world_type", "")
        if world_type and world_type != era:
            parts.append(f"- **世界类型**: {world_type}")

        cultivation_system = core_worldview.get("cultivation_system", {})
        if cultivation_system:
            if isinstance(cultivation_system, str):
                parts.append(f"- **修炼体系**: {cultivation_system}")
            elif isinstance(cultivation_system, dict):
                system_desc = cultivation_system.get("description", "")
                if system_desc:
                    parts.append(f"- **修炼体系**: {system_desc}")

        power_rules = core_worldview.get("power_rules", "")
        if power_rules and power_rules not in social_structure:
            rules_str = power_rules if isinstance(power_rules, str) else str(power_rules)
            parts.append(f"- **力量规则**: {rules_str[:200]}")

        # 门派势力
        sects = core_worldview.get("sects_and_factions", {})
        if sects and isinstance(sects, dict):
            major_sects = sects.get("major_sects", [])
            if major_sects:
                parts.append("- **主要势力**:")
                for sect in major_sects[:5]:
                    sect_name = sect.get("name", "未命名") if isinstance(sect, dict) else str(sect)
                    parts.append(f"  - {sect_name}")

        return "\n".join(parts)

    def build_major_event_context(self, major_event: Dict) -> str:
        """构建重大事件完整信息上下文"""
        if not major_event:
            return ""

        parts = ["## 所属重大事件（完整信息）"]

        parts.append(f"- **重大事件名称**: {major_event.get('name', '未命名')}")
        parts.append(f"- **章节范围**: {major_event.get('chapter_range', '未知')}")
        parts.append(f"- **核心目标**: {major_event.get('main_goal', '未设定')}")
        parts.append(f"- **在阶段中的作用**: {major_event.get('role_in_stage_arc', '未定义')}")

        # 事件概要（如果有）
        overview = major_event.get("overview", "")
        if overview:
            parts.append(f"- **事件概要**: {overview}")

        # 起承转合结构（如果有）
        structure = major_event.get("structure", {})
        if structure:
            parts.append("- **事件结构**:")
            for phase, content in list(structure.items())[:4]:  # 限制数量
                if isinstance(content, str):
                    parts.append(f"  - {phase}: {content}")
                elif isinstance(content, dict):
                    desc = content.get("description", "")
                    if desc:
                        parts.append(f"  - {phase}: {desc}")

        return "\n".join(parts)

    def build_stage_context(self, stage_name: str, medium_event: Dict, novel_data: Dict) -> str:
        """构建阶段上下文"""
        overall_stage_plan = novel_data.get("overall_stage_plans", {})
        stage_plan = overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {})

        if not stage_plan:
            return ""

        parts = ["## 当前阶段目标（最高层级指导）"]
        parts.append(f"- **阶段名称**: {stage_name}")
        parts.append(f"- **阶段核心目标**: {stage_plan.get('stage_goal', '推进主线发展')}")
        parts.append(f"- **阶段范围**: {stage_plan.get('chapter_range', '未知')}")
        parts.append(f"- **本事件对阶段的贡献**: {medium_event.get('contribution_to_major', '服务于阶段目标')}")

        return "\n".join(parts)


# 全局单例
_context_builder_instance = None

def get_scene_context_builder() -> SceneContextBuilder:
    """获取场景上下文构建器实例（单例模式）"""
    global _context_builder_instance
    if _context_builder_instance is None:
        _context_builder_instance = SceneContextBuilder()
    return _context_builder_instance
