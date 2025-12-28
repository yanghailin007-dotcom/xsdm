"""
事件优化器 - 负责优化事件系统的层级和连续性
"""
import json
from typing import Dict
from src.utils.logger import get_logger


class EventOptimizer:
    """事件优化器 - 根据评估结果优化事件系统"""
    
    def __init__(self, api_client, logger_name: str = "EventOptimizer"):
        self.api_client = api_client
        self.logger = get_logger(logger_name)
    
    def optimize_based_on_coherence_assessment(self, writing_plan: Dict, 
                                              assessment: Dict, stage_name: str, 
                                              stage_range: str) -> Dict:
        """
        根据目标层级评估结果优化写作计划
        
        Args:
            writing_plan: 写作计划
            assessment: 评估结果
            stage_name: 阶段名称
            stage_range: 阶段范围
            
        Returns:
            优化后的写作计划
        """
        critical_breakpoints = assessment.get("critical_breakpoints", [])
        improvement_recommendations = assessment.get("improvement_recommendations", [])
        
        if not critical_breakpoints and not improvement_recommendations:
            self.logger.info("  ✅ AI评估未发现严重的目标层级问题，无需优化。")
            return writing_plan
        
        self.logger.info(f"  🔧 指示AI根据目标层级评估，开始优化 {stage_name} 阶段事件目标链...")
        
        # 构建优化指令
        optimization_prompt = self._build_hierarchy_optimization_prompt(
            writing_plan, assessment, stage_name, stage_range
        )
        
        # 调用AI进行优化
        try:
            optimization_result = self.api_client.generate_content_with_retry(
                content_type="ai_hierarchy_optimization",
                user_prompt=optimization_prompt,
                purpose=f"优化{stage_name}阶段事件目标层级"
            )
            
            if optimization_result and "optimized_event_system" in optimization_result:
                # 用AI返回的优化后的事件系统替换旧的
                if "stage_writing_plan" in writing_plan:
                    plan_container = writing_plan["stage_writing_plan"]
                else:
                    plan_container = writing_plan
                
                plan_container["event_system"] = optimization_result["optimized_event_system"]
                plan_container["hierarchy_optimized"] = True
                
                summary = optimization_result.get("summary_of_hierarchy_changes", "AI未提供修改摘要。")
                self.logger.info(f"  ✅ AI目标层级优化执行完成。修改摘要: {summary}")
            else:
                self.logger.warn("  ⚠️ AI目标层级优化失败，未能返回有效的优化后事件系统。")
                
        except Exception as e:
            self.logger.error(f"  ❌ 在执行AI目标层级优化时发生错误: {e}")
        
        return writing_plan
    
    def optimize_based_on_continuity_assessment(self, writing_plan: Dict, 
                                               assessment: Dict, stage_name: str, 
                                               stage_range: str) -> Dict:
        """
        根据连续性评估结果优化写作计划
        
        Args:
            writing_plan: 写作计划
            assessment: 评估结果
            stage_name: 阶段名称
            stage_range: 阶段范围
            
        Returns:
            优化后的写作计划
        """
        self.logger.info(f"  🔧 指示AI根据连续性评估，开始优化 {stage_name} 阶段事件连续性...")
        
        # 提取当前事件系统
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        
        # 构建连续性优化提示词
        optimization_prompt = self._build_continuity_optimization_prompt(
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
                # 用AI返回的优化后的事件系统替换旧的
                if "stage_writing_plan" in writing_plan:
                    plan_container = writing_plan["stage_writing_plan"]
                else:
                    plan_container = writing_plan
                
                plan_container["event_system"] = optimization_result["optimized_event_system"]
                plan_container["continuity_optimized"] = True
                
                summary = optimization_result.get("summary_of_continuity_changes", "AI未提供修改摘要。")
                self.logger.info(f"  ✅ AI连续性优化执行完成。修改摘要: {summary}")
            else:
                self.logger.warn("  ⚠️ AI连续性优化失败，未能返回有效的优化后事件系统。")
                
        except Exception as e:
            self.logger.error(f"  ❌ 在执行AI连续性优化时发生错误: {e}")
        
        return writing_plan
    
    def _build_hierarchy_optimization_prompt(self, writing_plan: Dict, 
                                           assessment: Dict, stage_name: str, 
                                           stage_range: str) -> str:
        """构建目标层级优化提示词"""
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        
        event_system_str = json.dumps(event_system, ensure_ascii=False, indent=2)
        assessment_str = json.dumps(assessment, ensure_ascii=False, indent=2)
        
        prompt = f"""
# 任务：小说事件目标层级优化 (保持结构)
作为顶尖的剧情架构师，你刚刚对一份小说事件计划的目标层级进行了评估，发现了一些目标传递断裂的问题。

## 1. 待优化的事件计划 ({stage_name}, {stage_range})
```json
{event_system_str}
```

## 2. 目标层级评估发现的问题与建议
```json
{assessment_str}
```

## 3. 修复指令
请严格遵循评估建议，对上述的"待优化的事件计划"进行目标层级修复。

修复重点：
- 目标传递断裂: 修复重大事件→中型事件→章节事件→场景事件之间的目标传递断裂
- 贡献关系模糊: 为缺少明确贡献关系的事件添加具体的contribution_to_*字段
- 情绪目标不一致: 确保情绪目标在层级间保持连贯
- 目标过于抽象: 将抽象的目标转化为具体、可执行的目标

【最高优先级指令】保持结构完整性：
你返回的最终结果必须是一个与输入结构完全相同的 event_system JSON对象。

## 4. 返回格式
```json
{{
  "optimized_event_system": {{
    "major_events": [
      {{
        "name": "修复后的重大事件1名称",
        "main_goal": "优化后的核心目标",
        "composition": {{
          "起": [{{"name": "修复后的中型事件", "main_goal": "优化后的目标"}}],
          "承": [],
          "转": [],
          "合": []
        }}
      }}
    ]
  }},
  "summary_of_hierarchy_changes": "一句话总结修改"
}}
```
"""
        return prompt
    
    def _build_continuity_optimization_prompt(self, event_system: Dict, 
                                            assessment: Dict, stage_name: str, 
                                            stage_range: str) -> str:
        """构建连续性优化提示词"""
        critical_issues_str = json.dumps(assessment.get('critical_issues', []), ensure_ascii=False, indent=2)
        recommendations_str = json.dumps(assessment.get('improvement_recommendations', []), ensure_ascii=False, indent=2)
        event_system_str = json.dumps(event_system, ensure_ascii=False, indent=2)
        
        prompt = f"""
# 任务：小说事件连续性优化 (保持结构)
作为顶尖的剧情架构师，你刚刚对一份小说事件计划的连续性进行了评估，发现了一些逻辑断裂和节奏问题。

## 1. 待优化的事件计划 ({stage_name}, {stage_range})
```json
{event_system_str}
```

## 2. 连续性评估发现的关键问题
```json
{critical_issues_str}
```

## 3. 具体的改进建议
```json
{recommendations_str}
```

## 4. 修复指令
请严格遵循上述评估和建议，对"待优化的事件计划"进行优化。

修复重点：
- 逻辑断裂: 修复事件之间的逻辑断层
- 节奏问题: 调整事件密度和分布
- 情感连续性: 确保情感发展连贯
- 主线推进: 确保主线持续高效推进

【最高优先级指令】保持结构完整性：
你返回的最终结果必须是一个与输入结构完全相同的 event_system JSON对象。

## 5. 返回格式
```json
{{
  "optimized_event_system": {{
    "major_events": [
      {{
        "name": "修复后的重大事件1名称",
        "main_goal": "优化后的核心目标",
        "composition": {{
          "起": [],
          "承": [],
          "转": [],
          "合": []
        }}
      }}
    ]
  }},
  "summary_of_continuity_changes": "一句话总结修改"
}}
```
"""
        return prompt