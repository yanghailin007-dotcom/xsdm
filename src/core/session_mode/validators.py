"""
产物格式验证器 - 确保对话模式产物与传统模式一致
========================================================

提供功能：
1. JSON Schema 定义各步骤产物格式
2. 字段对比工具
3. 差异报告生成
4. 产物兼容性验证

使用示例：
    from src.core.session_mode.validators import FoundationPlanningValidator
    
    validator = FoundationPlanningValidator()
    is_valid = validator.validate(output)
    if not is_valid:
        print(validator.get_error_report())
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

try:
    import deepdiff
    DEEPDIFF_AVAILABLE = True
except ImportError:
    DEEPDIFF_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """验证错误信息"""
    field: str
    expected: Any
    actual: Any
    error_type: str  # 'missing', 'type_mismatch', 'value_mismatch', 'extra'
    message: str


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, field: str, expected: Any, actual: Any, 
                  error_type: str, message: str):
        self.errors.append(ValidationError(
            field=field, expected=expected, actual=actual,
            error_type=error_type, message=message
        ))
        self.is_valid = False
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def get_error_report(self) -> str:
        """生成错误报告"""
        if self.is_valid:
            return "✅ 验证通过"
        
        report = ["❌ 验证失败:"]
        for error in self.errors:
            report.append(f"  - {error.field}: {error.message}")
            report.append(f"    期望: {error.expected}")
            report.append(f"    实际: {error.actual}")
        
        if self.warnings:
            report.append("\n⚠️ 警告:")
            for warning in self.warnings:
                report.append(f"  - {warning}")
        
        return "\n".join(report)


class BaseValidator:
    """基础验证器"""
    
    # 必需字段定义，子类需要覆盖
    REQUIRED_FIELDS: Dict[str, type] = {}
    
    # 可选字段定义
    OPTIONAL_FIELDS: Dict[str, type] = {}
    
    # 嵌套验证器
    NESTED_VALIDATORS: Dict[str, 'BaseValidator'] = {}
    
    def _get_type_name(self, field_type) -> str:
        """获取类型名称（支持联合类型）"""
        if isinstance(field_type, tuple):
            return " or ".join(t.__name__ for t in field_type)
        return field_type.__name__
    
    def validate(self, output: Dict[str, Any]) -> ValidationResult:
        """
        验证产物格式
        
        Args:
            output: 待验证的产物字典
            
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(output, dict):
            result.add_error(
                field="<root>",
                expected="dict",
                actual=type(output).__name__,
                error_type="type_mismatch",
                message="产物必须是字典类型"
            )
            return result
        
        # 检查必需字段
        for field_name, field_type in self.REQUIRED_FIELDS.items():
            if field_name not in output:
                result.add_error(
                    field=field_name,
                    expected=self._get_type_name(field_type),
                    actual="missing",
                    error_type="missing",
                    message=f"缺少必需字段: {field_name}"
                )
            else:
                # 类型检查
                actual_value = output[field_name]
                if not self._check_type(actual_value, field_type):
                    result.add_error(
                        field=field_name,
                        expected=self._get_type_name(field_type),
                        actual=type(actual_value).__name__,
                        error_type="type_mismatch",
                        message=f"字段 {field_name} 类型不匹配"
                    )
                else:
                    # 嵌套验证
                    if field_name in self.NESTED_VALIDATORS and isinstance(actual_value, dict):
                        nested_result = self.NESTED_VALIDATORS[field_name].validate(actual_value)
                        if not nested_result.is_valid:
                            for error in nested_result.errors:
                                error.field = f"{field_name}.{error.field}"
                                result.errors.append(error)
                            result.is_valid = False
        
        # 检查未知字段（警告级别）
        known_fields = set(self.REQUIRED_FIELDS.keys()) | set(self.OPTIONAL_FIELDS.keys())
        for field_name in output.keys():
            if field_name not in known_fields:
                result.add_warning(f"发现未知字段: {field_name}")
        
        return result
    
    def _check_type(self, value: Any, expected_type: type) -> bool:
        """检查值类型是否匹配"""
        if expected_type == Any:
            return True
        if expected_type == dict:
            return isinstance(value, dict)
        if expected_type == list:
            return isinstance(value, list)
        if expected_type == str:
            return isinstance(value, str)
        if expected_type == int:
            return isinstance(value, int)
        if expected_type == float:
            return isinstance(value, (int, float))
        if expected_type == bool:
            return isinstance(value, bool)
        return isinstance(value, expected_type)
    
    def compare_with_reference(self, output: Dict[str, Any], 
                               reference: Dict[str, Any]) -> Dict[str, Any]:
        """
        与参考产物进行对比
        
        Args:
            output: 对话模式产物
            reference: 传统模式参考产物
            
        Returns:
            差异报告
        """
        if not DEEPDIFF_AVAILABLE:
            logger.warning("deepdiff 不可用，使用简单对比")
            return self._simple_compare(output, reference)
        
        diff = deepdiff.DeepDiff(reference, output, ignore_order=True)
        return {
            "differences": diff,
            "has_differences": bool(diff),
            "summary": self._summarize_diff(diff)
        }
    
    def _simple_compare(self, output: Dict, reference: Dict) -> Dict:
        """简单对比（无deepdiff时）"""
        differences = {}
        
        all_keys = set(output.keys()) | set(reference.keys())
        for key in all_keys:
            if key not in reference:
                differences[key] = {"type": "added", "value": output.get(key)}
            elif key not in output:
                differences[key] = {"type": "removed", "expected": reference.get(key)}
            elif output[key] != reference[key]:
                differences[key] = {
                    "type": "modified",
                    "expected": reference.get(key),
                    "actual": output.get(key)
                }
        
        return {
            "differences": differences,
            "has_differences": bool(differences),
            "summary": f"发现 {len(differences)} 处差异"
        }
    
    def _summarize_diff(self, diff: Any) -> str:
        """总结差异"""
        if not diff:
            return "无差异"
        
        summary_parts = []
        if 'dictionary_item_added' in diff:
            summary_parts.append(f"新增 {len(diff['dictionary_item_added'])} 个字段")
        if 'dictionary_item_removed' in diff:
            summary_parts.append(f"缺失 {len(diff['dictionary_item_removed'])} 个字段")
        if 'values_changed' in diff:
            summary_parts.append(f"修改 {len(diff['values_changed'])} 个值")
        if 'type_changes' in diff:
            summary_parts.append(f"类型变化 {len(diff['type_changes'])} 处")
        
        return "; ".join(summary_parts) if summary_parts else "未知差异"


