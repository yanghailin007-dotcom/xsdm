"""
EmotionalStructureSession - 情绪与结构规划会话（Session C）
=========================================================

职责：
- 生成爽文专用的情绪蓝图与成长规划
- 生成全书阶段计划（爽点单元制）

对话轮次：2轮
1. 基于 CharacterNarrativeSession 的 Context Brief 和已有数据，
   生成/验证情绪蓝图与成长规划（爽文专用格式）
2. 基于第1轮输出，生成爽点单元制的全书阶段计划

修复问题：
- 替代 PhaseGenerator._generate_emotional_and_growth_plan 的单次调用孤岛
- 替代 StagePlanManager.generate_overall_stage_plan 的单次调用孤岛
- 两轮对话在同一个会话中，上下文连贯
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from src.core.session_mode.novel_generation_session import NovelGenerationSession
from src.utils.logger import get_logger

logger = get_logger("EmotionalStructureSession")


class EmotionalStructureSession(NovelGenerationSession):
    """
    情绪与结构规划会话
    
    合并原步骤8-9（emotional_blueprint + global_growth_plan）和步骤10（stage_plan）
    在同一个对话会话中完成，替代原有的单次调用孤岛
    """
    
    STEPS = ["emotional_growth_planning", "stage_plan"]
    
    def __init__(
        self,
        api_client,
        novel_data: Optional[Dict] = None,
        context_briefs: Optional[List[str]] = None,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        # Session C 接收 CharacterNarrativeSession 的 Context Brief
        super().__init__(
            api_client=api_client,
            domain="structure",
            context_briefs=context_briefs or [],
            novel_data=novel_data,
            provider=provider,
            model_name=model_name,
            temperature=temperature,
        )
        
        # 存储每轮结果
        self.results: Dict[str, Any] = {}
        
        # 进度回调
        self._progress_callback: Optional[Callable[[int, str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """设置进度回调"""
        self._progress_callback = callback
    
    def _update_progress(self, progress: int, message: str):
        """更新进度"""
        if self._progress_callback:
            self._progress_callback(progress, message)
        logger.info(f"[EmotionalStructure] 进度 {progress}%: {message}")
    
    # =====================================================================
    # 主执行流程
    # =====================================================================
    
    def execute_all_steps(self) -> Dict[str, Any]:
        """
        执行全部2轮对话
        
        🔥 基于 CharacterNarrativeSession 的 Context Brief 和 novel_data 中已有数据
        
        Returns:
            完整产物字典，包含 emotional_blueprint, global_growth_plan, overall_stage_plans
        """
        logger.info("=" * 60)
        logger.info("EmotionalStructureSession 开始执行")
        logger.info("基于角色叙事会话的上下文，生成情绪蓝图、成长规划和阶段计划...")
        logger.info("=" * 60)
        
        # 获取已有数据（可能来自 CharacterNarrativeSession 或传统模式）
        existing_emotional = self.novel_data.get("emotional_blueprint", {})
        existing_growth = self.novel_data.get("global_growth_plan", {})
        
        # 获取 CharacterNarrative 的 Context Brief
        character_brief = {}
        if self.context_briefs:
            try:
                character_brief = json.loads(self.context_briefs[0]) if isinstance(self.context_briefs[0], str) else self.context_briefs[0]
            except:
                logger.warning("无法解析 CharacterNarrativeSession 的 Context Brief")
        
        try:
            # 第1轮：情绪蓝图 + 成长规划（爽文专用格式）
            self._update_progress(20, "生成爽文情绪蓝图与成长规划...")
            step1_result = self._round1_emotional_and_growth(
                character_brief, existing_emotional, existing_growth
            )
            self.results["emotional_blueprint"] = step1_result.get("emotional_blueprint", {})
            self.results["global_growth_plan"] = step1_result.get("global_growth_plan", {})
            
            # 第2轮：全书阶段计划（爽点单元制）
            self._update_progress(60, "生成爽点单元制阶段计划...")
            step2_result = self._round2_stage_plan(
                step1_result.get("emotional_blueprint", {}),
                step1_result.get("global_growth_plan", {}),
                character_brief
            )
            self.results["overall_stage_plans"] = step2_result
            
            # 验证产物格式
            self._update_progress(95, "验证产物格式...")
            if not self._validate_output(self.results):
                logger.error("产物格式验证失败")
                raise ValueError("产物格式不符合要求")
            
            self._update_progress(100, "情绪与结构规划完成")
            
            logger.info("✅ EmotionalStructureSession 执行完成")
            return self.results
            
        except Exception as e:
            logger.error(f"❌ EmotionalStructureSession 执行失败: {e}", exc_info=True)
            raise
    
    # =====================================================================
    # 各轮对话实现
    # =====================================================================
    
    def _round1_emotional_and_growth(
        self, 
        character_brief: Dict,
        existing_emotional: Dict,
        existing_growth: Dict
    ) -> Dict:
        """
        第1轮：生成爽文专用的情绪蓝图与成长规划
        
        如果已有数据（来自 CharacterNarrativeSession），则基于已有数据补充爽文专用字段
        """
        # 基础信息
        novel_title = self.novel_data.get("novel_title", "未命名")
        novel_synopsis = self.novel_data.get("novel_synopsis", "")
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 1000)
        
        # 从 character_brief 提取关键信息
        protagonist_name = character_brief.get("protagonist_profile", {}).get("name", "主角")
        protagonist_traits = character_brief.get("protagonist_profile", {}).get("core_traits", [])
        growth_milestones = character_brief.get("growth_milestones", [])
        emotional_arc = character_brief.get("emotional_arc", [])
        
        # 判断是否需要完全重新生成
        has_existing = bool(existing_emotional and existing_growth)
        
        if has_existing:
            mode_instruction = """已有基础数据，你的任务是：
