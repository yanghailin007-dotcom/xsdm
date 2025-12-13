#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能内容验证器 - 防止过度修正
引入"不轻易修改正确信息"的保护机制
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ConfidenceLevel(Enum):
    """置信度等级"""
    HIGH = "high"           # 高置信度 - 可以安全修改
    MEDIUM = "medium"       # 中等置信度 - 需要谨慎验证
    LOW = "low"            # 低置信度 - 建议保持原样
    CRITICAL = "critical"   # 关键信息 - 禁止修改

@dataclass
class ValidationRule:
    """验证规则"""
    field_path: str
    confidence_threshold: float  # 修改此字段需要的最低置信度
    preserve_if_correct: bool    # 如果已经正确是否保持不变
    correction_risk: str         # 修正风险等级：low, medium, high, critical

class SmartContentVerifier:
    """智能内容验证器 - 防止过度修正"""
    
    def __init__(self):
        self.authoritative_knowledge = self._load_authoritative_knowledge()
        self.validation_rules = self._load_validation_rules()
        self.preservation_threshold = 0.8  # 高置信度阈值，超过此值认为信息正确
    
    def verify_with_preservation(self, work_name: str, content: Dict, previous_content: Optional[Dict] = None) -> Dict:
        """
        带保护机制的验证
        
        Args:
            work_name: 作品名称
            content: 当前内容
            previous_content: 之前的内容（用于保护）
            
        Returns:
            验证结果和修正建议
        """
        print(f"[SMART_VERIFY] 开始智能验证《{work_name}》背景资料...")
        
        result = {
            "is_credible": False,
            "confidence_score": 0.0,
            "issues_found": [],
            "correction_suggestions": [],
            "preservation_warnings": [],
            "safe_to_modify": [],
            "should_preserve": []
        }
        
        # 1. 检查与权威知识的匹配度
        authority_match = self._check_authority_knowledge(work_name, content)
        result["confidence_score"] = authority_match["overall_score"]
        
        # 2. 如果有之前的内容，检查哪些部分应该保持不变
        if previous_content:
            preservation_analysis = self._analyze_preservation_needs(content, previous_content)
            result["preservation_warnings"] = preservation_analysis["warnings"]
            result["should_preserve"] = preservation_analysis["preserve_fields"]
            result["safe_to_modify"] = preservation_analysis["safe_to_modify"]
        
        # 3. 生成保守的修正建议
        correction_analysis = self._generate_conservative_corrections(work_name, content, previous_content)
        result["correction_suggestions"] = correction_analysis["suggestions"]
        result["issues_found"] = correction_analysis["issues"]
        
        # 4. 确定整体可信度
        result["is_credible"] = result["confidence_score"] >= 0.7 and len(correction_analysis["critical_issues"]) == 0
        
        return result
    
    def _check_authority_knowledge(self, work_name: str, content: Dict) -> Dict:
        """检查与权威知识的匹配度"""
        if work_name not in self.authoritative_knowledge:
            return {"overall_score": 0.0, "field_scores": {}, "matched_fields": []}
        
        authority_data = self.authoritative_knowledge[work_name]
        field_scores = {}
        matched_fields = []
        total_score = 0.0
        field_count = 0
        
        # 检查角色信息
        if "characters" in content and "characters" in authority_data:
            for char_name, authority_desc in authority_data["characters"].items():
                if char_name in content["characters"]:
                    content_desc = content["characters"][char_name]
                    match_score = self._calculate_text_similarity(content_desc, authority_desc)
                    field_scores[f"characters.{char_name}"] = match_score
                    total_score += match_score
                    field_count += 1
                    
                    if match_score >= self.preservation_threshold:
                        matched_fields.append(f"characters.{char_name}")
        
        overall_score = total_score / field_count if field_count > 0 else 0.0
        
        return {
            "overall_score": overall_score,
            "field_scores": field_scores,
            "matched_fields": matched_fields
        }
    
    def _analyze_preservation_needs(self, current_content: Dict, previous_content: Dict) -> Dict:
        """分析哪些字段需要保持不变"""
        warnings = []
        preserve_fields = []
        safe_to_modify = []
        
        # 检查每个字段的变化
        for section_name in ["worldview", "characters", "power_system"]:
            if section_name in current_content and section_name in previous_content:
                current_section = current_content[section_name]
                previous_section = previous_content[section_name]
                
                if isinstance(current_section, dict) and isinstance(previous_section, dict):
                    for field_name, current_value in current_section.items():
                        if field_name in previous_section:
                            previous_value = previous_section[field_name]
                            
                            if current_value == previous_value:
                                # 值没有变化，标记为应该保持
                                preserve_fields.append(f"{section_name}.{field_name}")
                            else:
                                # 值有变化，检查是否有必要
                                similarity = self._calculate_text_similarity(str(current_value), str(previous_value))
                                if similarity >= 0.8:  # 高相似度，可能是微调
                                    preserve_fields.append(f"{section_name}.{field_name}")
                                    warnings.append(f"{section_name}.{field_name} 变化较小，建议保持原样")
                                elif similarity >= 0.5:  # 中等相似度，需要谨慎
                                    safe_to_modify.append(f"{section_name}.{field_name}")
                                else:  # 低相似度，可能是必要修正
                                    safe_to_modify.append(f"{section_name}.{field_name}")
        
        return {
            "warnings": warnings,
            "preserve_fields": preserve_fields,
            "safe_to_modify": safe_to_modify
        }
    
    def _generate_conservative_corrections(self, work_name: str, content: Dict, previous_content: Optional[Dict]) -> Dict:
        """生成保守的修正建议"""
        suggestions = []
        issues = []
        critical_issues = []
        
        # 只对关键错误提出修正建议
        if work_name == "凡人修仙传":
            fanren_issues = self._check_fanren_critical_issues(content)
            issues.extend(fanren_issues["issues"])
            critical_issues.extend(fanren_issues["critical_issues"])
            
            # 为关键问题生成修正建议
            for issue in fanren_issues["critical_issues"]:
                suggestions.append({
                    "field": issue["field"],
                    "problem": issue["problem"],
                    "suggestion": issue["suggestion"],
                    "priority": "critical",
                    "reason": "关键事实错误，必须修正"
                })
        
        return {
            "suggestions": suggestions,
            "issues": issues,
            "critical_issues": critical_issues
        }
    
    def _check_fanren_critical_issues(self, content: Dict) -> Dict:
        """检查凡人修仙传的关键问题"""
        issues = []
        critical_issues = []
        
        characters = content.get("characters", {})
        
        # 检查慕沛灵修为 - 这是关键验证点
        if "慕沛灵" in characters:
            mupeiling_desc = characters["慕沛灵"]
            if "结丹期" in mupeiling_desc and "筑基期" not in mupeiling_desc:
                critical_issues.append({
                    "field": "characters.慕沛灵",
                    "problem": "修为错误：原著中此时为筑基期，非结丹期",
                    "suggestion": "将修为改为筑基期，删除结丹期相关描述"
                })
        
        # 检查梅凝体质 - 这是另一个关键点
        if "梅凝" in characters:
            meining_desc = characters["梅凝"]
            if "通玉凤髓之体" not in meining_desc:
                critical_issues.append({
                    "field": "characters.梅凝",
                    "problem": "缺少特殊体质：应为通玉凤髓之体",
                    "suggestion": "添加通玉凤髓之体的描述"
                })
        
        return {
            "issues": issues,
            "critical_issues": critical_issues
        }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 简单的关键词匹配算法
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _load_authoritative_knowledge(self) -> Dict:
        """加载权威知识库 - 基于原著的准确信息"""
        return {
            "凡人修仙传": {
                "characters": {
                    "韩立": {
                        "key_facts": [
                            "结丹后期大圆满修士",
                            "修炼青元剑诀",
                            "掌握辟邪神雷", 
                            "身怀掌天瓶",
                            "人称韩老魔"
                        ],
                        "critical_points": ["结丹后期", "辟邪神雷"]
                    },
                    "慕沛灵": {
                        "key_facts": [
                            "落云宗女弟子",
                            "筑基期修为",  # 关键：此时为筑基期
                            "容貌绝美",
                            "因家族逼迫面临困境"
                        ],
                        "critical_points": ["筑基期", "落云宗"]
                    },
                    "梅凝": {
                        "key_facts": [
                            "拥有通玉凤髓之体",
                            "是绝佳双修鼎炉",
                            "被魔道修士觊觎",
                            "心地善良性格坚韧"
                        ],
                        "critical_points": ["通玉凤髓之体"]
                    },
                    "温天仁": {
                        "key_facts": [
                            "乱星海逆星盟修士",
                            "魔道年轻一代的顶尖人物",
                            "结丹期大圆满修士",
                            "修炼六极真魔功",
                            "心狠手辣狂傲自负",
                            "是韩立结丹期最强大的敌人之一"
                        ],
                        "critical_points": ["逆星盟", "乱星海", "六极真魔功"]
                    }
                }
            }
        }
    
    def _load_validation_rules(self) -> Dict:
        """加载验证规则"""
        return {
            "凡人修仙传": {
                "characters.慕沛灵": ValidationRule(
                    field_path="characters.慕沛灵",
                    confidence_threshold=0.9,
                    preserve_if_correct=True,
                    correction_risk="critical"
                ),
                "characters.梅凝": ValidationRule(
                    field_path="characters.梅凝", 
                    confidence_threshold=0.9,
                    preserve_if_correct=True,
                    correction_risk="critical"
                ),
                "characters.温天仁": ValidationRule(
                    field_path="characters.温天仁",
                    confidence_threshold=0.9,
                    preserve_if_correct=True,
                    correction_risk="critical"
                ),
                "characters.韩立": ValidationRule(
                    field_path="characters.韩立",
                    confidence_threshold=0.9,
                    preserve_if_correct=True,
                    correction_risk="critical"
                )
            }
        }