# =============================================================================
# FoundationPlanning 验证器 (Session A)
# =============================================================================

class WritingStyleValidator(BaseValidator):
    """写作风格指南验证器"""
    REQUIRED_FIELDS = {
        "core_style": str,
        "language_characteristics": list,
        "key_principles": list,
    }
    OPTIONAL_FIELDS = {
        "atmosphere": str,
        "pacing": str,
        "dialogue_style": str,
    }


class MarketAnalysisValidator(BaseValidator):
    """市场分析验证器"""
    REQUIRED_FIELDS = {
        "target_platform": str,
        "genre_positioning": str,
        "core_selling_points": list,
    }
    OPTIONAL_FIELDS = {
        "target_audience": str,
        "competitive_analysis": dict,
        "market_potential": str,
    }


class CoreWorldviewValidator(BaseValidator):
    """核心世界观验证器"""
    REQUIRED_FIELDS = {
        "world_overview": str,
        "power_system": str,
    }
    OPTIONAL_FIELDS = {
        "key_locations": list,
        "world_rules": list,
        "historical_background": str,
    }


class FactionSystemValidator(BaseValidator):
    """势力系统验证器"""
    REQUIRED_FIELDS = {
        "factions": list,
        "main_conflict": str,
    }
    OPTIONAL_FIELDS = {
        "faction_power_balance": str,
        "recommended_starting_faction": str,
    }


class FoundationPlanningValidator(BaseValidator):
    """
    FoundationPlanningSession 产物验证器
    
    验证字段：
    - writing_style_guide: 写作风格指南
    - market_analysis: 市场分析
    - core_worldview: 核心世界观
    - faction_system: 势力系统
    """
    REQUIRED_FIELDS = {
        "writing_style_guide": dict,
        "market_analysis": dict,
        "core_worldview": dict,
        "faction_system": dict,
    }
    
    NESTED_VALIDATORS = {
        "writing_style_guide": WritingStyleValidator(),
        "market_analysis": MarketAnalysisValidator(),
        "core_worldview": CoreWorldviewValidator(),
        "faction_system": FactionSystemValidator(),
    }


# =============================================================================
# CharacterNarrative 验证器 (Session B)
# =============================================================================

class CharacterBasicInfoValidator(BaseValidator):
    """角色基础信息验证器"""
    REQUIRED_FIELDS = {
        "name": str,
    }
    OPTIONAL_FIELDS = {
        "age": (int, str),
        "gender": str,
        "appearance": str,
        "personality": str,
    }


