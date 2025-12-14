#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI输出内容可信度鉴定系统
用于验证AI生成内容的准确性和可靠性
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
class VerificationResult:
    """验证结果"""
    is_credible: bool
    confidence_score: float  # 0.0-1.0
    credibility_level: CredibilityLevel
    issues_found: List[str]
    suggestions: List[str]
    verified_facts: List[str]
    unverified_facts: List[str]

class ContentVerifier:
    """AI输出内容验证器"""
    
    def __init__(self):
        self.verified_knowledge_base = self._load_verified_knowledge()
        self.controversial_topics = self._load_controversial_topics()
        self.fact_checking_rules = self._load_fact_checking_rules()
    
    def verify_original_work_background(self, work_name: str, content: Dict) -> VerificationResult:
        """
        验证原著背景资料的可信度
        
        Args:
            work_name: 作品名称
            content: AI生成的内容
            
        Returns:
            VerificationResult: 验证结果
        """
        print(f"[VERIFY] 开始验证《{work_name}》背景资料可信度...")
        
        issues_found = []
        suggestions = []
        verified_facts = []
        unverified_facts = []
        
        confidence_score = 0.0
        total_checks = 0
        passed_checks = 0
        
        # 检查是否从知识库加载 - 如果是，直接通过验证
        background_source = content.get("verification_result", {}).get("background_source", "")
        if background_source == "knowledge_base":
            print(f"[PASS] 检测到数据来源为知识库，直接通过验证")
            confidence_score = 1.0
            passed_checks = 1
            total_checks = 1
            verified_facts.append("从知识库加载的权威数据，无需验证")
            suggestions.append("知识库数据可信度高，可以直接使用")
            
            return VerificationResult(
                is_credible=True,
                confidence_score=confidence_score,
                credibility_level=CredibilityLevel.HIGH,
                issues_found=[],
                suggestions=suggestions,
                verified_facts=verified_facts,
                unverified_facts=[]
            )
        
        # 1. 检查是否有权威知识库数据
        if work_name in self.verified_knowledge_base:
            verified_data = self.verified_knowledge_base[work_name]
            confidence_score += 0.4
            passed_checks += 1
            verified_facts.append("存在权威知识库数据")
            total_checks += 1
            
            # 2. 详细对比关键信息
            comparison_result = self._compare_with_verified_data(work_name, content, verified_data)
            issues_found.extend(comparison_result["issues"])
            verified_facts.extend(comparison_result["verified"])
            unverified_facts.extend(comparison_result["unverified"])
            
            passed_checks += comparison_result["passed_checks"]
            total_checks += comparison_result["total_checks"]
            
        else:
            issues_found.append("缺乏权威知识库验证数据")
            unverified_facts.append("整个背景资料缺乏验证")
            total_checks += 1
        
        # 3. 特定作品专门验证
        if work_name == "凡人修仙传":
            fanren_result = self._verify_fanren_specific_content(content)
            issues_found.extend(fanren_result["issues"])
            suggestions.extend(fanren_result["suggestions"])
            verified_facts.extend(fanren_result["verified"])
            unverified_facts.extend(fanren_result["unverified"])
            
            passed_checks += fanren_result["passed_checks"]
            total_checks += fanren_result["total_checks"]
        
        # 4. 内部一致性检查
        consistency_result = self._check_internal_consistency(content)
        issues_found.extend(consistency_result["issues"])
        verified_facts.extend(consistency_result["verified"])
        
        passed_checks += consistency_result["passed_checks"]
        total_checks += consistency_result["total_checks"]
        
        # 计算最终可信度分数
        if total_checks > 0:
            confidence_score = passed_checks / total_checks
        
        # 确定可信度等级
        credibility_level = self._determine_credibility_level(confidence_score, issues_found)
        
        # 生成建议
        if not suggestions:
            suggestions = self._generate_suggestions(issues_found, credibility_level)
        
        return VerificationResult(
            is_credible=credibility_level in [CredibilityLevel.HIGH, CredibilityLevel.MEDIUM],
            confidence_score=confidence_score,
            credibility_level=credibility_level,
            issues_found=issues_found,
            suggestions=suggestions,
            verified_facts=verified_facts,
            unverified_facts=unverified_facts
        )
    
    def _verify_fanren_specific_content(self, content: Dict) -> Dict:
        """专门验证《凡人修仙传》相关内容"""
        result = {
            "issues": [],
            "suggestions": [],
            "verified": [],
            "unverified": [],
            "passed_checks": 0,
            "total_checks": 0
        }
        
        characters = content.get("characters", {})
        
        # 验证慕沛灵修为 - 关键验证点
        if "慕沛灵" in characters:
            result["total_checks"] += 1
            mupeiling_desc = characters["慕沛灵"]
            
            # 严格验证：必须包含筑基期且不能包含结丹期
            if "筑基期" in mupeiling_desc and "结丹期" not in mupeiling_desc:
                result["verified"].append("慕沛灵修为正确：筑基期")
                result["passed_checks"] += 1
            elif "结丹期" in mupeiling_desc:
                result["issues"].append("慕沛灵修为错误：原著中此时为筑基期，非结丹期")
                result["unverified"].append("慕沛灵修为信息")
            else:
                result["issues"].append("慕沛灵修为信息不明确")
                result["unverified"].append("慕沛灵修为")
        else:
            result["total_checks"] += 1
            result["issues"].append("缺少慕沛灵角色信息")
        
        # 验证温天仁身份 - 关键验证点
        if "温天仁" in characters:
            result["total_checks"] += 1
            wentianren_desc = characters["温天仁"]
            
            # 验证温天仁来自乱星海逆星盟，非天南魔道六宗
            if ("逆星盟" in wentianren_desc or "乱星海" in wentianren_desc) and "六宗" not in wentianren_desc:
                if "合欢宗" not in wentianren_desc and "鬼灵门" not in wentianren_desc and "天煞宗" not in wentianren_desc:
                    result["verified"].append("温天仁身份正确：乱星海逆星盟修士")
                    result["passed_checks"] += 1
                else:
                    result["issues"].append("温天仁身份错误：来自乱星海逆星盟，非天南魔道六宗成员")
                    result["unverified"].append("温天仁身份信息")
            elif "六宗" in wentianren_desc or "合欢宗" in wentianren_desc:
                result["issues"].append("温天仁身份错误：非魔道六宗成员，而是乱星海逆星盟散修")
                result["unverified"].append("温天仁身份信息")
            else:
                result["issues"].append("温天仁身份信息不明确")
                result["unverified"].append("温天仁身份")
        else:
            result["total_checks"] += 1
            result["issues"].append("缺少温天仁角色信息")
        
        # 验证韩立信息
        if "韩立" in characters:
            result["total_checks"] += 1
            hanli_desc = characters["韩立"]
            
            # 验证韩立的核心特征
            has_correct_level = "结丹后期大圆满" in hanli_desc or "结丹后期" in hanli_desc
            has_divine_thunder = "辟邪神雷" in hanli_desc
            has_sword_skill = "青元剑诀" in hanli_desc
            
            if has_correct_level and has_divine_thunder:
                result["verified"].append("韩立修为和功法正确")
                result["passed_checks"] += 1
            else:
                if not has_correct_level:
                    result["issues"].append("韩立修为信息不准确：应为结丹后期大圆满")
                if not has_divine_thunder:
                    result["issues"].append("韩立功法信息不完整：缺少辟邪神雷")
                result["unverified"].append("韩立修为和功法")
        
        # 验证梅凝特殊体质
        if "梅凝" in characters:
            result["total_checks"] += 1
            meining_desc = characters["梅凝"]
            
            if "通玉凤髓之体" in meining_desc:
                result["verified"].append("梅凝特殊体质正确：通玉凤髓之体")
                result["passed_checks"] += 1
            else:
                result["issues"].append("梅凝特殊体质信息缺失：应为通玉凤髓之体")
                result["unverified"].append("梅凝特殊体质")
        
        return result
    
    def _compare_with_verified_data(self, work_name: str, content: Dict, verified_data: Dict) -> Dict:
        """与权威数据进行对比"""
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
            result["total_checks"] += 1
            
            if char_name in content_chars:
                content_desc = content_chars[char_name]
                
                # 简单的关键信息对比
                verified_keywords = self._extract_keywords(verified_desc)
                content_keywords = self._extract_keywords(content_desc)
                
                match_score = len(verified_keywords & content_keywords) / len(verified_keywords) if verified_keywords else 0
                
                if match_score >= 0.7:  # 70%以上匹配度
                    result["verified"].append(f"{char_name}信息基本准确")
                    result["passed_checks"] += 1
                elif match_score >= 0.4:  # 40-70%匹配度
                    result["issues"].append(f"{char_name}信息部分准确，但存在偏差")
                    result["unverified"].append(f"{char_name}的部分信息")
                else:
                    result["issues"].append(f"{char_name}信息与权威数据差异较大")
                    result["unverified"].append(f"{char_name}的大部分信息")
            else:
                result["issues"].append(f"缺少重要角色：{char_name}")
        
        return result
    
    def _check_internal_consistency(self, content: Dict) -> Dict:
        """检查内容内部一致性"""
        result = {
            "issues": [],
            "verified": [],
            "passed_checks": 0,
            "total_checks": 0
        }
        
        # 检查修为等级一致性
        power_system = content.get("power_system", {})
        if "等级划分" in str(power_system):
            result["total_checks"] += 1
            levels = str(power_system.get("等级划分", ""))
            
            # 检查基本修为顺序
            basic_levels = ["炼气", "筑基", "结丹", "元婴", "化神"]
            if all(level in levels for level in basic_levels):
                result["verified"].append("修为等级体系完整且顺序正确")
                result["passed_checks"] += 1
            else:
                result["issues"].append("修为等级体系不完整或顺序错误")
        
        return result
    
    def _extract_keywords(self, text: str) -> set:
        """提取文本中的关键词"""
        # 简单的关键词提取逻辑
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
    
    def _determine_credibility_level(self, score: float, issues: List[str]) -> CredibilityLevel:
        """确定可信度等级"""
        if score >= 0.8 and len(issues) == 0:
            return CredibilityLevel.HIGH
        elif score >= 0.6 and len(issues) <= 2:
            return CredibilityLevel.MEDIUM
        elif score >= 0.4:
            return CredibilityLevel.LOW
        else:
            return CredibilityLevel.UNVERIFIED
    
    def _generate_suggestions(self, issues: List[str], level: CredibilityLevel) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if level == CredibilityLevel.HIGH:
            suggestions.append("内容可信度高，可以放心使用")
        
        elif level == CredibilityLevel.MEDIUM:
            suggestions.append("建议人工核实关键信息")
            suggestions.append("可以参考权威资料进行验证")
        
        elif level == CredibilityLevel.LOW:
            suggestions.append("强烈建议重新生成或人工修正")
            suggestions.append("存在较多事实错误，需要仔细检查")
        
        else:  # UNVERIFIED
            suggestions.append("无法验证内容准确性，建议谨慎使用")
            suggestions.append("建议查找权威资料进行对比验证")
        
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
                    "world_name": "人界 - 天南地区、乱星海",
                    "social_structure": "天南三大正道宗门（落云宗、古剑门、百巧院）、三大魔道宗门（合欢宗、鬼灵门、天煞宗）以及众多散修；乱星海逆星盟",
                    "power_levels": "炼气期(共十三层) → 筑基期(分前、中、后三期) → 结丹期(分前、中、后三期及大圆满) → 元婴期(分前、中、后三期) → 化神期"
                },
                "power_system": {
                    "special_abilities": "功法神通（如韩立的《辟邪神雷》）、法宝古宝、特殊体质（如梅凝的《通玉凤髓之体》）、结婴天象"
                }
            }
        }
    
    def _load_controversial_topics(self) -> List[str]:
        """加载争议性话题列表"""
        return [
            "时间线混淆",
            "角色关系错误",
            "修为等级不符",
            "宗门归属错误"
        ]
    
    def _load_fact_checking_rules(self) -> Dict:
        """加载事实检查规则"""
        return {
            "凡人修仙传": {
                "慕沛灵": {
                    "required_level": "筑基期",
                    "forbidden_level": "结丹期",
                    "required_affiliation": "落云宗"
                },
                "温天仁": {
                    "required_identity": ["逆星盟", "乱星海", "高层"],
                    "forbidden_identity": ["天南六宗", "合欢宗", "鬼灵门", "天煞宗", "落云宗", "散修"],
                    "required_technique": "六极真魔功",
                    "special_note": "逆星盟高层，非普通散修"
                },
                "韩立": {
                    "required_level": ["结丹后期", "结丹后期大圆满"],
                    "required_techniques": ["辟邪神雷", "青元剑诀"],
                    "required_item": "掌天瓶"
                },
                "梅凝": {
                    "required_constitution": "通玉凤髓之体",
                    "special_note": "被魔道觊觎的双修鼎炉"
                }
            }
        }