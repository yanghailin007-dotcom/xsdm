"""
FoundationPlanningSession - 基础规划会话（Session A）
======================================================

职责：
- 生成写作风格指南
- 生成市场分析
- 构建世界观
- 设计势力系统

对话轮次：4-6轮
1. 分析创意种子，确定写作风格方向
2. 生成详细写作风格指南
3. 市场分析与定位
4. 世界观构建
5. 势力系统设计
6. 整合输出

产物格式（必须与传统模式一致）：
{
    "writing_style_guide": {
        "core_style": str,
        "language_characteristics": List[str],
        "key_principles": List[str],
        "atmosphere": str,  # 可选
        "pacing": str,      # 可选
        "dialogue_style": str  # 可选
    },
    "market_analysis": {
        "target_platform": str,
        "genre_positioning": str,
        "core_selling_points": List[str],
        "target_audience": str,  # 可选
        "competitive_analysis": dict,  # 可选
        "market_potential": str  # 可选
    },
    "core_worldview": {
        "world_overview": str,
        "power_system": str,
        "key_locations": List[str],  # 可选
        "world_rules": List[str],    # 可选
        "historical_background": str  # 可选
    },
    "faction_system": {
        "factions": List[dict],
        "main_conflict": str,
        "faction_power_balance": str,  # 可选
        "recommended_starting_faction": str  # 可选
    }
}
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from src.core.session_mode.novel_generation_session import NovelGenerationSession
from src.utils.logger import get_logger

logger = get_logger("FoundationPlanningSession")


class FoundationPlanningSession(NovelGenerationSession):
    """
    基础规划会话
    
    合并原步骤5-6（foundation_planning + worldview_with_factions）
    """
    
    STEPS = ["foundation_planning", "worldview_with_factions"]
    
    def __init__(
        self,
        api_client,
        novel_data: Optional[Dict] = None,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        # Foundation Session 没有上游 brief
        super().__init__(
            api_client=api_client,
            domain="foundation_planning",
            context_briefs=[],  # Session A 没有上游
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
        logger.info(f"[FoundationPlanning] 进度 {progress}%: {message}")
    
    # =====================================================================
    # 主执行流程
    # =====================================================================
    
    def execute_all_steps(self) -> Dict[str, Any]:
        """
        执行全部4-6轮对话
        
        🔥 基于前面 CreativeToPlanConversation 生成的 final_plan 继续生成
        
        Returns:
            完整产物字典
        """
        logger.info("=" * 60)
        logger.info("FoundationPlanningSession 开始执行")
        logger.info("基于 final_plan 生成基础规划...")
        logger.info("=" * 60)
        
        # 🔥 验证输入：必须存在 final_plan
        final_plan = self.novel_data.get("final_plan") or self.novel_data.get("selected_plan", {})
        if not final_plan:
            raise ValueError("novel_data 中缺少 final_plan 或 selected_plan，" 
                           "请确保 CreativeToPlanConversation 已成功执行")
        
        logger.info(f"输入验证通过：找到 final_plan，书名: {final_plan.get('title', '未命名')}")
        
        try:
            # 第1轮：分析最终方案，确定风格方向
            self._update_progress(10, "分析最终方案，确定写作风格方向...")
            step1_result = self._round1_analyze_final_plan()
            self.results["final_plan_analysis"] = step1_result
            
            # 第2轮：生成写作风格指南
            self._update_progress(25, "生成详细写作风格指南...")
            step2_result = self._round2_generate_writing_style(step1_result)
            self.results["writing_style"] = step2_result
            
            # 第3轮：市场分析
            self._update_progress(40, "进行市场分析与定位...")
            step3_result = self._round3_market_analysis(step1_result)
            self.results["market_analysis"] = step3_result
            
            # 第4轮：世界观构建
            self._update_progress(60, "构建世界观...")
            step4_result = self._round4_worldview_building(step1_result, step2_result)
            self.results["worldview"] = step4_result
            
            # 第5轮：势力系统设计
            self._update_progress(75, "设计势力系统...")
            step5_result = self._round5_faction_system(step4_result)
            self.results["faction_system"] = step5_result
            
            # 第6轮：整合与优化
            self._update_progress(90, "整合所有设定...")
            final_result = self._round6_integrate(
                step2_result, step3_result, step4_result, step5_result
            )
            
            # 验证产物格式
            self._update_progress(95, "验证产物格式...")
            if not self._validate_output(final_result):
                logger.error("产物格式验证失败")
                raise ValueError("产物格式不符合要求")
            
            self._update_progress(100, "基础规划完成")
            
            logger.info("✅ FoundationPlanningSession 执行完成")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ FoundationPlanningSession 执行失败: {e}", exc_info=True)
            raise
    
    # =====================================================================
    # 各轮对话实现
    # =====================================================================
    
    def _round1_analyze_final_plan(self) -> Dict:
        """
        第1轮：分析最终方案
        
        🔥 基于前面 CreativeToPlanConversation 生成的 final_plan
        提取核心卖点、类型特征、目标读者等
        """
        # 🔥 获取最终方案（由 CreativeToPlanConversation 生成）
        final_plan_data = self.novel_data.get("final_plan", {})
        
        # 如果 final_plan 在 nested 结构中，尝试提取
        if not final_plan_data and "final_plan" in self.novel_data.get("selected_plan", {}):
            final_plan_data = self.novel_data["selected_plan"]["final_plan"]
        
        # 兼容处理：如果还是拿不到，降级到 selected_plan
        if not final_plan_data:
            final_plan_data = self.novel_data.get("selected_plan", {})
            self.logger.warning("未找到 final_plan，使用 selected_plan 作为降级")
        
        # 提取关键信息
        title = final_plan_data.get("title") or self.novel_data.get("novel_title", "未命名")
        genre = final_plan_data.get("genre", "未分类")
        core_setting = final_plan_data.get("core_setting", {})
        book_structure = final_plan_data.get("book_structure", {})
        
        # 提取主角和金手指信息
        protagonist = core_setting.get("protagonist", {})
        golden_finger = core_setting.get("golden_finger", {})
        
        user_prompt = f"""请深度分析以下最终方案，提取关键要素用于基础规划：