class ProtagonistValidator(BaseValidator):
    """主角验证器"""
    REQUIRED_FIELDS = {
        "basic_info": dict,
        "goals": (str, list, dict),
        "abilities": (str, list, dict),
    }
    NESTED_VALIDATORS = {
        "basic_info": CharacterBasicInfoValidator(),
    }


class CharacterDesignValidator(BaseValidator):
    """角色设计验证器"""
    REQUIRED_FIELDS = {
        "protagonist": dict,
    }
    OPTIONAL_FIELDS = {
        "supporting_characters": list,
        "antagonist": dict,
    }
    NESTED_VALIDATORS = {
        "protagonist": ProtagonistValidator(),
    }


class EmotionalBlueprintValidator(BaseValidator):
    """情绪蓝图验证器"""
    REQUIRED_FIELDS = {
        "emotional_arcs": list,
    }
    OPTIONAL_FIELDS = {
        "key_emotional_beats": list,
        "emotional_themes": list,
    }


class GrowthPlanValidator(BaseValidator):
    """成长规划验证器"""
    REQUIRED_FIELDS = {
        "protagonist_growth": list,
        "milestone_events": list,
    }
    OPTIONAL_FIELDS = {
        "power_progression": list,
        "relationship_development": list,
    }


class CharacterNarrativeValidator(BaseValidator):
    """
    CharacterNarrativeSession 产物验证器
    
    验证字段：
    - character_design: 角色设计
    - emotional_blueprint: 情绪蓝图
    - global_growth_plan: 全局成长规划
    """
    REQUIRED_FIELDS = {
        "character_design": dict,
        "emotional_blueprint": dict,
        "global_growth_plan": dict,
    }
    
    NESTED_VALIDATORS = {
        "character_design": CharacterDesignValidator(),
        "emotional_blueprint": EmotionalBlueprintValidator(),
        "global_growth_plan": GrowthPlanValidator(),
    }


# =============================================================================
# StructurePlanning 验证器 (Session C)
# =============================================================================

class StageValidator(BaseValidator):
    """单个阶段验证器"""
    REQUIRED_FIELDS = {
        "stage_name": str,
        "chapter_range": str,
        "core_conflict": str,
    }
    OPTIONAL_FIELDS = {
        "emotional_focus": str,
        "growth_goals": str,
        "key_events": list,
    }


class StageOverviewValidator(BaseValidator):
    """阶段概览验证器"""
    REQUIRED_FIELDS = {
        "stages": list,
    }


class ChapterBreakdownValidator(BaseValidator):
    """章节分解验证器"""
    REQUIRED_FIELDS = {
        "chapter_number": (int, str),
        "title": str,
    }
    OPTIONAL_FIELDS = {
        "key_events": str,
        "emotional_tone": str,
        "plot_progression": str,
    }


class StageWritingPlanValidator(BaseValidator):
    """阶段写作计划验证器"""
    REQUIRED_FIELDS = {
        "chapter_breakdown": list,
    }


class StructurePlanningValidator(BaseValidator):
    """
    StructurePlanningSession 产物验证器
    
    验证字段：
    - overall_stage_plans: 全书阶段计划概览
    - stage_writing_plans: 各阶段详细写作计划
    - supplementary_characters: 补充角色
    """
    REQUIRED_FIELDS = {
        "overall_stage_plans": dict,
        "stage_writing_plans": dict,
    }
    OPTIONAL_FIELDS = {
        "supplementary_characters": list,
    }
    
    NESTED_VALIDATORS = {
        "overall_stage_plans": StageOverviewValidator(),
    }


# =============================================================================
# ExpectationSystem 验证器 (Session D)
# =============================================================================

class ExpectationMappingValidator(BaseValidator):
    """期待感映射验证器"""
    REQUIRED_FIELDS = {
        "expectation_elements": list,
    }
    OPTIONAL_FIELDS = {
        "element_schedule": dict,
        "reveal_timing": dict,
    }


class SystemInitValidator(BaseValidator):
    """系统初始化验证器"""
    REQUIRED_FIELDS = {}
    OPTIONAL_FIELDS = {
        "initialized_systems": list,
        "status": str,
    }


class ExpectationSystemValidator(BaseValidator):
    """
    ExpectationSystemSession 产物验证器
    
    验证字段：
    - expectation_mapping: 期待感映射
    - system_init: 系统初始化状态
    """
    REQUIRED_FIELDS = {
        "expectation_mapping": dict,
    }
    OPTIONAL_FIELDS = {
        "system_init": dict,
    }
    
    NESTED_VALIDATORS = {
        "expectation_mapping": ExpectationMappingValidator(),
        "system_init": SystemInitValidator(),
    }


