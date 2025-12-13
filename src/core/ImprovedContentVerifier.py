#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的AI输出内容可信度鉴定系统
提供精确的字段级修正指导
"""

import re
import json
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum

class CredibilityLevel(Enum):
    """可信度等级"""
    HIGH = "high"           # 高可信度 - 有权威来源验证
    MEDIUM = "medium"       # 中等可信度 - 部分验证通过
    LOW = "low"            # 低可信度 - 缺乏验证
    UNVERIFIED = "unverified"  # 未验证 - 无法确定

@dataclass
class FieldIssue:
    """字段级问题"""
    field_path: str  # 字段路径，如 "characters.慕沛灵"
    issue_type: str  # 问题类型：错误值、缺失信息、冲突信息
    current_value: str  # 当前值
    expected_value: str  # 期望值
    severity: str  # 严重程度：critical, major, minor
    description: str  # 问题描述

@dataclass
class VerificationResult:
    """验证结果"""
    is_credible: bool
    confidence_score: float  # 0.0-1.0
    credibility_level: CredibilityLevel
    field_issues: List[FieldIssue]  # 字段级问题列表
    suggestions: List[str]
    verified_facts: List[str]
    unverified_facts: List[str]
    correction_guide: Dict  # 修正指导

class ImprovedContentVerifier:
    """改进的AI输出内容验证器"""
    
    def __init__(self):
        self.verified_knowledge_base = self._load_verified_knowledge()
        self.field_validation_rules = self._load_field_validation_rules()
    
    def verify_original_work_background(self, work_name: str, content: Dict) -> VerificationResult:
        """
        验证原著背景资料的可信度，提供字段级修正指导
        
        Args:
            work_name: 作品名称
            content: AI生成的内容
            
        Returns:
            VerificationResult: 包含字段级修正指导的验证结果
        """
        print(f"[VERIFY] 开始验证《{work_name}》背景资料可信度...")
        
        field_issues = []
        suggestions = []
        verified_facts = []
        unverified_facts = []
        correction_guide = {}
        
        confidence_score = 0.0
        total_checks = 0
        passed_checks = 0
        
        # 1. 检查是否有权威知识库数据
        if work_name in self.verified_knowledge_base:
            verified_data = self.verified_knowledge_base[work_name]
            confidence_score += 0.4
            passed_checks += 1
            verified_facts.append("存在权威知识库数据")
            total_checks += 1
            
            # 2. 字段级详细对比
            field_comparison = self._compare_fields_detailed(work_name, content, verified_data)
            field_issues.extend(field_comparison["issues"])
            verified_facts.extend(field_comparison["verified"])
            unverified_facts.extend(field_comparison["unverified"])
            
            passed_checks += field_comparison["passed_checks"]
            total_checks += field_comparison["total_checks"]
            
            # 3. 生成修正指导
            correction_guide = self._generate_correction_guide(field_issues, content, verified_data)
            
        else:
            field_issues.append(FieldIssue(
                field_path="root",
                issue_type="missing_verification_data",
                current_value="",
                expected_value="",
                severity="major",
                description="缺乏权威知识库验证数据"
            ))
            total_checks += 1
        
        # 4. 特定作品专门验证
        if work_name == "凡人修仙传":
            fanren_result = self._verify_fanren_fields_detailed(content)
            field_issues.extend(fanren_result["issues"])
            verified_facts.extend(fanren_result["verified"])
            unverified_facts.extend(fanren_result["unverified"])
            
            passed_checks += fanren_result["passed_checks"]
            total_checks += fanren_result["total_checks"]
        
        # 5. 内部一致性检查
        consistency_result = self._check_internal_consistency_detailed(content)
        field_issues.extend(consistency_result["issues"])
        verified_facts.extend(consistency_result["verified"])
        
        passed_checks += consistency_result["passed_checks"]
        total_checks += consistency_result["total_checks"]
        
        # 计算最终可信度分数
        if total_checks > 0:
            confidence_score = passed_checks / total_checks
        
        # 确定可信度等级
        credibility_level = self._determine_credibility_level(confidence_score, field_issues)
        
        # 生成建议
        if not suggestions:
            suggestions = self._generate_suggestions(field_issues, credibility_level)
        
        return VerificationResult(
            is_credible=credibility_level in [CredibilityLevel.HIGH, CredibilityLevel.MEDIUM],
            confidence_score=confidence_score,
            credibility_level=credibility_level,
            field_issues=field_issues,
            suggestions=suggestions,
            verified_facts=verified_facts,
            unverified_facts=unverified_facts,
            correction_guide=correction_guide
        )
    
    def _compare_fields_detailed(self, work_name: str, content: Dict, verified_data: Dict) -> Dict:
        """详细的字段级对比"""
        result = {
            "issues": [],
            "verified": [],
            "unverified": [],
            "passed_checks": 0,
            "total_checks": 0
        }
        
        # 对比角色信息
        content_chars = content.get("characters", {})
        verified_chars = verified_data.get("characters", {})
        
        for char_name, verified_desc in verified_chars.items():
            field_path = f"characters.{char_name}"
            result["total_checks"] += 1
            
            if char_name in content_chars:
                content_desc = content_chars[char_name]
                
                # 使用验证规则进行精确检查
                if work_name in self.field_validation_rules and char_name in self.field_validation_rules[work_name]:
                    validation_rules = self.field_validation_rules[work_name][char_name]
                    field_check = self._validate_character_field(char_name, content_desc, validation_rules)
                    
                    if field_check["is_correct"]:
                        result["verified"].append(f"{char_name}信息符合验证规则")
                        result["passed_checks"] += 1
                    else:
                        for issue in field_check["issues"]:
                            result["issues"].append(FieldIssue(
                                field_path=field_path,
                                issue_type=issue["type"],
                                current_value=content_desc,
                                expected_value=issue["expected"],
                                severity=issue["severity"],
                                description=issue["description"]
                            ))
                        result["unverified"].append(f"{char_name}的部分信息")
                else:
                    # 通用关键词对比
                    verified_keywords = self._extract_keywords(verified_desc)
                    content_keywords = self._extract_keywords(content_desc)
                    
                    match_score = len(verified_keywords & content_keywords) / len(verified_keywords) if verified_keywords else 0
                    
                    if match_score >= 0.7:
                        result["verified"].append(f"{char_name}信息基本准确")
                        result["passed_checks"] += 1
                    elif match_score >= 0.4:
                        result["issues"].append(FieldIssue(
                            field_path=field_path,
                            issue_type="partial_match",
                            current_value=content_desc,
                            expected_value=verified_desc,
                            severity="major",
                            description=f"{char_name}信息部分准确，但存在偏差"
                        ))
                        result["unverified"].append(f"{char_name}的部分信息")
                    else:
                        result["issues"].append(FieldIssue(
                            field_path=field_path,
                            issue_type="major_mismatch",
                            current_value=content_desc,
                            expected_value=verified_desc,
                            severity="critical",
                            description=f"{char_name}信息与权威数据差异较大"
                        ))
                        result["unverified"].append(f"{char_name}的大部分信息")
            else:
                result["issues"].append(FieldIssue(
                    field_path=field_path,
                    issue_type="missing_field",
                    current_value="",
                    expected_value=verified_desc,
                    severity="critical",
                    description=f"缺少重要角色：{char_name}"
                ))
        
        return result
    
    def _validate_character_field(self, char_name: str, content_desc: str, validation_rules: Dict) -> Dict:
        """使用规则验证角色字段"""
        result = {
            "is_correct": True,
            "issues": []
        }
        
        # 检查必需信息
        if "required_level" in validation_rules:
            required_levels = validation_rules["required_level"]
            if isinstance(required_levels, str):
                required_levels = [required_levels]
            
            has_required = any(level in content_desc for level in required_levels)
            if not has_required:
                result["is_correct"] = False
                result["issues"].append({
                    "type": "missing_required_level",
                    "expected": f"必须包含: {', '.join(required_levels)}",
                    "severity": "critical",
                    "description": f"{char_name}缺少必需的修为信息"
                })
        
        # 检查禁止信息
        if "forbidden_level" in validation_rules:
            forbidden_levels = validation_rules["forbidden_level"]
            if isinstance(forbidden_levels, str):
                forbidden_levels = [forbidden_levels]
            
            has_forbidden = any(level in content_desc for level in forbidden_levels)
            if has_forbidden:
                result["is_correct"] = False
                result["issues"].append({
                    "type": "contains_forbidden_info",
                    "expected": f"不能包含: {', '.join(forbidden_levels)}",
                    "severity": "critical",
                    "description": f"{char_name}包含错误的修为信息"
                })
        
        # 检查必需身份
        if "required_identity" in validation_rules:
            required_identities = validation_rules["required_identity"]
            if isinstance(required_identities, str):
                required_identities = [required_identities]
            
            has_required = any(identity in content_desc for identity in required_identities)
            if not has_required:
                result["is_correct"] = False
                result["issues"].append({
                    "type": "missing_required_identity",
                    "expected": f"必须包含: {', '.join(required_identities)}",
                    "severity": "critical",
                    "description": f"{char_name}缺少必需的身份信息"
                })
        
        # 检查禁止身份
        if "forbidden_identity" in validation_rules:
            forbidden_identities = validation_rules["forbidden_identity"]
            if isinstance(forbidden_identities, str):
                forbidden_identities = [forbidden_identities]
            
            has_forbidden = any(identity in content_desc for identity in forbidden_identities)
            if has_forbidden:
                result["is_correct"] = False
                result["issues"].append({
                    "type": "contains_forbidden_identity",
                    "expected": f"不能包含: {', '.join(forbidden_identities)}",
                    "severity": "critical",
                    "description": f"{char_name}包含错误的身份信息"
                })
        
        # 检查特殊要求
        if "special_requirements" in validation_rules:
            for req in validation_rules["special_requirements"]:
                if req["type"] == "must_contain":
                    if req["value"] not in content_desc:
                        result["is_correct"] = False
                        result["issues"].append({
                            "type": "missing_special_requirement",
                            "expected": f"必须包含: {req['value']}",
                            "severity": req.get("severity", "major"),
                            "description": f"{char_name}缺少特殊要求: {req['description']}"
                        })
                elif req["type"] == "must_not_contain":
                    if req["value"] in content_desc:
                        result["is_correct"] = False
                        result["issues"].append({
                            "type": "contains_forbidden_requirement",
                            "expected": f"不能包含: {req['value']}",
                            "severity": req.get("severity", "critical"),
                            "description": f"{char_name}包含禁止的要求: {req['description']}"
                        })
        
        return result
    
    def _verify_fanren_fields_detailed(self, content: Dict) -> Dict:
        """详细的《凡人修仙传》字段验证"""
        result = {
            "issues": [],
            "verified": [],
            "unverified": [],
            "passed_checks": 0,
            "total_checks": 0
        }
        
        characters = content.get("characters", {})
        
        # 使用验证规则检查每个角色
        if "凡人修仙传" in self.field_validation_rules:
            rules = self.field_validation_rules["凡人修仙传"]
            
            for char_name, char_rules in rules.items():
                if char_name in characters:
                    result["total_checks"] += 1
                    char_desc = characters[char_name]
                    
                    field_check = self._validate_character_field(char_name, char_desc, char_rules)
                    
                    if field_check["is_correct"]:
                        result["verified"].append(f"{char_name}信息验证通过")
                        result["passed_checks"] += 1
                    else:
                        for issue in field_check["issues"]:
                            result["issues"].append(FieldIssue(
                                field_path=f"characters.{char_name}",
                                issue_type=issue["type"],
                                current_value=char_desc,
                                expected_value=issue["expected"],
                                severity=issue["severity"],
                                description=issue["description"]
                            ))
                        result["unverified"].append(f"{char_name}信息")
                else:
                    result["total_checks"] += 1
                    result["issues"].append(FieldIssue(
                        field_path=f"characters.{char_name}",
                        issue_type="missing_character",
                        current_value="",
                        expected_value="",
                        severity="critical",
                        description=f"缺少重要角色: {char_name}"
                    ))
        
        return result
    
    def _check_internal_consistency_detailed(self, content: Dict) -> Dict:
        """详细的内部一致性检查"""
        result = {
            "issues": [],
            "verified": [],
            "passed_checks": 0,
            "total_checks": 0
        }
        
        # 检查JSON结构完整性
        required_fields = ["worldview", "characters", "power_system"]
        for field in required_fields:
            result["total_checks"] += 1
            if field in content and isinstance(content[field], dict):
                result["verified"].append(f"{field}字段结构正确")
                result["passed_checks"] += 1
            else:
                result["issues"].append(FieldIssue(
                    field_path=field,
                    issue_type="missing_required_field",
                    current_value="",
                    expected_value="dict",
                    severity="critical",
                    description=f"缺少必需字段: {field}"
                ))
        
        return result
    
    def _generate_correction_guide(self, field_issues: List[FieldIssue], current_content: Dict, verified_data: Dict) -> Dict:
        """生成精确的修正指导"""
        correction_guide = {
            "preserve_fields": [],  # 需要保持的字段
            "modify_fields": {},    # 需要修改的字段
            "add_fields": {},       # 需要添加的字段
            "remove_fields": [],    # 需要删除的字段
            "specific_corrections": {}  # 具体修正指导
        }
        
        # 分析当前内容的哪些部分是正确的
        for section_name, section_data in current_content.items():
            if section_name in ["worldview", "characters", "power_system"]:
                if isinstance(section_data, dict):
                    if section_name == "characters":
                        # 角色信息需要逐个检查
                        for char_name, char_desc in section_data.items():
                            char_issues = [issue for issue in field_issues if issue.field_path == f"characters.{char_name}"]
                            if not char_issues:
                                correction_guide["preserve_fields"].append(f"characters.{char_name}")
                            else:
                                correction_guide["modify_fields"][f"characters.{char_name}"] = {
                                    "current_value": char_desc,
                                    "issues": [issue.description for issue in char_issues],
                                    "suggested_fix": self._generate_character_fix(char_name, char_issues, verified_data)
                                }
                    else:
                        # 其他字段整体检查
                        section_issues = [issue for issue in field_issues if issue.field_path.startswith(section_name)]
                        if not section_issues:
                            correction_guide["preserve_fields"].append(section_name)
                        else:
                            correction_guide["modify_fields"][section_name] = {
                                "current_value": section_data,
                                "issues": [issue.description for issue in section_issues],
                                "suggested_fix": self._generate_section_fix(section_name, section_issues, verified_data)
                            }
        
        # 添加缺失的字段
        for issue in field_issues:
            if issue.issue_type == "missing_field" or issue.issue_type == "missing_character":
                field_path = issue.field_path
                correction_guide["add_fields"][field_path] = {
                    "suggested_value": issue.expected_value,
                    "description": issue.description
                }
        
        return correction_guide
    
    def _generate_character_fix(self, char_name: str, issues: List[FieldIssue], verified_data: Dict) -> str:
        """生成角色修正建议"""
        if char_name in verified_data.get("characters", {}):
            verified_desc = verified_data["characters"][char_name]
            
            fix_suggestions = []
            for issue in issues:
                if issue.issue_type == "missing_required_level":
                    fix_suggestions.append(f"修为应为{issue.expected_value}")
                elif issue.issue_type == "contains_forbidden_info":
                    fix_suggestions.append(f"不应包含{issue.expected_value}")
                elif issue.issue_type == "missing_required_identity":
                    fix_suggestions.append(f"身份应为{issue.expected_value}")
                elif issue.issue_type == "contains_forbidden_identity":
                    fix_suggestions.append(f"身份不应为{issue.expected_value}")
            
            if fix_suggestions:
                return f"建议: {', '.join(fix_suggestions)}。参考标准: {verified_desc}"
            else:
                return f"参考标准描述: {verified_desc}"
        
        return "请根据原著修正此角色信息"
    
    def _generate_section_fix(self, section_name: str, issues: List[FieldIssue], verified_data: Dict) -> str:
        """生成章节修正建议"""
        if section_name in verified_data:
            verified_section = verified_data[section_name]
            return f"参考标准{section_name}: {verified_section}"
        
        return f"请修正{section_name}部分的错误"
    
    def _extract_keywords(self, text: str) -> set:
        """提取文本中的关键词"""
        keywords = set()
        
        # 修为等级关键词
        levels = ["炼气期", "筑基期", "结丹期", "元婴期", "化神期", "结丹后期", "大圆满"]
        for level in levels:
            if level in text:
                keywords.add(level)
        
        # 身份关键词
        identities = ["散修", "宗门", "魔道", "正道", "逆星盟", "乱星海", "落云宗"]
        for identity in identities:
            if identity in text:
                keywords.add(identity)
        
        # 特殊体质
        special_bodies = ["通玉凤髓之体", "特殊体质"]
        for body in special_bodies:
            if body in text:
                keywords.add(body)
        
        # 功法神通
        techniques = ["辟邪神雷", "青元剑诀", "六极真魔功"]
        for technique in techniques:
            if technique in text:
                keywords.add(technique)
        
        # 重要物品
        items = ["掌天瓶"]
        for item in items:
            if item in text:
                keywords.add(item)
        
        return keywords
    
    def _determine_credibility_level(self, score: float, issues: List[FieldIssue]) -> CredibilityLevel:
        """确定可信度等级"""
        critical_issues = len([issue for issue in issues if issue.severity == "critical"])
        major_issues = len([issue for issue in issues if issue.severity == "major"])
        
        if score >= 0.8 and critical_issues == 0 and major_issues <= 1:
            return CredibilityLevel.HIGH
        elif score >= 0.6 and critical_issues == 0 and major_issues <= 3:
            return CredibilityLevel.MEDIUM
        elif score >= 0.4:
            return CredibilityLevel.LOW
        else:
            return CredibilityLevel.UNVERIFIED
    
    def _generate_suggestions(self, issues: List[FieldIssue], level: CredibilityLevel) -> List[str]:
        """基于字段级问题生成改进建议"""
        suggestions = []
        
        critical_issues = [issue for issue in issues if issue.severity == "critical"]
        major_issues = [issue for issue in issues if issue.severity == "major"]
        
        if critical_issues:
            suggestions.append(f"发现{len(critical_issues)}个严重问题，需要立即修正")
            suggestions.append("建议使用针对性修正功能，只修正错误部分")
        
        if major_issues:
            suggestions.append(f"发现{len(major_issues)}个重要问题，建议修正")
        
        if level == CredibilityLevel.HIGH:
            suggestions.append("内容可信度高，可以放心使用")
        elif level == CredibilityLevel.MEDIUM:
            suggestions.append("建议修正主要问题后使用")
        elif level == CredibilityLevel.LOW:
            suggestions.append("建议修正所有问题后再使用")
        else:
            suggestions.append("内容可信度不足，建议重新生成或全面修正")
        
        return suggestions
    
    def _load_verified_knowledge(self) -> Dict:
        """加载已验证的知识库"""
        return {
            "凡人修仙传": {
                "characters": {
                    "韩立": "原著主角，结丹后期大圆满修士，修炼《青元剑诀》和《辟邪神雷》，身怀掌天瓶",
                    "慕沛灵": "落云宗筑基期女修（重要：此时为筑基期，非结丹期），容貌绝美，资质出众，因家族逼迫和宗门内元婴长老觊觎而深陷困境",
                    "梅凝": "拥有极其罕见的'通玉凤髓之体'的特殊体质女子，是绝佳的双修鼎炉，因此被魔道修士觊觎，心地善良，性格坚韧",
                    "温天仁": "乱星海逆星盟修士，结丹后期大圆满修士，修炼《六极真魔功》。与韩立有私人恩怨（重要：来自乱星海逆星盟，非天南魔道六宗），心狠手辣"
                },
                "worldview": {
                    "世界名称": "人界 - 天南地区、乱星海",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界。修仙资源稀缺，修士之间为了功法、丹药、法宝等资源不惜生死相搏",
                    "社会结构": "天南地区：三大正道宗门（落云宗、古剑门、百巧院）、三大魔道宗门（合欢宗、鬼灵门、天煞宗）以及众多散修；乱星海：逆星盟等势力"
                },
                "power_system": {
                    "体系名称": "凡人流修仙体系",
                    "等级划分": "炼气期(共十三层) → 筑基期(分前、中、后三期) → 结丹期(分前、中、后三期及大圆满) → 元婴期(分前、中、后三期) → 化神期",
                    "特殊能力": "功法神通（如韩立的《辟邪神雷》、温天仁的《六极真魔功》）、法宝古宝、特殊体质（如梅凝的《通玉凤髓之体》）、结婴天象（突破元婴时引发的天地异象）"
                }
            }
        }
    
    def _load_field_validation_rules(self) -> Dict:
        """加载字段验证规则"""
        return {
            "凡人修仙传": {
                "慕沛灵": {
                    "required_level": ["筑基期"],
                    "forbidden_level": ["结丹期"],
                    "required_identity": ["落云宗"],
                    "special_requirements": [
                        {
                            "type": "must_contain",
                            "value": "筑基期",
                            "severity": "critical",
                            "description": "慕沛灵此时必须是筑基期"
                        },
                        {
                            "type": "must_not_contain",
                            "value": "结丹期",
                            "severity": "critical",
                            "description": "慕沛灵此时不能是结丹期"
                        }
                    ]
                },
                "温天仁": {
                    "required_identity": ["逆星盟", "乱星海"],
                    "forbidden_identity": ["合欢宗", "鬼灵门", "天煞宗", "天南六宗"],
                    "required_technique": ["六极真魔功"],
                    "special_requirements": [
                        {
                            "type": "must_contain",
                            "value": "逆星盟",
                            "severity": "critical",
                            "description": "温天仁必须来自逆星盟"
                        },
                        {
                            "type": "must_not_contain",
                            "value": "合欢宗",
                            "severity": "critical",
                            "description": "温天仁不是合欢宗成员"
                        }
                    ]
                },
                "韩立": {
                    "required_level": ["结丹后期", "结丹后期大圆满"],
                    "required_techniques": ["辟邪神雷", "青元剑诀"],
                    "special_requirements": [
                        {
                            "type": "must_contain",
                            "value": "辟邪神雷",
                            "severity": "major",
                            "description": "韩立应该掌握辟邪神雷"
                        }
                    ]
                },
                "梅凝": {
                    "special_requirements": [
                        {
                            "type": "must_contain",
                            "value": "通玉凤髓之体",
                            "severity": "critical",
                            "description": "梅凝必须有通玉凤髓之体"
                        }
                    ]
                }
            }
        }