**最终方案信息**
- 书名：{title}
- 类型：{genre}
- 世界观：{core_setting.get("worldview", "未指定")}
- 力量体系：{core_setting.get("power_system", "未指定")}
- 主角设定：{json.dumps(protagonist, ensure_ascii=False, indent=2)}
- 金手指设定：{json.dumps(golden_finger, ensure_ascii=False, indent=2)}
- 全书结构：{json.dumps(book_structure, ensure_ascii=False, indent=2)}

**分析任务**
1. 提取核心卖点（3-5个，基于 final_plan 的内容提炼）
2. 确定目标读者画像（年龄、性别、阅读偏好）
3. 分析题材特征（节奏、风格、情绪基调，要与 final_plan 匹配）
4. 评估金手指的独特性和可延展性
5. 评估商业化潜力（爆款潜力评分1-10，基于全书结构设计）

**输出格式（JSON）**
{{
    "core_selling_points": ["卖点1", "卖点2", "卖点3"],
    "target_reader": {{
        "age_range": "18-35岁",
        "gender": "男/女/不限",
        "preferences": ["偏好1", "偏好2"]
    }},
    "genre_features": {{
        "pacing": "快节奏/慢热",
        "style": "爽文/正剧/轻松",
        "emotional_tone": "热血/悬疑/甜宠"
    }},
    "golden_finger": {{
        "uniqueness": "独特性描述",
        "scalability": "可延展性描述",
        "limitations": ["限制1", "限制2"]
    }},
    "commercial_potential": {{
        "score": 8,
        "reasoning": "评分理由"
    }}
}}"""
        
        logger.info("[Round 1] 分析创意种子")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round1_creative_analysis"
        )
        
        if not result:
            raise RuntimeError("第1轮对话失败：无法分析创意种子")
        
        return result
    
    def _round2_generate_writing_style(self, round1_result: Dict) -> Dict:
        """
        第2轮：生成写作风格指南
        """
        user_prompt = f"""基于上一轮的创意分析，生成详细的写作风格指南。

**创意分析摘要**
{json.dumps(round1_result, ensure_ascii=False, indent=2)}