1. 将已有数据转换为【爽文专用格式】（补充爽点密度、压抑-爆发配对、黄金三章等字段）
2. 检查并修复已有数据中的不一致
3. 确保情绪蓝图和成长规划相互协调"""
            existing_data_section = f"""
**已有的情绪蓝图（来自角色叙事会话）**
{json.dumps(existing_emotional, ensure_ascii=False, indent=2)}

**已有的成长规划（来自角色叙事会话）**
{json.dumps(existing_growth, ensure_ascii=False, indent=2)}"""
        else:
            mode_instruction = """从头生成完整的情绪蓝图和成长规划。"""
            existing_data_section = "（无已有数据，需要从头生成）"
        
        user_prompt = f"""# 角色：顶级爽文情绪架构专家

你的任务是为小说设计【爽文专用的情绪蓝图与成长规划】。{mode_instruction}

# 小说核心信息
*   **书名**: {novel_title}
*   **简介**: {novel_synopsis}
*   **总章节数**: {total_chapters}

# 角色信息（来自角色叙事会话）
*   **主角**: {protagonist_name}
*   **性格标签**: {', '.join(protagonist_traits) if protagonist_traits else '未指定'}
*   **成长里程碑**: {', '.join(growth_milestones[:3]) if growth_milestones else '未指定'}
*   **情绪弧线**: {json.dumps(emotional_arc, ensure_ascii=False) if emotional_arc else '未指定'}

{existing_data_section}

# 第一部分：爽点情绪蓝图设计

## 任务
设计全书的爽点情绪节奏图，核心目标：**让读者持续产生爽感，欲罢不能**。

## 输出要求（爽文专用格式）
1. **爽感情感光谱**: 提炼3-5个核心爽感关键词（如：装逼快感、打脸宣泄、收获满足、逆袭狂喜、护短温暖）
2. **爽点节奏图**（不是传统的起承转合，而是爽点循环）：
   - opening_stage(黄金开局): 快速建立代入感 → 首次小爽点 → 强悬念钩子
   - development_stage(爽点展开): 压抑→爆发→收获的波浪节奏，每2-4章一个小爽点
   - climax_stage(高潮碾压): 层层升级的爽点爆发，从个人打脸到势力碾压
   - ending_stage(终局收束): 最终大爽点 + 圆满或新期待
3. **爽点爆发节点**: 明确标记全书的爽点位置、类型和强度
4. **压抑设计**: 为每个大爽点设计前置的压抑铺垫

# 第二部分：爽感成长规划

## 任务
设计主角的成长路线，确保每次成长都对应一个爽点爆发。

## 输出要求（爽文专用格式）
1. **能力跃迁路线**: 每次能力提升对应什么爽点
2. **打脸升级路线**: 从被轻视到震惊众人的阶段性设计
3. **收获认可路线**: 从默默无闻到各方势力争抢的成长路径
4. **境界/资源体系**: 如果是修仙/系统流，设计配套的升级体系

