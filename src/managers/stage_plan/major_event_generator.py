"""
重大事件生成器 - 负责生成阶段的主龙骨（重大事件骨架）
"""
import json
from typing import Dict, List
from src.utils.logger import get_logger


class MajorEventGenerator:
    """重大事件生成器 - 生成阶段的重大事件框架"""
    
    def __init__(self, api_client, logger_name: str = "MajorEventGenerator"):
        self.api_client = api_client
        self.logger = get_logger(logger_name)
    
    def generate_major_event_skeletons(self, stage_name: str, stage_range: str,
                                      creative_seed: Dict, global_novel_data: Dict,
                                      stage_emotional_plan: Dict, overall_stage_plan: Dict,
                                      density_requirements: Dict, novel_title: str) -> List[Dict]:
        """
        生成重大事件骨架（主龙骨）
        
        Args:
            stage_name: 阶段名称
            stage_range: 阶段章节范围
            creative_seed: 创意种子
            global_novel_data: 全局小说数据
            stage_emotional_plan: 阶段情绪计划
            overall_stage_plan: 整体阶段计划
            density_requirements: 密度要求
            novel_title: 小说标题
            
        Returns:
            重大事件骨架列表
        """
        self.logger.info(f"    -> 正在为【{stage_name}】构建主龙骨，开始注入顶层设计上下文...")
        
        try:
            # 构建上下文注入区块
            context_injection_block = self._build_context_injection(
                creative_seed, global_novel_data, overall_stage_plan, stage_name
            )
        except Exception as e:
            self.logger.error(f"    ❌ 构建上下文注入区块失败: {e}")
            return []
        
        # 构建prompt
        prompt_header = f"""
任务：基于顶层设计，为【{stage_name}】阶段编排"主龙骨"
作为顶级AI剧情架构师，你的任务是严格遵循下方提供的三份核心设计文档，为小说的【{stage_name}】({stage_range})规划出宏观的"主龙骨"（重大事件列表）。

【绝对核心参考资料 (必须严格遵守)】
{context_injection_block}
"""
        
        # 根据阶段选择不同的设计要求
        if stage_name == "opening_stage":
            design_requirements = self._get_opening_stage_requirements(density_requirements)
            json_format_example = self._get_opening_stage_format_example(stage_emotional_plan)
        else:
            design_requirements = self._get_standard_stage_requirements(stage_name, density_requirements)
            json_format_example = self._get_standard_format_example(stage_emotional_plan)
        
        # 组合最终prompt
        user_prompts = prompt_header + design_requirements + json_format_example
        
        try:
            result = self.api_client.generate_content_with_retry(
                content_type="stage_major_event_skeleton",
                user_prompt=user_prompts,
                purpose=f"【顶层设计注入】生成 {novel_title} 的【{stage_name}】主龙骨"
            )
            
            # 🔥 增强错误诊断
            if not result:
                self.logger.error(f"    ❌ 生成主龙骨失败：API返回为空")
                return []
            
            if not isinstance(result, dict):
                self.logger.error(f"    ❌ 生成主龙骨失败：返回类型不正确，期望dict，实际为{type(result)}")
                return []
            
            if "major_event_skeletons" not in result:
                self.logger.error(f"    ❌ 生成主龙骨失败：缺少'major_event_skeletons'字段")
                self.logger.error(f"    实际返回的字段: {list(result.keys())}")
                return []
            
            return result["major_event_skeletons"]
                
        except Exception as e:
            self.logger.error(f"    ❌ 调用API生成主龙骨时出错: {e}")
            return []
    
    def _build_context_injection(self, creative_seed: Dict, global_novel_data: Dict,
                                 overall_stage_plan: Dict, stage_name: str) -> str:
        """构建上下文注入区块"""
        try:
            # 1. 注入创意种子
            creative_seed_str = json.dumps(creative_seed, ensure_ascii=False, indent=2)
            
            # 2. 注入全书成长规划
            global_growth_plan = global_novel_data.get("global_growth_plan", {})
            if not global_growth_plan:
                self.logger.warning("    ⚠️ 警告：无法从 novel_data 中获取'global_growth_plan'。")
            global_growth_plan_str = json.dumps(global_growth_plan, ensure_ascii=False, indent=2)
            
            # 3. 注入整体阶段计划
            overall_stage_plan_str = json.dumps(overall_stage_plan, ensure_ascii=False, indent=2)
            
            return f"""
# 1. 最高指令：核心创意种子 (Creative Seed)
你的一切创作都必须是这份文档的具象化。如果其他资料与此冲突，以此为准。
```json
{creative_seed_str}
```

# 2. 战略蓝图：全书成长规划 (Global Growth Plan)
这份规划定义了主角和故事在每个阶段的成长目标和里程碑。你设计的事件必须服务于这些目标。
```json
{global_growth_plan_str}
```

# 3. 战术地图：整体阶段计划 (Overall Stage Plans)
这份计划将全书划分了"起承转合"，明确了各阶段的核心任务。当前正处于【{stage_name}】。
```json
{overall_stage_plan_str}
```
"""
        except Exception as e:
            self.logger.error(f"    ❌ 构建上下文注入区块失败: {e}")
            return "# 上下文注入失败\n简化版上下文"
    
    def _get_opening_stage_requirements(self, density_requirements: Dict) -> str:
        """获取开局阶段的设计要求"""
        return f"""
【opening_stage】设计要求
1.  **忠于蓝图**: 你设计的 {density_requirements['major_events']} 个重大事件，必须共同构成一个服务于核心参考资料中【opening_stage】阶段目标的"起、承、转、合"叙事链条。
2.  **【强制】黄金开局改编**: 第一个重大事件必须被设计为一个特殊的【黄金开局弧光】，后续流程将强制使用它来**精准演绎**`creative_seed.completeStoryline.opening`中的开篇情节。
3.  **后续衔接**: 剩余的重大事件，则用于完成`global_growth_plan`和`creative_seed`中为本阶段设定的其他目标。
"""
    
    def _get_opening_stage_format_example(self, stage_emotional_plan: Dict) -> str:
        """获取开局阶段的格式示例"""
        return """
## 输出格式: 严格返回一个JSON对象，其中包含一个键名为`major_event_skeletons`的列表。

【🔥 开局阶段章节划分铁律 - 必须遵守】
1. **第1-3章必须作为一个完整的重大事件（黄金开局弧光）**
   - 章节范围固定为: "1-3"
   - is_golden_arc: true
   - 这是不可拆分的叙事整体

2. **第4章及以后的事件从第4章开始计算**
   - 第二个事件章节范围示例: "4-15" 或 "4-8" 等
   - 严禁与第1-3章重叠

3. **章节编号必须连续**
   - 第一个事件结束于第3章
   - 第二个事件必须从第4章开始

正确示例:
{
    "major_event_skeletons": [
        {
            "name": "黄金开局弧光",
            "is_golden_arc": true,
            "role_in_stage_arc": "起 (引爆器)",
            "chapter_range": "1-3",
            "main_goal": "此事件为特殊容器，后续流程必须【精准演绎】核心创意种子中的开篇商业设计。涵盖：诡异降临→模拟器初现→初步破局。",
            "emotional_arc": "高能开局，极速入戏",
            "description": "这是决定小说生死的黄金三章（第1-3章），必须100%忠于创意种子中的商业化设计。必须作为一个完整的叙事单元，不可拆分。"
        },
        {
            "name": "后续重大事件名称",
            "is_golden_arc": false,
            "role_in_stage_arc": "承",
            "chapter_range": "4-15",
            "main_goal": "开始应对黄金开局结尾留下的短期危机，推进核心参考资料中的情节",
            "emotional_arc": "发展与探索",
            "description": "承接黄金三章的结尾，展开后续剧情发展"
        }
    ]
}

【错误示例 - 严禁】
❌ 不要将第1-3章拆分为多个事件:
   - 错误: 事件1(1-2章) + 事件2(3章) + 事件3(4-5章)
   - 正确: 事件1(1-3章整体) + 事件2(4-15章)
"""
    
    def _get_standard_stage_requirements(self, stage_name: str, density_requirements: Dict) -> str:
        """获取标准阶段的设计要求"""
        return f"""
【{stage_name}】设计要求
1.  **忠于蓝图**: 你的任务是演绎和编排，不是原创。你设计的 {density_requirements['major_events']} 个重大事件，必须共同构成一个服务于核心参考资料中【{stage_name}】阶段目标的"起、承、转、合"叙事链条。
2.  **目标对齐**: 确保每个重大事件的`main_goal`都直接对应`global_growth_plan`和`creative_seed`中为本阶段设定的某个核心目标。
3.  **承上启下**: 第一个事件要承接上一阶段的结尾，最后一个事件要为下一阶段埋下伏笔。
"""
    
    def _get_standard_format_example(self, stage_emotional_plan: Dict) -> str:
        """获取标准阶段的格式示例"""
        emotional_arc = stage_emotional_plan.get('main_emotional_arc', 'N/A')
        return f"""
## 输出格式: 严格返回一个JSON对象，其中包含一个键名为`major_event_skeletons`的列表。
{{
    "major_event_skeletons": [
        {{
            "name": "第一个重大事件的名称",
            "role_in_stage_arc": "起",
            "chapter_range": "31-50",
            "main_goal": "这个重大事件的核心目标",
            "emotional_arc": "{emotional_arc}",
            "description": "对该事件的简要描述，体现其在蓝图中的作用"
        }},
        {{
            "name": "第二个重大事件的名称",
            "role_in_stage_arc": "承",
            "chapter_range": "51-70",
            "main_goal": "此事件的核心目标",
            "emotional_arc": "探索与成长",
            "description": "描述此事件如何发展'起'事件留下的线索"
        }}
    ]
}}
"""

    def generate_all_stages_skeletons_batch(self, stages_config: List[Dict],
                                           creative_seed: Dict, global_novel_data: Dict,
                                           overall_stage_plan: Dict, novel_title: str) -> Dict[str, List[Dict]]:
        """
        🚀 批量生成所有阶段的主龙骨 - 将多次API调用合并为一次
        
        Args:
            stages_config: 阶段配置列表，每个包含 stage_name, stage_range, density_requirements, stage_emotional_plan
            creative_seed: 创意种子
            global_novel_data: 全局小说数据
            overall_stage_plan: 整体阶段计划
            novel_title: 小说标题
            
        Returns:
            Dict[str, List[Dict]]: {stage_name: [major_event_skeletons]}
        """
        self.logger.info(f"    🚀 批量生成 {len(stages_config)} 个阶段的主龙骨...")
        
        try:
            # 构建上下文注入
            context_injection_block = self._build_context_injection(
                creative_seed, global_novel_data, overall_stage_plan, "全书四大阶段"
            )
        except Exception as e:
            self.logger.error(f"    ❌ 构建上下文注入区块失败: {e}")
            return {}
        
        # 构建所有阶段的设计要求
        stages_design_requirements = []
        for i, stage_config in enumerate(stages_config):
            stage_name = stage_config['stage_name']
            stage_range = stage_config['stage_range']
            density = stage_config['density_requirements']
            
            if stage_name == "opening_stage":
                req = self._get_opening_stage_requirements(density)
            else:
                req = self._get_standard_stage_requirements(stage_name, density)
            
            stages_design_requirements.append(f"""
## 阶段 {i+1}: {stage_name} ({stage_range})
{req}
""")
        
        # 组合批量生成的提示词
        user_prompts = f"""
任务：基于顶层设计，为小说的四个阶段批量生成"主龙骨"
作为顶级AI剧情架构师，你的任务是严格遵循下方提供的三份核心设计文档，为小说的四大阶段（起、承、转、合）批量生成宏观的"主龙骨"。

【绝对核心参考资料 (必须严格遵守)】
{context_injection_block}

【各阶段设计要求】
{chr(10).join(stages_design_requirements)}

【批量输出格式 - 必须严格遵守】
你必须返回一个JSON对象，且必须包含以下顶层字段：
{{
    "all_stages_skeletons": {{
        "opening_stage": [
            {{
                "name": "重大事件名称",
                "role_in_stage_arc": "起/承/转/合",
                "chapter_range": "章节范围",
                "main_goal": "核心目标",
                "emotional_arc": "情感弧光",
                "description": "描述"
            }}
        ],
        "development_stage": [...],
        "climax_stage": [...],
        "ending_stage": [...]
    }}
}}

【严格约束 - 违者解析失败】
1. 根级别只能有且仅有 "all_stages_skeletons" 一个字段
2. 禁止返回 "decomposed_events"、"batch_coherence_analysis" 等其他字段名
3. "all_stages_skeletons" 内部必须包含 "opening_stage"、"development_stage"、"climax_stage"、"ending_stage" 四个键
4. 每个阶段对应一个事件对象数组
5. opening_stage 的第一个事件必须是【黄金开局弧光】，is_golden_arc: true
6. 确保四个阶段的事件链条连贯、层层递进
7. 前一阶段的结尾要为下一阶段埋下伏笔
"""
        
        try:
            result = self.api_client.generate_content_with_retry(
                content_type="batch_major_event_decomposition",
                user_prompt=user_prompts,
                purpose=f"【批量顶层设计注入】一次性生成 {novel_title} 四大阶段主龙骨"
            )
            
            # 🔥 增强错误诊断
            if not result:
                self.logger.error(f"    ❌ 批量生成主龙骨失败：API返回为空")
                return {}
            
            if not isinstance(result, dict):
                self.logger.error(f"    ❌ 批量生成主龙骨失败：返回类型不正确，期望dict，实际为{type(result)}")
                self.logger.debug(f"    返回内容: {str(result)[:500]}")
                return {}
            
            # 🔥 智能修复：尝试处理AI可能返回的错误字段名
            if "all_stages_skeletons" not in result:
                # 情况1：AI可能返回了 "decomposed_events" 字段
                if "decomposed_events" in result:
                    self.logger.warning(f"    🔧 AI返回了 'decomposed_events'，尝试转换为 'all_stages_skeletons'")
                    decomposed = result["decomposed_events"]
                    if isinstance(decomposed, dict) and len(decomposed) > 0:
                        result["all_stages_skeletons"] = decomposed
                    elif isinstance(decomposed, list):
                        # 如果是列表，包装为 opening_stage
                        result["all_stages_skeletons"] = {"opening_stage": decomposed}
                    else:
                        self.logger.error(f"    ❌ 'decomposed_events' 格式不正确，无法转换")
                        return {}
                else:
                    self.logger.error(f"    ❌ 批量生成主龙骨失败：缺少'all_stages_skeletons'字段")
                    self.logger.error(f"    实际返回的字段: {list(result.keys())}")
                    self.logger.debug(f"    返回内容: {json.dumps(result, ensure_ascii=False, indent=2)[:1000]}")
                    return {}
            
            all_skeletons = result["all_stages_skeletons"]
            if not isinstance(all_skeletons, dict):
                self.logger.error(f"    ❌ 批量生成主龙骨失败：'all_stages_skeletons'类型不正确，期望dict，实际为{type(all_skeletons)}")
                return {}
            
            total_events = sum(len(events) for events in all_skeletons.values() if isinstance(events, list))
            self.logger.info(f"    ✅ 批量生成成功: {len(all_skeletons)} 个阶段, {total_events} 个重大事件")
            return all_skeletons
                
        except Exception as e:
            self.logger.error(f"    ❌ 批量生成主龙骨时出错: {e}")
            return {}