**写作风格指南要求**
请制定一份详细的写作风格指南，包含：

1. **核心风格定位**
   - 整体风格描述（2-3句话）
   - 与其他同类作品的差异化

2. **语言特征**
   - 句式特点（长短句比例、节奏感）
   - 用词偏好（华丽/朴实、现代/古风）
   - 对话风格（占比、特点、与叙述的比例）
   - 描写密度（环境/心理/动作）

3. **关键创作原则**
   - 黄金三章的执行策略
   - 爽点分布原则
   - 悬念设置方式
   - 情绪曲线控制

4. **氛围营造**
   - 整体氛围基调
   - 不同场景的氛围变化

5. **节奏控制**
   - 章节内节奏（高潮/缓冲比例）
   - 全书节奏规划（起承转合）

**输出格式（JSON）**
{{
    "core_style": "核心风格描述",
    "language_characteristics": [
        "句式特点：短句为主，节奏明快",
        "用词偏好：朴实有力，避免过度修饰",
        "对话占比：50%以上，推动剧情",
        "描写密度：动作描写为主，心理描写适度"
    ],
    "key_principles": [
        "黄金三章：第一章直接展示金手指，第三章第一个小高潮",
        "爽点分布：每3章至少一个小爽点，每10章一个大爽点",
        "悬念设置：每章结尾留钩子，每阶段埋长线伏笔",
        "情绪曲线：张弛有度，高潮后必有缓冲"
    ],
    "atmosphere": "整体氛围基调描述",
    "pacing": "节奏控制策略描述",
    "dialogue_style": "对话风格特点"
}}"""
        
        logger.info("[Round 2] 生成写作风格指南")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round2_writing_style"
        )
        
        if not result:
            raise RuntimeError("第2轮对话失败：无法生成写作风格指南")
        
        return result
    
    def _round3_market_analysis(self, round1_result: Dict) -> Dict:
        """
        第3轮：市场分析
        """
        category = self.novel_data.get("category", "未分类")
        
        user_prompt = f"""基于创意分析，进行详细的市场分析。

**创意分析摘要**
{json.dumps(round1_result, ensure_ascii=False, indent=2)}

**市场分析任务**
1. **目标平台适配**
   - 番茄小说平台该类型表现
   - 推荐标签组合（3-5个）
   - 最佳发布时间建议

2. **类型定位**
   - 细分类型（如：末世→丧尸末世/异能末世/废土末世）
   - 与平台现有爆款的差异化定位
   - 竞品分析（2-3部相似作品）

3. **核心卖点提炼**
   - 一句话卖点（电梯演讲）
   - 3个核心爽点
   - 3个差异化亮点
   - 情绪价值（读者能获得的情感体验）

4. **目标受众**
   - 核心受众画像
   - 潜在受众扩展
   - 读者痛点与需求

5. **商业化建议**
   - 付费点设计建议
   - 可能的衍生方向
   - IP化潜力评估

**输出格式（JSON）**
{{
    "target_platform": "番茄小说",
    "genre_positioning": "细分类型定位",
    "core_selling_points": [
        "一句话卖点",
        "核心爽点1",
        "核心爽点2",
        "核心爽点3"
    ],
    "differentiation": [
        "差异化亮点1",
        "差异化亮点2",
        "差异化亮点3"
    ],
    "emotional_value": "读者能获得的情感体验",
    "target_audience": "核心受众画像描述",
    "recommended_tags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
    "competitive_analysis": {{
        "similar_works": [
            {{"title": "竞品1", "similarity": "相似点", "difference": "差异点"}}
        ],
        "market_gap": "市场空白点"
    }},
    "commercial_suggestions": {{
        "payment_points": "付费点设计建议",
        "derivation_potential": "衍生方向",
        "ip_potential": "IP化潜力"
    }}
}}"""
        
        logger.info("[Round 3] 市场分析")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round3_market_analysis"
        )
        
        if not result:
            raise RuntimeError("第3轮对话失败：无法生成市场分析")
        
        return result
    
    def _round4_worldview_building(self, round1_result: Dict, round2_result: Dict) -> Dict:
        """
        第4轮：世界观构建
        """
        # 提取金手指信息
        golden_finger = round1_result.get("golden_finger", {})
        
        user_prompt = f"""基于前期分析，构建详细的世界观设定。