## 输出格式（JSON）
{{
    "emotional_blueprint": {{
        "爽感光谱": ["关键词1", "关键词2", "关键词3"],
        "stage_emotional_arcs": {{
            "opening_stage": {{"emotional_tone": "情绪基调", "reader_feeling": "读者感受", "爽点密度": "高/中/低", "description": "阶段描述"}},
            "development_stage": {{...}},
            "climax_stage": {{...}},
            "ending_stage": {{...}}
        }},
        "payoff_moments": [
            {{"chapter": "X", "type": "装逼打脸/收获奖励/境界突破/势力碾压", "intensity": 1-10, "description": "爽点描述"}}
        ],
        "suppression_design": [
            {{"chapter": "X", "type": "被轻视/被嘲讽/被陷害", "purpose": "为哪个爽点做铺垫", "duration": "压抑持续章节数"}}
        ],
        "golden_three_chapters": {{
            "chapter1_hook": "第1章钩子设计",
            "chapter2_conflict": "第2章冲突升级",
            "chapter3_payoff": "第3章首次爽点"
        }}
    }},
    "global_growth_plan": {{
        "protagonist_growth": [
            {{"stage": "阶段名", "growth_goal": "成长目标", "ability_progression": "能力提升", "corresponding_payoff": "对应的爽点"}}
        ],
        "milestone_events": [
            {{"chapter_range": "章节范围", "event": "里程碑事件", "significance": "成长意义", "payoff_type": "爽点类型"}}
        ],
        "power_progression": [
            {{"chapter": "章节", "upgrade": "能力提升", "impact": "带来的影响", "payoff_chapter": "对应的爽点章节"}}
        ],
        "face_slap_stages": [
            {{"stage": "阶段", "from_status": "被轻视的状态", "to_status": "震惊众人的状态", "method": "打脸方式"}}
        ],
        "realm_system": {{
            "name": "境界体系名称（如有）",
            "overview": "体系概述",
            "realms": [
                {{"name": "境界名称", "description": "境界描述 + 该境界能打出什么爽点"}}
            ]
        }}
    }}
}}

## 爽文设计铁律
1. 确保两个部分相互协调，每次成长高潮后必须有对应的爽点章节
2. 情绪蓝图中必须有明确的「压抑→爆发」配对设计
3. 成长规划中每次能力升级后，必须标注「这个能力能打出什么爽点"
4. 黄金三章必须在 opening_stage 中明确设计"""
        
        logger.info("[Round 1] 生成爽文情绪蓝图与成长规划")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round1_emotional_and_growth"
        )
        
        if not result:
            raise RuntimeError("第1轮对话失败：无法生成情绪蓝图与成长规划")
        
        return result
    
    def _round2_stage_plan(
        self,
        emotional_blueprint: Dict,
        global_growth_plan: Dict,
        character_brief: Dict
    ) -> Dict:
        """
        第2轮：生成全书阶段计划（爽点单元制）
        
        基于第1轮的情绪蓝图和成长规划，在同一个会话中生成阶段计划
        """
        novel_title = self.novel_data.get("novel_title", "未命名")
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 1000)
        
        # 提取成长阶段数量用于建议阶段数
        growth_stages = global_growth_plan.get('protagonist_growth', [])
        milestones = global_growth_plan.get('milestone_events', [])
        
        # 计算建议阶段数
        if total_chapters >= 400:
            suggest_min = total_chapters // 5
            suggest_max = total_chapters // 3
        elif total_chapters >= 300:
            suggest_min = total_chapters // 5
            suggest_max = total_chapters // 4
        else:
            suggest_min = total_chapters // 6
            suggest_max = total_chapters // 4
        
        # 提取爽点信息
        payoff_moments = emotional_blueprint.get("payoff_moments", [])
        suppression_design = emotional_blueprint.get("suppression_design", [])
        
        user_prompt = f"""基于上一轮的情绪蓝图和成长规划，现在生成全书的阶段计划。

# 上一轮输出摘要

## 爽点情绪蓝图
- 爽感光谱：{', '.join(emotional_blueprint.get('爽感光谱', []))}
- 黄金三章：{json.dumps(emotional_blueprint.get('golden_three_chapters', {}), ensure_ascii=False)}
- 关键爽点：{len(payoff_moments)}个
- 压抑设计：{len(suppression_design)}个

## 成长规划
- 成长阶段：{len(growth_stages)}个
- 里程碑事件：{len(milestones)}个

# 阶段计划任务

将全书划分为【爽点单元】，每个单元围绕一个核心爽点设计：

