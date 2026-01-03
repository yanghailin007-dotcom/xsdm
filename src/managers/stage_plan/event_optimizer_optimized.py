"""
事件优化器 - 优化版，减少API载荷大小
支持智能数据合并，确保不丢失原始字段
"""
import json
from typing import Dict, Any
from copy import deepcopy
from src.utils.logger import get_logger


class EventOptimizerOptimized:
    """事件优化器 - 优化版，减少API载荷，支持智能合并"""
    
    def __init__(self, api_client, logger_name: str = "EventOptimizer"):
        self.api_client = api_client
        self.logger = get_logger(logger_name)
    
    def _compress_event_system(self, event_system: Dict) -> Dict:
        """
        压缩事件系统，只保留优化所需的关键字段
        
        Args:
            event_system: 完整的事件系统
            
        Returns:
            压缩后的事件系统
        """
        compressed = {
            "major_events": []
        }
        
        for major_event in event_system.get("major_events", []):
            compressed_major = {
                "name": major_event.get("name"),
                "chapter_range": major_event.get("chapter_range"),
                "main_goal": major_event.get("main_goal"),
                "role_in_stage_arc": major_event.get("role_in_stage_arc"),
                "composition": {}
            }
            
            # 只保留中型事件的关键信息
            for phase_name, medium_events in major_event.get("composition", {}).items():
                if not isinstance(medium_events, list):
                    continue
                
                compressed_medium = []
                for medium in medium_events:
                    compressed_medium.append({
                        "name": medium.get("name"),
                        "chapter_range": medium.get("chapter_range"),
                        "main_goal": medium.get("main_goal"),
                        # 移除详细描述、场景规划等冗余字段
                    })
                
                compressed_major["composition"][phase_name] = compressed_medium
            
            compressed["major_events"].append(compressed_major)
        
        return compressed
    
    def _merge_optimized_with_original(self, original_event_system: Dict,
                                      optimized_compressed: Dict) -> Dict:
        """
        将AI优化的压缩结果合并回原始完整数据结构
        
        Args:
            original_event_system: 原始完整的事件系统
            optimized_compressed: AI返回的优化后压缩数据
            
        Returns:
            合并后的完整事件系统
        """
        merged = deepcopy(original_event_system)
        optimized_major_events = optimized_compressed.get("major_events", [])
        
        # 构建原始事件的映射表（name -> event）
        original_major_map = {
            event.get("name"): event
            for event in merged.get("major_events", [])
        }
        
        # 遍历优化后的事件，更新原始数据
        for opt_major in optimized_major_events:
            opt_name = opt_major.get("name")
            
            if opt_name not in original_major_map:
                self.logger.warn(f"  ⚠️ 优化结果中找不到事件 '{opt_name}'，跳过")
                continue
            
            orig_major = original_major_map[opt_name]
            
            # 更新关键字段（保留其他字段不变）
            if "main_goal" in opt_major:
                orig_major["main_goal"] = opt_major["main_goal"]
            if "chapter_range" in opt_major:
                orig_major["chapter_range"] = opt_major["chapter_range"]
            
            # 处理 composition（中型事件）
            opt_composition = opt_major.get("composition", {})
            orig_composition = orig_major.get("composition", {})
            
            for phase_name, opt_medium_events in opt_composition.items():
                if phase_name not in orig_composition:
                    orig_composition[phase_name] = []
                    continue
                
                if not isinstance(opt_medium_events, list):
                    continue
                
                # 构建原始中型事件的映射
                orig_medium_map = {
                    event.get("name"): event
                    for event in orig_composition[phase_name]
                }
                
                # 更新中型事件
                for opt_medium in opt_medium_events:
                    opt_medium_name = opt_medium.get("name")
                    
                    if opt_medium_name in orig_medium_map:
                        # 更新关键字段
                        orig_medium = orig_medium_map[opt_medium_name]
                        if "main_goal" in opt_medium:
                            orig_medium["main_goal"] = opt_medium["main_goal"]
                        if "chapter_range" in opt_medium:
                            orig_medium["chapter_range"] = opt_medium["chapter_range"]
                        # 保留其他所有字段（detailed_description, scene_planning等）
                    else:
                        self.logger.warn(f"  ⚠️ 找不到中型事件 '{opt_medium_name}'，跳过")
        
        self.logger.info(f"  ✅ 成功合并优化结果，保留了所有原始字段")
        return merged
    
    def _build_continuity_optimization_prompt_compact(self, event_system: Dict, 
                                                     assessment: Dict, stage_name: str, 
                                                     stage_range: str) -> str:
        """构建连续性优化提示词 - 紧凑版"""
        # 使用压缩后的事件系统
        compressed_system = self._compress_event_system(event_system)
        # 使用紧凑格式（无缩进）
        event_system_str = json.dumps(compressed_system, ensure_ascii=False, separators=(',', ':'))
        
        critical_issues_str = json.dumps(
            assessment.get('critical_issues', [])[:5],  # 只取前5个关键问题
            ensure_ascii=False, 
            separators=(',', ':')
        )
        recommendations_str = json.dumps(
            assessment.get('improvement_recommendations', [])[:5],  # 只取前5个建议
            ensure_ascii=False,
            separators=(',', ':')
        )
        
        prompt = f"""# 任务：小说事件连续性优化 (保持结构)

## 待优化事件 ({stage_name}, {stage_range})
{event_system_str}

## 关键问题
{critical_issues_str}

## 改进建议
{recommendations_str}

## 修复重点
- 逻辑断裂: 修复事件之间的逻辑断层
- 节奏问题: 调整事件密度和分布  
- 情感连续性: 确保情感发展连贯
- 主线推进: 确保主线持续高效推进

【最高优先级】返回与输入结构完全相同的 event_system JSON对象。

## 返回格式
{{"optimized_event_system": {{}},"summary_of_continuity_changes": ""}}
"""
        return prompt
    
    def optimize_based_on_continuity_assessment_compact(self, writing_plan: Dict,
                                                        assessment: Dict, stage_name: str,
                                                        stage_range: str) -> Dict:
        """
        根据连续性评估结果优化写作计划 - 紧凑版（支持智能合并）
        
        Args:
            writing_plan: 写作计划
            assessment: 评估结果
            stage_name: 阶段名称
            stage_range: 阶段范围
            
        Returns:
            优化后的写作计划（保留所有原始字段）
        """
        self.logger.info(f"  🔧 [优化版] 指示AI优化 {stage_name} 阶段事件连续性...")
        
        # 提取当前事件系统
        if "stage_writing_plan" in writing_plan:
            plan_container = writing_plan["stage_writing_plan"]
            event_system = plan_container.get("event_system", {})
        else:
            plan_container = writing_plan
            event_system = writing_plan.get("event_system", {})
        
        # 保存原始完整数据用于合并
        original_event_system = deepcopy(event_system)
        
        # 记录压缩前后的数据量对比
        original_size = len(json.dumps(event_system, ensure_ascii=False))
        compressed_system = self._compress_event_system(event_system)
        compressed_size = len(json.dumps(compressed_system, ensure_ascii=False))
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        self.logger.info(f"  📊 数据压缩: {original_size} → {compressed_size} 字符 (减少 {compression_ratio:.1f}%)")
        
        # 构建紧凑的连续性优化提示词
        optimization_prompt = self._build_continuity_optimization_prompt_compact(
            event_system, assessment, stage_name, stage_range
        )
        
        # 调用AI进行优化
        try:
            optimization_result = self.api_client.generate_content_with_retry(
                content_type="ai_event_plan_optimization",
                user_prompt=optimization_prompt,
                purpose=f"优化{stage_name}阶段事件连续性"
            )
            
            if optimization_result and "optimized_event_system" in optimization_result:
                optimized_compressed = optimization_result["optimized_event_system"]
                
                # 【关键】将AI优化的压缩结果合并回原始完整数据
                merged_event_system = self._merge_optimized_with_original(
                    original_event_system,
                    optimized_compressed
                )
                
                # 更新事件系统（保留所有原始字段）
                plan_container["event_system"] = merged_event_system
                plan_container["continuity_optimized"] = True
                
                # 记录字段保留情况
                merged_size = len(json.dumps(merged_event_system, ensure_ascii=False))
                retention_rate = (merged_size / original_size) * 100
                self.logger.info(f"  ✅ [优化版] AI连续性优化完成")
                self.logger.info(f"  📊 字段保留率: {retention_rate:.1f}% (保留了所有非优化字段)")
                
                summary = optimization_result.get("summary_of_continuity_changes", "AI未提供修改摘要。")
                self.logger.info(f"  📝 修改摘要: {summary}")
            else:
                self.logger.warn("  ⚠️ AI连续性优化失败，未能返回有效的优化后事件系统。")
                
        except Exception as e:
            self.logger.error(f"  ❌ 在执行AI连续性优化时发生错误: {e}")
            import traceback
            self.logger.error(f"  📋 堆栈跟踪: {traceback.format_exc()}")
        
        return writing_plan