**参考信息**
- 风格指南：{round2_result.get('core_style', '未指定')}
- 金手指设定：{json.dumps(golden_finger, ensure_ascii=False)}

**世界观构建任务**
1. **世界概述**
   - 世界基本设定（时代、地域、文明程度）
   - 核心冲突背景
   - 世界运转的基本逻辑

2. **力量体系**
   - 力量来源（金手指如何运作）
   - 力量等级划分（如有）
   - 力量获取方式
   - 力量限制与代价

3. **关键场景**
   - 3-5个关键地点及其特征
   - 场景间的关联
   - 场景对剧情的作用

4. **世界规则**
   - 物理/社会规则（3-5条）
   - 规则对主角的影响
   - 规则的可突破性

5. **历史背景**
   - 简要历史沿革
   - 当前时代特征
   - 可能影响剧情的历史事件

**输出格式（JSON）**
{{
    "world_overview": "世界概述，200-300字",
    "power_system": "力量体系详细描述，300-500字",
    "key_locations": [
        {{"name": "地点1", "description": "描述", "significance": "剧情作用"}},
        {{"name": "地点2", "description": "描述", "significance": "剧情作用"}}
    ],
    "world_rules": [
        "规则1：描述",
        "规则2：描述"
    ],
    "historical_background": "历史背景简述"
}}"""
        
        logger.info("[Round 4] 世界观构建")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round4_worldview"
        )
        
        if not result:
            raise RuntimeError("第4轮对话失败：无法构建世界观")
        
        return result
    
    def _round5_faction_system(self, worldview_result: Dict) -> Dict:
        """
        第5轮：势力系统设计
        """
        world_overview = worldview_result.get("world_overview", "")
        power_system = worldview_result.get("power_system", "")
        
        user_prompt = f"""基于世界观，设计势力系统。

**世界观信息**
- 世界概述：{world_overview}
- 力量体系：{power_system}

**势力系统设计任务**
1. **主要势力**
   设计3-5个主要势力，每个包含：
   - 势力名称
   - 势力定位（正派/反派/中立/灰色）
   - 核心特征（理念、资源、优势）
   - 与主角的关系（初期/中期/后期）

2. **核心冲突**
   - 主要矛盾（势力间/势力与主角）
   - 冲突的层次（表面/深层）
   - 冲突的演变方向

3. **势力平衡**
   - 当前势力格局（谁强谁弱）
   - 势力的动态变化趋势
   - 主角加入后的影响

4. **推荐起始势力**
   - 主角初期最适合加入/接触的势力
   - 理由和预期发展

**输出格式（JSON）**
{{
    "factions": [
        {{
            "name": "势力名称",
            "alignment": "正派/反派/中立/灰色",
            "description": "势力描述",
            "core_values": "核心理念",
            "resources": "掌握的资源",
            "strengths": "优势",
            "relationship_with_protagonist": {{
                "early": "初期关系",
                "mid": "中期关系",
                "late": "后期关系"
            }}
        }}
    ],
    "main_conflict": "核心冲突描述",
    "faction_power_balance": "势力平衡格局",
    "recommended_starting_faction": "推荐起始势力及理由"
}}"""
        
        logger.info("[Round 5] 势力系统设计")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round5_faction_system"
        )
        
        if not result:
            raise RuntimeError("第5轮对话失败：无法设计势力系统")
        
        return result
    
    def _round6_integrate(
        self,
        writing_style: Dict,
        market_analysis: Dict,
        worldview: Dict,
        faction_system: Dict
    ) -> Dict:
        """
        第6轮：整合所有设定，确保一致性
        """
        user_prompt = f"""整合所有设定，生成最终输出格式。

**写作风格指南**
{json.dumps(writing_style, ensure_ascii=False, indent=2)}

**市场分析**
{json.dumps(market_analysis, ensure_ascii=False, indent=2)}

**世界观**
{json.dumps(worldview, ensure_ascii=False, indent=2)}

**势力系统**
{json.dumps(faction_system, ensure_ascii=False, indent=2)}