## 阶段设计要求
1. **阶段数量**: 建议 {max(3, len(growth_stages))}-{min(6, len(growth_stages)+2)} 个阶段（基于 {total_chapters} 章）
2. **每个阶段必须包含**:
   - 阶段名称（爽点导向，如"觉醒打脸篇""势力崛起篇"）
   - 章节范围
   - 核心爽点（该阶段最大的爽点是什么）
   - 压抑铺垫（为该爽点做了什么前置压抑）
   - 成长跃迁（主角在该阶段的能力/地位变化）
   - 关键事件（3-5个推动剧情的事件）
3. **阶段间关系**: 爽点强度逐层升级，不能倒退

## 输出格式（JSON）
{{
    "overall_stage_plan": {{
        "opening_stage": {{
            "stage_name": "阶段名（爽点导向）",
            "chapter_range": "1-XX",
            "chapter_count": XX,
            "core_payoff": "该阶段核心爽点",
            "suppression_setup": "压抑铺垫",
            "growth_jump": "成长跃迁",
            "key_events": ["事件1", "事件2", "事件3"],
            "emotional_focus": "情绪焦点",
            "climax": "阶段高潮",
            "next_stage_hook": "下一阶段钩子"
        }},
        "development_stage": {{...}},
        "climax_stage": {{...}},
        "ending_stage": {{...}}
    }},
    "stage_flow": [
        {{"from": "阶段A", "to": "阶段B", "transition": "如何过渡", "escalation": "爽点如何升级"}}
    ],
    "overall_payoff_arc": "全书爽点升级弧线描述"
}}

注意：
- 保留 opening_stage/development_stage/climax_stage/ending_stage 的键名以兼容下游系统
- 但内容使用爽点单元制而非起承转合
- 确保每个阶段都有明确的爽点爆发和压抑铺垫"""
        
        logger.info("[Round 2] 生成爽点单元制阶段计划")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round2_stage_plan"
        )
        
        if not result:
            raise RuntimeError("第2轮对话失败：无法生成阶段计划")
        
        return result
    
    # =====================================================================
    # 验证与导出
    # =====================================================================
    
    def _validate_output(self, output: Dict) -> bool:
        """验证产物格式"""
        emotional = output.get("emotional_blueprint", {})
        growth = output.get("global_growth_plan", {})
        stage_plans = output.get("overall_stage_plans", {})
        
        # 基本检查
        checks = [
            (bool(emotional), "情绪蓝图缺失"),
            (bool(growth), "成长规划缺失"),
            (bool(stage_plans), "阶段计划缺失"),
            ("overall_stage_plan" in stage_plans or any(k in stage_plans for k in ["opening_stage", "development_stage", "climax_stage", "ending_stage"]), "阶段计划格式不正确"),
        ]
        
        all_valid = True
        for check, msg in checks:
            if not check:
                logger.error(f"[EmotionalStructureSession] 验证失败: {msg}")
                all_valid = False
        
        return all_valid
    
    def export_results(self) -> Dict[str, Any]:
        """
        导出结果（兼容传统格式）
        """
        return {
            "emotional_blueprint": self.results.get("emotional_blueprint", {}),
            "global_growth_plan": self.results.get("global_growth_plan", {}),
            "overall_stage_plans": self.results.get("overall_stage_plans", {}),
        }
    
    def export_context_brief(self) -> Dict[str, Any]:
        """
        导出 Context Brief 传递给下游会话
        """
        emotional = self.results.get("emotional_blueprint", {})
        growth = self.results.get("global_growth_plan", {})
        stage_plans = self.results.get("overall_stage_plans", {})
        
        # 提取阶段概览
        stage_overview = {}
        if "overall_stage_plan" in stage_plans:
            for key, stage in stage_plans["overall_stage_plan"].items():
                stage_overview[key] = {
                    "name": stage.get("stage_name", ""),
                    "chapter_range": stage.get("chapter_range", ""),
                    "core_payoff": stage.get("core_payoff", ""),
                }
        
        return {
            "emotional_spectrum": emotional.get("爽感光谱", []),
            "key_payoff_moments": [
                {"chapter": p.get("chapter"), "type": p.get("type"), "intensity": p.get("intensity")}
                for p in emotional.get("payoff_moments", [])[:5]  # 只取前5个
            ],
            "golden_three_chapters": emotional.get("golden_three_chapters", {}),
            "growth_milestones": [
                m.get("event", "") for m in growth.get("milestone_events", [])[:5]
            ],
            "stage_overview": stage_overview,
            "generation_timestamp": datetime.now().isoformat(),
            "session_type": "EmotionalStructureSession"
        }
