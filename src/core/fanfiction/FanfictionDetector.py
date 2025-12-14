"""
同人小说检测器
负责检测文本是否为同人小说并提取原著名称，获取背景资料并进行可信度验证
"""

import re
import json
import os
from typing import Tuple, Dict, Optional


class FanfictionDetector:
    """同人小说检测器"""
    
    def __init__(self, api_client=None):
        # 同人小说关键词检测
        self.fanfiction_keywords = [
            "同人", "穿越", "重生", "异世界", "穿越到", "来到了", "进入了",
            "动漫", "小说", "游戏", "电影", "电视剧", "原著",
            "哈利波特", "火影", "海贼王", "死神", "斗罗", "遮天", "凡人修仙传",
            "盗墓笔记", "全职高手", "魔道祖师", "天官赐福", "陈情令"
        ]
        
        # 作品名标准化映射
        self.name_normalizations = {
            "凡人修仙": "凡人修仙传",
            "凡人": "凡人修仙传",
            "斗罗": "斗罗大陆",
            "火影": "火影忍者",
            "海贼": "海贼王",
            "死神": "死神",
            "魔道": "魔道祖师",
            "陈情": "陈情令",
            "天官": "天官赐福",
            "盗墓": "盗墓笔记",
            "全职": "全职高手",
            "知否": "知否知否应是绿肥红瘦",
            "琅琊": "琅琊榜",
            "甄嬛": "甄嬛传",
            "雪中": "雪中悍刀行",
            "雪中悍刀": "雪中悍刀行"
        }
        
        # API客户端（用于获取背景资料）
        self.api_client = api_client
        
        # 预定义的常见作品背景资料
        self.background_database = {
            "凡人修仙传": {
                "worldview": {
                    "世界名称": "人界 - 天南地区、乱星海",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界。修仙资源稀缺，修士之间为了功法、丹药、法宝等资源不惜生死相搏",
                    "社会结构": "天南地区：三大正道宗门（落云宗、古剑门、百巧院）、三大魔道宗门（合欢宗、鬼灵门、天煞宗）以及众多散修；乱星海：逆星盟等势力",
                    "地理划分": "天南地区、乱星海、大晋等其他区域"
                },
                "characters": {
                    "韩立": "原著主角，人称'韩老魔'。结丹后期大圆满修士，相貌平平但心智坚韧。修炼《青元剑诀》和《辟邪神雷》，身怀掌天瓶能催熟灵药。与温天仁有私人恩怨",
                    "慕沛灵": "落云宗筑基期女修（关键信息：此时为筑基期，非结丹期），容貌绝美，资质出众。因家族逼迫和宗门内元婴长老觊觎而深陷困境，性格外冷内热",
                    "梅凝": "拥有极其罕见的'通玉凤髓之体'的特殊体质女子，是绝佳的双修鼎炉，因此被魔道修士觊觎。心地善良，性格坚韧，与兄长梅真人相依为命",
                    "温天仁": "乱星海逆星盟高层修士，结丹后期大圆满修士，修炼《六极真魔功》。与韩立有私人恩怨（关键信息：来自乱星海逆星盟高层，非天南魔道六宗成员，非普通散修），心狠手辣，觊觎梅凝的特殊体质"
                },
                "power_system": {
                    "体系名称": "凡人流修仙体系",
                    "等级划分": "炼气期(共十三层) → 筑基期(分前、中、后三期) → 结丹期(分前、中、后三期及大圆满) → 元婴期(分前、中、后三期) → 化神期",
                    "特殊能力": "功法神通（如韩立的《辟邪神雷》、温天仁的《六极真魔功》）、法宝古宝、特殊体质（如梅凝的《通玉凤髓之体》）、结婴天象（突破元婴时引发的天地异象）",
                    "修炼资源": "灵石、丹药、法宝、功法玉简、灵药等"
                },
                "key_events": {
                    "韩立温天仁大战": "发生在乱星海的结丹期修士大战，韩立使用辟邪神雷对战温天仁的六极真魔功",
                    "阴冥之地": "神秘险地，韩立和梅凝等人曾卷入其中",
                    "暴风山": "阴冥之地中的高山，是脱困的关键地点"
                }
            }
        }

    def detect_fanfiction(self, creative_work: dict) -> Tuple[bool, str]:
        """
        检测是否为同人小说并提取原著名称
        
        Args:
            creative_work: 用户提供的创意作品信息
            
        Returns:
            Tuple[bool, str]: (是否为同人小说, 原著作品名称)
        """
        print("  检测是否为同人小说并提取原著背景资料...")
        
        # 提取所有文本内容进行检测
        combined_text = self._extract_combined_text(creative_work)
        
        # 检测同人小说特征
        is_fanfiction = self._check_fanfiction_keywords(combined_text)
        
        if not is_fanfiction:
            print("    未检测到同人小说特征，按原创作品处理")
            return False, ""
        
        print("    检测到同人小说特征，开始提取原著背景资料...")
        
        # 提取原著名称
        original_work_name = self._extract_original_work_name(combined_text)
        
        print(f"    原著: {original_work_name}")
        
        return True, original_work_name

    def _extract_combined_text(self, creative_work: dict) -> str:
        """提取创意作品中的所有文本内容"""
        core_setting = creative_work.get("coreSetting", "")
        core_selling_points = creative_work.get("coreSellingPoints", "")
        storyline = creative_work.get("completeStoryline", {})
        
        # 将故事线转换为文本
        storyline_text = ""
        if isinstance(storyline, dict):
            for stage_key, stage_data in storyline.items():
                if isinstance(stage_data, dict):
                    storyline_text += f"{stage_data.get('stageName', '')} {stage_data.get('summary', '')} "
        
        # 合并所有文本并转为小写
        return f"{core_setting} {core_selling_points} {storyline_text}".lower()

    def _check_fanfiction_keywords(self, text: str) -> bool:
        """检查文本中是否包含同人小说关键词"""
        return any(keyword in text for keyword in self.fanfiction_keywords)

    def _extract_original_work_name(self, text: str) -> str:
        """
        从文本中提取原著作品名称 - 精准匹配版本
        
        Args:
            text: 待分析的文本
            
        Returns:
            原著作品名称
        """
        # 1. 精准模式匹配：优先匹配明确的同人文表述
        precise_patterns = [
            r'([^，。！？\s]+)同人文',
            r'([^，。！？\s]+)同人',
            r'([^，。！？\s]+)同人小说',
            r'([^，。！？\s]+)衍生',
            r'([^，。！？\s]+)AU',
            r'《([^》]+)》同人文',
            r'《([^》]+)》同人',
            r'《([^》]+)》同人小说',
            r'《([^》]+)》衍生'
        ]
        
        for pattern in precise_patterns:
            matches = re.findall(pattern, text)
            if matches:
                work_name = matches[0].strip()
                # 标准化常见作品名
                work_name = self._normalize_work_name(work_name)
                if work_name != "未知原著":
                    print(f"    精准匹配到作品: {work_name}")
                    return work_name
        
        # 2. 引号中的书名匹配
        quoted_names = re.findall(r'《([^》]+)》', text)
        if quoted_names:
            work_name = self._normalize_work_name(quoted_names[0])
            if work_name != "未知原著":
                print(f"    引号匹配到作品: {work_name}")
                return work_name
        
        # 3. 场景模式匹配
        scene_patterns = [
            r'穿越到([^，。！？\s]+)',
            r'来到了([^，。！？\s]+)',
            r'进入了([^，。！？\s]+)',
            r'重生在([^，。！？\s]+)',
            r'转生到([^，。！？\s]+)',
            r'重生到([^，。！？\s]+)'
        ]
        
        for pattern in scene_patterns:
            matches = re.findall(pattern, text)
            if matches:
                work_name = self._normalize_work_name(matches[0])
                if work_name != "未知原著":
                    print(f"    场景匹配到作品: {work_name}")
                    return work_name
        
        return "未知原著"

    def _normalize_work_name(self, work_name: str) -> str:
        """
        标准化作品名称，处理常见的变体和简称
        
        Args:
            work_name: 原始作品名
            
        Returns:
            标准化后的作品名
        """
        # 移除常见的修饰词
        cleaned_name = re.sub(r'(小说|动漫|动画|漫画|电视剧|电影|网文|网文|原著|原作)$', '', work_name.strip())
        
        # 检查标准化映射
        for key, standard_name in self.name_normalizations.items():
            if key in cleaned_name:
                return standard_name
        
        # 如果包含标准名，直接返回
        for standard_name in self.name_normalizations.values():
            if standard_name in cleaned_name or cleaned_name in standard_name:
                return standard_name
        
        # 返回清理后的名称
        return cleaned_name if cleaned_name else "未知原著"

    def get_fanfiction_type(self, text: str) -> str:
        """
        获取同人小说类型
        
        Args:
            text: 文本内容
            
        Returns:
            同人类型（如"动漫衍生"、"男频衍生"等）
        """
        has_dongman = any(keyword in text for keyword in ["动漫", "动画", "漫画"])
        has_tongren = "同人" in text
        
        if has_tongren:
            if has_dongman:
                return "动漫衍生"
            else:
                return "男频衍生"
        
        return "未知类型"

    def get_original_work_background(self, work_name: str, creative_work: Optional[dict] = None, content_verifier=None) -> Dict:
        """
        获取原著背景资料并进行可信度验证
        
        Args:
            work_name: 原著作品名称
            creative_work: 用户的创意作品信息
            content_verifier: 内容验证器实例
            
        Returns:
            Dict: 原著背景资料 + 验证结果
        """
        print(f"    获取《{work_name}》背景资料并进行可信度验证...")
        
        background_info = None
        background_source = None
        
        # 1. 首先尝试从知识库文件加载已保存的背景资料
        background_info = self._load_from_knowledge_base(work_name)
        if background_info:
            background_source = "knowledge_base"
            print(f"    [SUCCESS] 从知识库加载背景资料成功")
        else:
            print(f"    [FAILED] 从知识库加载背景资料失败")
            
            # 2. 知识库加载失败，尝试通过AI获取
            if self.api_client:
                print(f"    [AI] 开始通过AI获取《{work_name}》背景资料...")
                background_info = self._fetch_via_ai(work_name, creative_work)
                if background_info:
                    background_source = "ai_generated"
                    print(f"    [SUCCESS] AI成功获取《{work_name}》背景资料")
                else:
                    print(f"    [FAILED] AI获取《{work_name}》背景资料失败")
            else:
                print(f"    [WARNING] 未配置API客户端，无法通过AI获取背景资料")
            
            # 3. 如果AI也失败，使用预定义资料
            if not background_info:
                if work_name in self.background_database:
                    background_info = self.background_database[work_name].copy()
                    background_source = "predefined"
                    print(f"    [DATABASE] 使用预定义的《{work_name}》背景资料")
                else:
                    # 4. 如果预定义资料也没有，使用基础结构
                    background_info = self._get_basic_background(work_name)
                    background_source = "basic"
                    print(f"    [BASIC] 使用基础背景资料结构")
        
        # 5. 整合用户创意设定
        if creative_work and background_info:
            background_info = self._merge_creative_setting(background_info, creative_work)
            print(f"    [SUCCESS] 成功整合用户创意设定到背景资料")
        
        # 6. 进行可信度验证（对所有来源的背景资料）
        verification_result = None
        if content_verifier and background_info:
            print(f"    开始进行背景资料可信度验证...")
            
            # 确保背景资料中包含来源信息，以便验证器识别
            if "verification_result" not in background_info:
                background_info["verification_result"] = {
                    "background_source": background_source or "unknown",
                    "note": f"数据来源: {background_source or 'unknown'}"
                }
            else:
                background_info["verification_result"]["background_source"] = background_source or "unknown"
            
            verification_result = content_verifier.verify_original_work_background(work_name, background_info)
            
            # 7. 如果可信度不足且配置了API客户端，尝试通过AI重新获取和修正
            if not verification_result.is_credible and self.api_client:
                print(f"    [WARNING] 背景资料可信度不足，尝试通过AI重新获取...")
                print(f"    置信度: {verification_result.confidence_score:.2f}")
                print(f"    发现问题: {len(verification_result.issues_found)}个")
                
                # 输出具体问题详情
                if verification_result.issues_found:
                    print(f"    具体问题:")
                    for i, issue in enumerate(verification_result.issues_found, 1):
                        print(f"      {i}. {issue}")
                
                # 输出改进建议
                if verification_result.suggestions:
                    print(f"    改进建议:")
                    for i, suggestion in enumerate(verification_result.suggestions, 1):
                        print(f"      {i}. {suggestion}")
                
                # 通过AI重新获取背景资料
                retry_count = 0
                max_retries = 2
                
                while retry_count < max_retries and not verification_result.is_credible:
                    retry_count += 1
                    print(f"    [RETRY] 第{retry_count}次通过AI重新获取背景资料...")
                    
                    # 使用验证结果改进提示词
                    improved_background = self._fetch_with_verification_feedback(
                        work_name, creative_work, verification_result
                    )
                    
                    if improved_background:
                        background_info = improved_background
                        background_source = "ai_improved"
                        if creative_work:
                            background_info = self._merge_creative_setting(background_info, creative_work)
                        
                        # 重新验证
                        print(f"    [REVERIFY] 重新验证第{retry_count}次修正后的背景资料...")
                        verification_result = content_verifier.verify_original_work_background(work_name, background_info)
                        
                        if verification_result.is_credible:
                            print(f"    [SUCCESS] AI重新获取后验证通过！")
                            print(f"    修正后置信度: {verification_result.confidence_score:.2f}")
                            break
                        else:
                            print(f"    [WARNING] 第{retry_count}次AI重新获取后仍未通过验证")
                            print(f"    当前置信度: {verification_result.confidence_score:.2f}")
                            print(f"    剩余问题: {len(verification_result.issues_found)}个")
                    else:
                        print(f"    [FAILED] 第{retry_count}次AI重新获取失败")
        
        # 8. 添加验证结果到背景资料中
        if verification_result:
            background_info["verification_result"] = {
                "is_credible": verification_result.is_credible,
                "confidence_score": verification_result.confidence_score,
                "credibility_level": verification_result.credibility_level.value,
                "issues_found": verification_result.issues_found,
                "suggestions": verification_result.suggestions,
                "verified_facts": verification_result.verified_facts,
                "unverified_facts": verification_result.unverified_facts,
                "background_source": background_source,
                "note": f"数据来源: {background_source}，已通过内容验证"
            }
            
            # 输出验证结果摘要
            print(f"    验证结果摘要:")
            print(f"       可信度: {'通过' if verification_result.is_credible else '未通过'}")
            print(f"       置信度: {verification_result.confidence_score:.2f}")
            print(f"       等级: {verification_result.credibility_level.value}")
            print(f"       数据来源: {background_source}")
            if verification_result.issues_found:
                print(f"       问题数量: {len(verification_result.issues_found)}个")
            print(f"       已验证事实: {len(verification_result.verified_facts)}个")
            print(f"       未验证事实: {len(verification_result.unverified_facts)}个")
        else:
            # 如果没有验证器，添加基本信息
            background_info["verification_result"] = {
                "is_credible": background_source in ["knowledge_base", "predefined"],
                "confidence_score": 0.8 if background_source in ["knowledge_base", "predefined"] else 0.5,
                "credibility_level": "high" if background_source in ["knowledge_base", "predefined"] else "medium",
                "issues_found": [],
                "suggestions": ["建议人工核实关键信息"] if background_source not in ["knowledge_base", "predefined"] else [],
                "verified_facts": [f"来自{background_source}"] if background_source in ["knowledge_base", "predefined"] else [],
                "unverified_facts": [],
                "background_source": background_source,
                "note": f"数据来源: {background_source}，未进行详细验证"
            }
            
            print(f"    验证结果摘要:")
            print(f"       数据来源: {background_source}")
            print(f"       说明: 未进行详细内容验证")
        
        return background_info

    def _load_from_knowledge_base(self, work_name: str) -> Optional[Dict]:
        """从知识库文件加载背景资料"""
        # 如果是凡人修仙传，直接从simplified_knowledge_base.json读取
        if work_name == "凡人修仙传":
            knowledge_base_path = "knowledge_base/凡人修仙传/simplified_knowledge_base.json"
            try:
                if os.path.exists(knowledge_base_path):
                    with open(knowledge_base_path, 'r', encoding='utf-8') as f:
                        simplified_data = json.load(f)
                    
                    # 将simplified_knowledge_base的数据转换为标准格式
                    background_info = self._convert_simplified_to_standard_format(simplified_data)
                    print(f"    [SUCCESS] 从简化知识库加载《{work_name}》背景资料成功")
                    return background_info
                else:
                    print(f"    简化知识库文件不存在: {knowledge_base_path}")
            except Exception as e:
                print(f"    从简化知识库加载背景资料失败: {e}")
        
        # 对于其他作品，使用原来的路径
        knowledge_base_path = f"knowledge_base/{work_name}/original_work_background.json"
        try:
            if os.path.exists(knowledge_base_path):
                with open(knowledge_base_path, 'r', encoding='utf-8') as f:
                    background_info = json.load(f)
                print(f"    [SUCCESS] 从知识库加载《{work_name}》背景资料成功")
                return background_info
        except Exception as e:
            print(f"    从知识库加载背景资料失败: {e}")
        
        # 注意：不再在这里检查预定义资料，让主方法处理
        return None

    def _convert_simplified_to_standard_format(self, simplified_data: Dict) -> Dict:
        """
        将简化知识库数据转换为标准格式
        
        Args:
            simplified_data: 简化知识库数据
            
        Returns:
            标准格式的背景资料
        """
        try:
            # 创建标准格式的背景资料
            standard_format = {
                "worldview": {},
                "characters": {},
                "power_system": {}
            }
            
            # 转换世界观数据
            if "worldview" in simplified_data:
                worldview_data = simplified_data["worldview"]
                standard_format["worldview"] = {
                    "世界名称": worldview_data.get("世界名称", ""),
                    "时代背景": worldview_data.get("时代背景", ""),
                    "社会结构": worldview_data.get("社会结构", "")
                }
            
            # 转换角色数据
            if "characters" in simplified_data:
                characters_data = simplified_data["characters"]
                characters_dict = {}
                
                # 遍历所有角色，包括嵌套的模板角色
                for char_key, char_info in characters_data.items():
                    if isinstance(char_info, dict) and char_key != "模板角色":
                        # 如果是字典格式的角色信息
                        char_desc = self._build_character_description(char_info)
                        characters_dict[char_key] = char_desc
                    elif isinstance(char_info, str):
                        # 如果是字符串格式的角色信息
                        characters_dict[char_key] = char_info
                    elif char_key == "模板角色" and isinstance(char_info, dict):
                        # 处理模板角色
                        for template_name, template_info in char_info.items():
                            if isinstance(template_info, dict):
                                template_desc = self._build_character_description(template_info)
                                characters_dict[template_name] = template_desc
                            else:
                                characters_dict[template_name] = str(template_info)
                
                standard_format["characters"] = characters_dict
            
            # 转换修炼体系数据
            if "power_system" in simplified_data:
                power_data = simplified_data["power_system"]
                standard_format["power_system"] = {
                    "体系名称": power_data.get("体系名称", ""),
                    "等级划分": self._format_cultivation_realms(power_data.get("等级划分", {})),
                    "特殊能力": self._format_special_abilities(power_data.get("特殊能力", {}))
                }
            
            # 添加其他有用的信息
            if "sects_and_factions" in simplified_data:
                standard_format["sects_and_factions"] = simplified_data["sects_and_factions"]
            
            if "important_locations" in simplified_data:
                standard_format["important_locations"] = simplified_data["important_locations"]
            
            if "key_treasures" in simplified_data:
                standard_format["key_treasures"] = simplified_data["key_treasures"]
            
            return standard_format
            
        except Exception as e:
            print(f"    转换简化知识库格式时出错: {e}")
            # 如果转换失败，返回基础格式
            return {
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {
                    "韩立": "原著主角，身怀掌天瓶",
                    "南宫婉": "掩月宗长老，韩立道侣"
                },
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通、法宝、特殊体质"
                }
            }

    def _build_character_description(self, char_info: Dict) -> str:
        """构建角色描述字符串"""
        desc_parts = []
        
        # 添加身份
        if "身份" in char_info:
            desc_parts.append(char_info["身份"])
        
        # 添加称号
        if "称号" in char_info:
            desc_parts.append(f"称号：{char_info['称号']}")
        
        # 添加性格特点
        if "性格特点" in char_info:
            desc_parts.append(f"性格：{char_info['性格特点']}")
        
        # 添加修为
        if "修为" in char_info:
            desc_parts.append(f"修为：{char_info['修为']}")
        
        # 添加核心能力
        if "核心能力" in char_info:
            desc_parts.append(f"能力：{char_info['核心能力']}")
        
        # 添加特殊物品
        if "特殊物品" in char_info:
            desc_parts.append(f"物品：{char_info['特殊物品']}")
        
        # 添加功法
        if "功法" in char_info:
            desc_parts.append(f"功法：{char_info['功法']}")
        
        # 添加特殊体质
        if "特殊体质" in char_info:
            desc_parts.append(f"体质：{char_info['特殊体质']}")
        
        # 添加人际关系
        if "人际关系" in char_info:
            desc_parts.append(f"关系：{char_info['人际关系']}")
        
        # 添加类型
        if "类型" in char_info:
            desc_parts.append(f"类型：{char_info['类型']}")
        
        # 添加背景
        if "背景" in char_info:
            desc_parts.append(f"背景：{char_info['背景']}")
        
        # 添加处境
        if "处境" in char_info:
            desc_parts.append(f"处境：{char_info['处境']}")
        
        # 添加目标
        if "目标" in char_info:
            desc_parts.append(f"目标：{char_info['目标']}")
        
        return "，".join(desc_parts) if desc_parts else "未知角色信息"

    def _format_cultivation_realms(self, realms_data: Dict) -> str:
        """格式化修炼境界信息"""
        if isinstance(realms_data, dict):
            realm_descriptions = []
            for realm_name, realm_desc in realms_data.items():
                realm_descriptions.append(f"{realm_name}: {realm_desc}")
            return "；".join(realm_descriptions)
        else:
            return str(realms_data)

    def _format_special_abilities(self, abilities_data: Dict) -> str:
        """格式化特殊能力信息"""
        if isinstance(abilities_data, dict):
            ability_descriptions = []
            for ability_name, ability_desc in abilities_data.items():
                ability_descriptions.append(f"{ability_name}: {ability_desc}")
            return "；".join(ability_descriptions)
        else:
            return str(abilities_data)

    def _fetch_via_ai(self, work_name: str, creative_work: Optional[dict] = None) -> Optional[Dict]:
        """通过AI获取背景资料"""
        if not self.api_client:
            print(f"    未配置API客户端，无法通过AI获取背景资料")
            return None
        
        print(f"    通过AI获取《{work_name}》的背景资料...")
        
        # 构建包含用户创意信息的提示词
        creative_info = ""
        if creative_work:
            core_setting = creative_work.get("coreSetting", "")
            core_selling_points = creative_work.get("coreSellingPoints", "")
            storyline = creative_work.get("completeStoryline", {})
            
            creative_info = f"""

【用户创意设定信息】
核心设定: {core_setting}
核心卖点: {core_selling_points}
故事线: {str(storyline)}

请特别注意结合用户的创意设定，在提供原著背景的同时，也要考虑到用户创意中涉及的角色和设定。
"""
        
        prompt = f"""
请为作品《{work_name}》提供详细的背景资料，包括但不限于：

1. 世界观设定（地理、时代、社会结构等）
2. 主要角色（主角、重要配角、反派等）
3. 力量体系（修炼等级、特殊能力、规则等）{creative_info}

请以JSON格式返回，结构如下：
{{
    "worldview": {{
        "世界名称": "描述",
        "时代背景": "描述",
        "社会结构": "描述"
    }},
    "characters": {{
        "角色名": "简要描述",
        "角色名": "简要描述"
    }},
    "power_system": {{
        "体系名称": "描述",
        "等级划分": "描述",
        "特殊能力": "描述"
    }}
}}

如果无法识别该作品，请返回空字典。
"""
        
        try:
            result = self.api_client.call_api(
                "extract_original_work_background",
                prompt,
                0.5,  # 较低创造性，确保准确性
                purpose="提取原著背景资料"
            )
            
            if result:
                try:
                    # 尝试解析JSON
                    background_info = json.loads(result)
                    
                    # 验证JSON结构是否正确
                    if self._validate_background_json_structure(background_info):
                        print(f"    成功获取《{work_name}》背景资料")
                        return background_info
                    else:
                        print(f"    AI返回JSON结构不正确，尝试修复...")
                        # 尝试修复JSON结构
                        fixed_info = self._fix_json_structure(background_info)
                        if fixed_info:
                            print(f"    成功修复JSON结构")
                            return fixed_info
                        else:
                            print(f"    无法修复JSON结构，返回基础信息")
                            return self._get_basic_background(work_name)
                            
                except json.JSONDecodeError as e:
                    print(f"    AI返回格式不正确: {e}，尝试从文本提取...")
                    # 尝试从文本中提取JSON
                    extracted_json = self._extract_json_from_text(result)
                    if extracted_json:
                        print(f"    从文本中成功提取JSON")
                        return extracted_json
                    else:
                        print(f"    无法从文本中提取有效JSON，返回基础信息")
                        return self._get_basic_background(work_name)
            else:
                print(f"    AI无法获取《{work_name}》的背景资料")
                return None
                
        except Exception as e:
            print(f"    获取《{work_name}》背景资料时出错: {e}")
            return None

    def _get_basic_background(self, work_name: str) -> Dict:
        """获取基础背景信息结构"""
        return {
            "worldview": {
                "世界名称": f"《{work_name}》的世界观",
                "时代背景": "未知时代背景",
                "社会结构": "未知社会结构"
            },
            "characters": {
                "未知角色": f"《{work_name}》的角色"
            },
            "power_system": {
                "体系名称": f"《{work_name}》的力量体系",
                "等级划分": "未知等级划分",
                "特殊能力": "未知特殊能力"
            }
        }

    def _merge_creative_setting(self, background_info: dict, creative_work: dict) -> dict:
        """将用户的创意设定整合到背景资料中"""
        try:
            # 创建背景资料的副本以避免修改原数据
            merged_info = background_info.copy()
            
            # 添加用户创意设定部分
            user_creative_setting = {
                "小说标题": creative_work.get("novelTitle", "未命名"),
                "核心设定": creative_work.get("coreSetting", "未提供核心设定"),
                "核心卖点": creative_work.get("coreSellingPoints", "未提供核心卖点"),
                "故事线": creative_work.get("completeStoryline", {}),
            }
            
            # 如果原著背景中没有用户创意设定部分，则添加
            if "user_creative_setting" not in merged_info:
                merged_info["user_creative_setting"] = user_creative_setting
            
            print(f"    成功整合用户创意设定到背景资料")
            return merged_info
            
        except Exception as e:
            print(f"    整合用户创意设定时出错: {e}")
            return background_info

    def _fetch_with_verification_feedback(self, work_name: str, creative_work: Optional[dict], verification_result) -> Optional[Dict]:
        """根据验证结果反馈重新获取背景资料"""
        if not self.api_client:
            return None
        
        # 构建基于验证结果的改进提示词
        issues_feedback = ""
        if verification_result.issues_found:
            issues_feedback = f"\n【需要特别注意的问题】\n"
            for issue in verification_result.issues_found:
                issues_feedback += f"- {issue}\n"
        
        suggestions_feedback = ""
        if verification_result.suggestions:
            suggestions_feedback = f"\n【改进建议】\n"
            for suggestion in verification_result.suggestions:
                suggestions_feedback += f"- {suggestion}\n"
        
        creative_info = ""
        if creative_work:
            core_setting = creative_work.get("coreSetting", "")
            core_selling_points = creative_work.get("coreSellingPoints", "")
            creative_info = f"""
【用户创意设定】
核心设定: {core_setting}
核心卖点: {core_selling_points}
"""
        
        prompt = f"""
之前的背景资料获取存在问题，请根据以下反馈重新提供《{work_name}》的准确背景资料：

{issues_feedback}
{suggestions_feedback}

{creative_info}

请特别确保提供的信息准确无误，尤其是：
1. 角色的修为等级和身份归属要准确
2. 势力关系和地理位置要正确
3. 时间线和事件顺序要符合原著

请严格按照以下JSON格式返回准确的背景资料：
{{
    "worldview": {{
        "世界名称": "描述",
        "时代背景": "描述",
        "社会结构": "描述"
    }},
    "characters": {{
        "角色名": "简要描述",
        "角色名": "简要描述"
    }},
    "power_system": {{
        "体系名称": "描述",
        "等级划分": "描述",
        "特殊能力": "描述"
    }}
}}

注意：必须严格遵循上述JSON结构，不要添加其他字段或修改字段名称。
"""
        
        try:
            result = self.api_client.call_api(
                "improve_original_work_background",
                prompt,
                0.3,  # 更低创造性，确保准确性
                purpose="改进原著背景资料"
            )
            
            if result:
                try:
                    # 尝试解析JSON
                    background_info = json.loads(result)
                    
                    # 验证JSON结构是否正确
                    if self._validate_background_json_structure(background_info):
                        print(f"    成功改进《{work_name}》背景资料")
                        return background_info
                    else:
                        print(f"    改进后JSON结构不正确，缺少必要字段")
                        # 尝试修复JSON结构
                        fixed_info = self._fix_json_structure(background_info)
                        if fixed_info:
                            print(f"    成功修复JSON结构")
                            return fixed_info
                        else:
                            print(f"    无法修复JSON结构")
                            return None
                            
                except json.JSONDecodeError as e:
                    print(f"    改进后格式不正确: {e}")
                    # 尝试从文本中提取JSON
                    extracted_json = self._extract_json_from_text(result)
                    if extracted_json:
                        print(f"    从文本中成功提取JSON")
                        return extracted_json
                    else:
                        print(f"    无法从文本中提取有效JSON")
                        return None
            else:
                print(f"    改进背景资料失败")
                return None
                
        except Exception as e:
            print(f"    改进背景资料时出错: {e}")
            return None

    def _validate_background_json_structure(self, data: dict) -> bool:
        """验证背景资料JSON结构是否正确"""
        required_top_level_keys = ["worldview", "characters", "power_system"]
        
        # 检查顶级键是否存在
        for key in required_top_level_keys:
            if key not in data:
                return False
            if not isinstance(data[key], dict):
                return False
        
        # 检查worldview的必要字段
        worldview_keys = ["世界名称", "时代背景", "社会结构"]
        for key in worldview_keys:
            if key not in data["worldview"]:
                return False
        
        # 检查power_system的必要字段
        power_keys = ["体系名称", "等级划分", "特殊能力"]
        for key in power_keys:
            if key not in data["power_system"]:
                return False
        
        # characters可以是空的，但必须是字典
        if not isinstance(data["characters"], dict):
            return False
        
        return True

    def _fix_json_structure(self, data: dict) -> Optional[Dict]:
        """尝试修复JSON结构"""
        try:
            # 检查是否是错误格式的响应（包含title、synopsis等）
            if self._is_wrong_format_response(data):
                print("    检测到错误格式的响应，尝试转换...")
                return self._convert_wrong_format_to_standard(data)
            
            fixed_data = {}
            
            # 修复worldview
            if "worldview" in data and isinstance(data["worldview"], dict):
                fixed_data["worldview"] = {
                    "世界名称": data["worldview"].get("世界名称", "未知世界名称"),
                    "时代背景": data["worldview"].get("时代背景", "未知时代背景"),
                    "社会结构": data["worldview"].get("社会结构", "未知社会结构")
                }
            else:
                fixed_data["worldview"] = {
                    "世界名称": "未知世界名称",
                    "时代背景": "未知时代背景",
                    "社会结构": "未知社会结构"
                }
            
            # 修复characters
            if "characters" in data and isinstance(data["characters"], dict):
                fixed_data["characters"] = data["characters"]
            else:
                fixed_data["characters"] = {}
            
            # 修复power_system
            if "power_system" in data and isinstance(data["power_system"], dict):
                fixed_data["power_system"] = {
                    "体系名称": data["power_system"].get("体系名称", "未知体系"),
                    "等级划分": data["power_system"].get("等级划分", "未知等级"),
                    "特殊能力": data["power_system"].get("特殊能力", "未知能力")
                }
            else:
                fixed_data["power_system"] = {
                    "体系名称": "未知体系",
                    "等级划分": "未知等级",
                    "特殊能力": "未知能力"
                }
            
            return fixed_data
            
        except Exception as e:
            print(f"    修复JSON结构时出错: {e}")
            return None

    def _is_wrong_format_response(self, data: dict) -> bool:
        """检查是否是错误格式的响应"""
        wrong_format_indicators = ["title", "synopsis", "opening_scene", "core_background"]
        return any(indicator in data for indicator in wrong_format_indicators)

    def _convert_wrong_format_to_standard(self, data: dict) -> Optional[Dict]:
        """将错误格式的响应转换为标准格式"""
        try:
            converted_data = {
                "worldview": {
                    "世界名称": "凡人修仙世界",
                    "时代背景": "修仙时代，实力为尊的丛林法则世界",
                    "社会结构": "修仙门派林立，正道魔道并存"
                },
                "characters": {},
                "power_system": {
                    "体系名称": "凡人修仙体系",
                    "等级划分": "炼气期→筑基期→结丹期→元婴期→化神期",
                    "特殊能力": "各种功法神通、法宝、特殊体质"
                }
            }
            
            # 从core_background中提取角色信息
            if "core_background" in data and isinstance(data["core_background"], dict):
                characters_info = data["core_background"].get("characters", [])
                if isinstance(characters_info, list):
                    for char_info in characters_info:
                        if isinstance(char_info, dict) and "name" in char_info:
                            char_name = char_info["name"]
                            char_desc = f"修为: {char_info.get('cultivation', '未知')}, 身份: {char_info.get('identity', '未知')}"
                            converted_data["characters"][char_name] = char_desc
            
            # 如果没有找到角色信息，添加基本角色
            if not converted_data["characters"]:
                converted_data["characters"] = {
                    "韩立": "原著主角，结丹期大圆满修士，修炼辟邪神雷",
                    "慕沛灵": "落云宗女修，筑基期修为",
                    "梅凝": "拥有通玉凤髓之体的特殊体质女修",
                    "温天仁": "乱星海修士，修炼六极真魔功"
                }
            
            return converted_data
            
        except Exception as e:
            print(f"    转换错误格式时出错: {e}")
            return None

    def _extract_json_from_text(self, text: str) -> Optional[Dict]:
        """从文本中提取JSON内容"""
        try:
            # 尝试找到JSON开始和结束位置
            json_start = text.find('{')
            json_end = text.rfind('}')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_text = text[json_start:json_end + 1]
                background_info = json.loads(json_text)
                
                # 验证提取的JSON结构
                if self._validate_background_json_structure(background_info):
                    return background_info
                else:
                    # 尝试修复结构
                    fixed_info = self._fix_json_structure(background_info)
                    return fixed_info
            else:
                return None
                
        except Exception as e:
            print(f"    从文本提取JSON时出错: {e}")
            return None