**整合任务**
1. 检查各模块间的一致性
2. 补充缺失的字段
3. 优化描述，确保专业性和可执行性
4. 生成最终标准格式

**注意**
- 必须严格按照指定的JSON格式输出
- 所有必需字段必须存在
- 可选字段如有相关数据也应包含
- 确保写作风格与世界观、势力系统协调一致

**输出格式（JSON）**
{{
    "writing_style_guide": {{
        "core_style": "核心风格",
        "language_characteristics": ["特征1", "特征2", "特征3"],
        "key_principles": ["原则1", "原则2", "原则3", "原则4"],
        "atmosphere": "氛围基调",
        "pacing": "节奏控制",
        "dialogue_style": "对话风格"
    }},
    "market_analysis": {{
        "target_platform": "番茄小说",
        "genre_positioning": "类型定位",
        "core_selling_points": ["卖点1", "卖点2", "卖点3"],
        "target_audience": "目标受众",
        "competitive_analysis": {{}},
        "market_potential": "市场潜力"
    }},
    "core_worldview": {{
        "world_overview": "世界概述",
        "power_system": "力量体系",
        "key_locations": [{{"name": "", "description": "", "significance": ""}}],
        "world_rules": ["规则1", "规则2"],
        "historical_background": "历史背景"
    }},
    "faction_system": {{
        "factions": [
            {{
                "name": "",
                "alignment": "",
                "description": "",
                "core_values": "",
                "resources": "",
                "strengths": "",
                "relationship_with_protagonist": {{}}
            }}
        ],
        "main_conflict": "核心冲突",
        "faction_power_balance": "势力平衡",
        "recommended_starting_faction": "推荐起始势力"
    }}
}}"""
        
        logger.info("[Round 6] 整合输出")
        result = self.send_structured_message(
            user_prompt=user_prompt,
            purpose="round6_integrate"
        )
        
        if not result:
            raise RuntimeError("第6轮对话失败：无法整合输出")
        
        return result
    
    # =====================================================================
    # 验证与导出
    # =====================================================================
    
    def _validate_output(self, output: Dict) -> bool:
        """验证产物格式"""
        from src.core.session_mode.validators import FoundationPlanningValidator
        
        validator = FoundationPlanningValidator()
        result = validator.validate(output)
        
        if not result.is_valid:
            logger.error(f"产物验证失败:\n{result.get_error_report()}")
        
        return result.is_valid
    
    def export_results(self) -> Dict[str, Any]:
        """
        导出结果（兼容传统格式）
        
        返回与传统模式完全一致的格式
        """
        return self.results.get("final_integrated", {})
    
    def export_context_brief(self) -> Dict[str, Any]:
        """
        导出 Context Brief 传递给 CharacterNarrativeSession
        
        包含核心信息，供下游 Session 使用
        """
        writing_style = self.results.get("writing_style", {})
        market = self.results.get("market_analysis", {})
        worldview = self.results.get("worldview", {})
        factions = self.results.get("faction_system", {})
        
        return {
            "writing_style_summary": {
                "core_style": writing_style.get("core_style", ""),
                "key_principles": writing_style.get("key_principles", [])[:3],  # 只取前3个
                "pacing": writing_style.get("pacing", ""),
            },
            "market_positioning": {
                "genre": market.get("genre_positioning", ""),
                "core_selling_points": market.get("core_selling_points", [])[:3],
                "target_audience": market.get("target_audience", ""),
            },
            "world_overview": worldview.get("world_overview", ""),
            "power_system": worldview.get("power_system", ""),
            "key_locations": [
                loc.get("name", "") 
                for loc in worldview.get("key_locations", [])
            ],
            "world_rules": worldview.get("world_rules", []),
            "main_conflict": factions.get("main_conflict", ""),
            "factions": [
                {
                    "name": f.get("name", ""),
                    "alignment": f.get("alignment", ""),
                    "description": f.get("description", "")[:100],  # 限制长度
                }
                for f in factions.get("factions", [])
            ],
            "recommended_starting_faction": factions.get(
                "recommended_starting_faction", ""
            ),
            "generation_timestamp": datetime.now().isoformat(),
            "session_type": "FoundationPlanningSession"
        }
