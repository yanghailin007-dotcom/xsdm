#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的Mock API客户端
支持精确的字段级背景资料修正
"""

import json
from typing import Optional, Dict, Any


class ImprovedMockAPIClient:
    """改进的Mock API客户端，支持精确的字段级修正"""
    
    def __init__(self):
        # 模拟不同场景的响应
        self.scenario_responses = {
            "extract_original_work_background": {
                "initial_response": {
                    "worldview": {
                        "世界名称": "凡人修仙世界",
                        "时代背景": "修仙时代，实力为尊的丛林法则世界",
                        "社会结构": "修仙门派林立，正道魔道并存"
                    },
                    "characters": {
                        "韩立": "原著主角，结丹后期修士，修炼辟邪神雷",
                        "慕沛灵": "落云宗女修，结丹期修为",  # 错误：应该是筑基期
                        "梅凝": "拥有特殊体质的女修",
                        "温天仁": "合欢宗少主，结丹期修士"  # 错误：应该是逆星盟
                    },
                    "power_system": {
                        "体系名称": "凡人修仙体系",
                        "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                        "特殊能力": "各种功法神通、法宝、特殊体质"
                    }
                }
            },
            "targeted_background_correction": {
                # 针对精确修正的响应
                "correction_response": {
                    "worldview": {
                        "世界名称": "凡人修仙世界",
                        "时代背景": "修仙时代，实力为尊的丛林法则世界",
                        "社会结构": "修仙门派林立，正道魔道并存"
                    },
                    "characters": {
                        "韩立": "原著主角，结丹后期修士，修炼辟邪神雷",
                        "慕沛灵": "落云宗筑基期女修，容貌绝美，资质出众",  # 修正：筑基期
                        "梅凝": "拥有通玉凤髓之体的特殊体质女修",
                        "温天仁": "乱星海逆星盟修士，结丹期修士，修炼六极真魔功"  # 修正：逆星盟
                    },
                    "power_system": {
                        "体系名称": "凡人修仙体系",
                        "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                        "特殊能力": "各种功法神通、法宝、特殊体质"
                    }
                }
            }
        }
    
    def call_api(self, function_name: str, prompt: str, creativity: float, purpose: str) -> Optional[str]:
        """
        模拟API调用，支持精确的字段级修正
        
        Args:
            function_name: 功能名称
            prompt: 提示词
            creativity: 创造性参数
            purpose: 调用目的
            
        Returns:
            API响应结果
        """
        print(f"    [MOCK API] 调用功能: {function_name}")
        print(f"    [MOCK API] 目的: {purpose}")
        print(f"    [MOCK API] 创造性: {creativity}")
        
        # 分析提示词以确定响应类型
        if "精确的字段级修正" in prompt or "targeted" in function_name.lower():
            return self._handle_targeted_correction(prompt)
        elif "extract_original_work_background" in function_name:
            return self._handle_background_extraction(prompt)
        else:
            return self._handle_default_response(prompt)
    
    def _handle_targeted_correction(self, prompt: str) -> str:
        """处理精确的字段级修正请求，返回补丁而非完整JSON"""
        print("    [MOCK API] 执行精确字段级修正...")
        
        # 构建补丁响应，只包含需要修改的字段
        patch_response = {}
        
        # 根据提示词动态生成补丁
        if "慕沛灵" in prompt and ("筑基期" in prompt or "结丹长老" in prompt):
            if "characters" not in patch_response:
                patch_response["characters"] = {}
            patch_response["characters"]["慕沛灵"] = "落云宗筑基期女修，容貌绝美，资质出众，因修炼媚术功法遭反噬，命悬一线，被宗门元婴老怪觊觎"
            print("    [MOCK API] 生成补丁：修正慕沛灵为筑基期")
        
        if "温天仁" in prompt and ("逆星盟" in prompt or "乱星海" in prompt):
            if "characters" not in patch_response:
                patch_response["characters"] = {}
            patch_response["characters"]["温天仁"] = "乱星海逆星盟的著名散修，结丹期大圆满修为，修炼魔道奇功《六极真魔功》，实力强横，心性狠辣，为夺取梅凝的'通玉凤髓之体'不择手段"
            print("    [MOCK API] 生成补丁：修正温天仁为逆星盟散修")
        
        if "梅凝" in prompt and ("通玉凤髓之体" in prompt or "特殊体质" in prompt):
            if "characters" not in patch_response:
                patch_response["characters"] = {}
            patch_response["characters"]["梅凝"] = "来自乱星海的散修，拥有极其罕见的'通玉凤髓之体'，是顶级炉鼎体质，因此被温天仁追杀。她外柔内刚，心地善良，性格坚韧"
            print("    [MOCK API] 生成补丁：修正梅凝添加通玉凤髓之体")
        
        # 如果没有需要修正的字段，返回空补丁
        if not patch_response:
            print("    [MOCK API] 无需修正，返回空补丁")
            return "{}"
        
        return json.dumps(patch_response, ensure_ascii=False, indent=2)
    
    def _handle_background_extraction(self, prompt: str) -> str:
        """处理背景资料提取请求"""
        print("    [MOCK API] 提取背景资料...")
        
        # 返回包含一些错误的初始背景资料
        initial_response = self.scenario_responses["extract_original_work_background"]["initial_response"].copy()
        
        return json.dumps(initial_response, ensure_ascii=False, indent=2)
    
    def _handle_default_response(self, prompt: str) -> str:
        """处理默认请求"""
        print("    [MOCK API] 处理默认请求...")
        
        default_response = {
            "worldview": {
                "世界名称": "未知世界",
                "时代背景": "未知时代背景",
                "社会结构": "未知社会结构"
            },
            "characters": {
                "未知角色": "未知角色描述"
            },
            "power_system": {
                "体系名称": "未知体系",
                "等级划分": "未知等级划分",
                "特殊能力": "未知特殊能力"
            }
        }
        
        return json.dumps(default_response, ensure_ascii=False, indent=2)


class MockAPIClientWithCorrectionScenarios:
    """支持多种修正场景的Mock API客户端"""
    
    def __init__(self):
        self.scenarios = {
            "success_on_first_try": self._success_on_first_try,
            "needs_one_correction": self._needs_one_correction,
            "needs_multiple_corrections": self._needs_multiple_corrections,
            "partial_correction": self._partial_correction,
            "format_error_recovery": self._format_error_recovery
        }
        self.current_scenario = "success_on_first_try"
        self.call_count = 0
    
    def set_scenario(self, scenario_name: str):
        """设置测试场景"""
        if scenario_name in self.scenarios:
            self.current_scenario = scenario_name
            self.call_count = 0
            print(f"    [MOCK API] 设置场景: {scenario_name}")
        else:
            print(f"    [MOCK API] 未知场景: {scenario_name}")
    
    def call_api(self, function_name: str, prompt: str, creativity: float, purpose: str) -> Optional[str]:
        """根据当前场景调用相应的处理方法"""
        self.call_count += 1
        print(f"    [MOCK API] 第{self.call_count}次调用 - 场景: {self.current_scenario}")
        
        scenario_handler = self.scenarios.get(self.current_scenario, self._default_scenario)
        return scenario_handler(function_name, prompt, creativity, purpose)
    
    def _success_on_first_try(self, function_name: str, prompt: str, creativity: float, purpose: str) -> str:
        """场景：第一次就成功"""
        if "extract_original_work_background" in function_name:
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹后期大圆满修士，修炼《青元剑诀》和《辟邪神雷》，身怀掌天瓶",
                    "慕沛灵": "落云宗筑基期女修，容貌绝美，资质出众。因家族逼迫和宗门内元婴长老觊觎而深陷困境",
                    "梅凝": "拥有极其罕见的'通玉凤髓之体'的特殊体质女子，是绝佳的双修鼎炉",
                    "温天仁": "乱星海逆星盟修士，结丹后期大圆满修士，修炼《六极真魔功》"
                },
                "power_system": {
                    "体系名称": "凡人流修仙体系",
                    "等级划分": "炼气期(共十三层) → 筑基期(分前、中、后三期) → 结丹期(分前、中、后三期及大圆满) → 元婴期(分前、中、后三期) → 化神期",
                    "特殊能力": "功法神通、法宝古宝、特殊体质、结婴天象"
                }
            }, ensure_ascii=False, indent=2)
        
        return "{}"
    
    def _needs_one_correction(self, function_name: str, prompt: str, creativity: float, purpose: str) -> str:
        """场景：需要一次修正"""
        if self.call_count == 1:
            # 第一次返回有错误的背景资料
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹后期修士，修炼辟邪神雷",
                    "慕沛灵": "落云宗女修，结丹期修为",  # 错误：应该是筑基期
                    "梅凝": "拥有特殊体质的女修",
                    "温天仁": "合欢宗少主，结丹期修士"  # 错误：应该是逆星盟
                },
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通、法宝、特殊体质"
                }
            }, ensure_ascii=False, indent=2)
        else:
            # 第二次返回修正后的背景资料
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹后期修士，修炼辟邪神雷",
                    "慕沛灵": "落云宗筑基期女修，容貌绝美，资质出众",  # 修正
                    "梅凝": "拥有通玉凤髓之体的特殊体质女修",
                    "温天仁": "乱星海逆星盟修士，结丹期修士，修炼六极真魔功"  # 修正
                },
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通、法宝、特殊体质"
                }
            }, ensure_ascii=False, indent=2)
    
    def _needs_multiple_corrections(self, function_name: str, prompt: str, creativity: float, purpose: str) -> str:
        """场景：需要多次修正"""
        if self.call_count == 1:
            # 第一次返回多个错误的背景资料
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹期修士",  # 缺少详细信息
                    "慕沛灵": "落云宗女修，结丹期修为",  # 错误修为
                    "梅凝": "普通女修",  # 缺少特殊体质
                    "温天仁": "合欢宗少主"  # 错误身份
                },
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通"
                }
            }, ensure_ascii=False, indent=2)
        elif self.call_count == 2:
            # 第二次修正部分错误
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹后期大圆满修士，修炼《青元剑诀》和《辟邪神雷》",
                    "慕沛灵": "落云宗筑基期女修，容貌绝美，资质出众",  # 修正
                    "梅凝": "拥有特殊体质的女修",  # 仍然不够准确
                    "温天仁": "乱星海修士，结丹期修士"  # 修正了身份但缺少细节
                },
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通、法宝、特殊体质"
                }
            }, ensure_ascii=False, indent=2)
        else:
            # 第三次完全修正
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹后期大圆满修士，修炼《青元剑诀》和《辟邪神雷》，身怀掌天瓶",
                    "慕沛灵": "落云宗筑基期女修，容貌绝美，资质出众。因家族逼迫和宗门内元婴长老觊觎而深陷困境",
                    "梅凝": "拥有极其罕见的'通玉凤髓之体'的特殊体质女子，是绝佳的双修鼎炉",
                    "温天仁": "乱星海逆星盟修士，结丹后期大圆满修士，修炼《六极真魔功》。与韩立有私人恩怨"
                },
                "power_system": {
                    "体系名称": "凡人流修仙体系",
                    "等级划分": "炼气期(共十三层) → 筑基期(分前、中、后三期) → 结丹期(分前、中、后三期及大圆满) → 元婴期(分前、中、后三期) → 化神期",
                    "特殊能力": "功法神通、法宝古宝、特殊体质、结婴天象"
                }
            }, ensure_ascii=False, indent=2)
    
    def _partial_correction(self, function_name: str, prompt: str, creativity: float, purpose: str) -> str:
        """场景：部分修正，仍有问题"""
        if self.call_count == 1:
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹后期修士，修炼辟邪神雷",
                    "慕沛灵": "落云宗女修，结丹期修为",  # 错误
                    "梅凝": "拥有特殊体质的女修",
                    "温天仁": "合欢宗少主，结丹期修士"  # 错误
                },
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通、法宝、特殊体质"
                }
            }, ensure_ascii=False, indent=2)
        else:
            # 修正了部分问题，但仍有遗留
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹后期修士，修炼辟邪神雷",
                    "慕沛灵": "落云宗筑基期女修，容貌绝美",  # 修正了修为
                    "梅凝": "拥有特殊体质的女修",  # 仍然不够具体
                    "温天仁": "乱星海逆星盟修士，结丹期修士"  # 修正了身份
                },
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通、法宝、特殊体质"
                }
            }, ensure_ascii=False, indent=2)
    
    def _format_error_recovery(self, function_name: str, prompt: str, creativity: float, purpose: str) -> str:
        """场景：格式错误恢复"""
        if self.call_count == 1:
            # 返回错误格式的响应
            return json.dumps({
                "title": "凡人修仙传同人小说",
                "synopsis": "这是一个同人小说",
                "opening_scene": {
                    "title": "第一章",
                    "content": "开头内容"
                },
                "core_background": {
                    "characters": [
                        {
                            "name": "韩立",
                            "cultivation": "结丹后期",
                            "identity": "原著主角"
                        },
                        {
                            "name": "慕沛灵",
                            "cultivation": "筑基期",
                            "identity": "落云宗女修"
                        }
                    ]
                }
            }, ensure_ascii=False, indent=2)
        else:
            # 返回修正后的标准格式
            return json.dumps({
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，结丹后期修士，修炼辟邪神雷",
                    "慕沛灵": "落云宗筑基期女修，容貌绝美，资质出众"
                },
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通、法宝、特殊体质"
                }
            }, ensure_ascii=False, indent=2)
    
    def _default_scenario(self, function_name: str, prompt: str, creativity: float, purpose: str) -> str:
        """默认场景"""
        return "{}"