# =============================================================================
# 验证器工厂
# =============================================================================

class ValidatorFactory:
    """验证器工厂"""
    
    _validators = {
        'foundation_planning': FoundationPlanningValidator,
        'character_narrative': CharacterNarrativeValidator,
        'structure_planning': StructurePlanningValidator,
        'expectation_system': ExpectationSystemValidator,
        # 传统步骤验证器
        'writing_style': WritingStyleValidator,
        'market_analysis': MarketAnalysisValidator,
        'character_design': CharacterDesignValidator,
        'emotional_blueprint': EmotionalBlueprintValidator,
        'stage_plan': StageOverviewValidator,
    }
    
    @classmethod
    def get_validator(cls, step_name: str) -> Optional[BaseValidator]:
        """获取验证器实例"""
        validator_class = cls._validators.get(step_name)
        if validator_class:
            return validator_class()
        return None
    
    @classmethod
    def register_validator(cls, step_name: str, validator_class: type):
        """注册新的验证器"""
        cls._validators[step_name] = validator_class


# =============================================================================
# 对比测试工具
# =============================================================================

def compare_session_outputs(
    traditional_output: Dict[str, Any],
    conversation_output: Dict[str, Any],
    session_name: str
) -> Dict[str, Any]:
    """
    对比传统模式和对话模式的产物
    
    Args:
        traditional_output: 传统模式产物
        conversation_output: 对话模式产物
        session_name: Session名称
        
    Returns:
        对比结果报告
    """
    validator = ValidatorFactory.get_validator(session_name)
    if not validator:
        return {
            "error": f"未找到 {session_name} 的验证器",
            "is_valid": False
        }
    
    # 验证对话模式产物
    validation_result = validator.validate(conversation_output)
    
    # 对比差异
    diff_report = validator.compare_with_reference(conversation_output, traditional_output)
    
    return {
        "session_name": session_name,
        "validation_passed": validation_result.is_valid,
        "validation_errors": [e.message for e in validation_result.errors],
        "validation_warnings": validation_result.warnings,
        "has_differences": diff_report.get("has_differences", True),
        "difference_summary": diff_report.get("summary", "无法计算差异"),
        "detailed_diff": diff_report.get("differences", {}),
        "is_compatible": validation_result.is_valid and not diff_report.get("has_differences", True)
    }


def generate_comparison_report(results: List[Dict[str, Any]]) -> str:
    """生成对比测试报告"""
    report_lines = [
        "=" * 80,
        "第一阶段对话化改造 - 产物对比测试报告",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 80,
        ""
    ]
    
    all_passed = True
    for result in results:
        session_name = result.get("session_name", "Unknown")
        report_lines.append(f"\n【{session_name}】")
        report_lines.append("-" * 40)
        
        if result.get("error"):
            report_lines.append(f"❌ 错误: {result['error']}")
            all_passed = False
            continue
        
        # 验证状态
        if result.get("validation_passed"):
            report_lines.append("✅ 格式验证通过")
        else:
            report_lines.append("❌ 格式验证失败")
            for error in result.get("validation_errors", []):
                report_lines.append(f"   - {error}")
            all_passed = False
        
        # 差异状态
        if result.get("has_differences"):
            report_lines.append(f"⚠️ 存在差异: {result.get('difference_summary', '')}")
        else:
            report_lines.append("✅ 与参考产物完全一致")
        
        # 兼容性
        if result.get("is_compatible"):
            report_lines.append("✅ 兼容性: 通过")
        else:
            report_lines.append("❌ 兼容性: 失败")
    
    report_lines.extend([
        "",
        "=" * 80,
        f"总体结果: {'✅ 全部通过' if all_passed else '❌ 存在失败'}"
    ])
    
    return "\n".join(report_lines)


# =============================================================================
# 便捷函数
# =============================================================================

def quick_validate(session_name: str, output: Dict[str, Any]) -> bool:
    """快速验证产物格式"""
    validator = ValidatorFactory.get_validator(session_name)
    if not validator:
        logger.warning(f"未找到 {session_name} 的验证器")
        return True
    
    result = validator.validate(output)
    if not result.is_valid:
        logger.warning(f"{session_name} 验证失败:\n{result.get_error_report()}")
    
    return result.is_valid


def validate_all_sessions(outputs: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
    """验证所有 Session 的产物"""
    results = {}
    for session_name, output in outputs.items():
        results[session_name] = quick_validate(session_name, output)
    return results
