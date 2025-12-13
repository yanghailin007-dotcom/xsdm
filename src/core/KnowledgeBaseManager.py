"""
凡人修仙传知识库管理器
用于管理和查询背景设定知识库，避免AI生成内容时的偏离问题
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

class KnowledgeBaseManager:
    """凡人修仙传知识库管理器"""
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化知识库管理器
        
        Args:
            knowledge_base_path: 知识库文件路径，默认使用项目内置路径
        """
        if knowledge_base_path is None:
            # 默认路径
            current_dir = Path(__file__).parent.parent.parent
            self.knowledge_base_path = current_dir / "knowledge_base" / "凡人修仙传" / "fanren_knowledge_base_template.json"
        else:
            self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base = None
        self.example_data = None
        self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> None:
        """加载知识库数据"""
        try:
            # 加载主知识库
            if self.knowledge_base_path.exists():
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
            else:
                print(f"警告：知识库文件不存在: {self.knowledge_base_path}")
                self.knowledge_base = self._get_empty_knowledge_base()
            
            # 加载示例数据
            example_path = self.knowledge_base_path.parent / "example_filled_data.json"
            if example_path.exists():
                with open(example_path, 'r', encoding='utf-8') as f:
                    self.example_data = json.load(f)
                    
        except Exception as e:
            print(f"加载知识库失败: {e}")
            self.knowledge_base = self._get_empty_knowledge_base()
    
    def _get_empty_knowledge_base(self) -> Dict[str, Any]:
        """获取空的知识库结构"""
        return {
            "metadata": {"title": "未找到知识库", "version": "0.0.0"},
            "world_setting": {},
            "characters": {},
            "cultivation_system": {},
            "sects_and_factions": {},
            "treasures_and_items": {},
            "rules_and_constraints": {}
        }
    
    def get_character_info(self, character_name: str) -> Dict[str, Any]:
        """
        获取角色信息
        
        Args:
            character_name: 角色名称
            
        Returns:
            角色信息字典
        """
        if not self.knowledge_base:
            return {}
            
        # 先在主角色中查找
        protagonist = self.knowledge_base.get("characters", {}).get("protagonist", {})
        if character_name.lower() in ["韩立", "han_li"]:
            return protagonist.get("han_li", {})
        
        # 在主要角色中查找
        major_characters = self.knowledge_base.get("characters", {}).get("major_characters", {})
        for char_key, char_info in major_characters.items():
            if char_info.get("name") == character_name:
                return char_info
        
        # 在示例数据中查找
        if self.example_data:
            examples = self.example_data.get("filled_examples", {})
            char_example = examples.get("character_example", {})
            if character_name.lower() in ["韩立", "han_li"]:
                return char_example.get("han_li_detailed", {})
        
        return {}
    
    def get_cultivation_realm(self, realm_name: str) -> Dict[str, Any]:
        """
        获取修炼境界信息
        
        Args:
            realm_name: 境界名称
            
        Returns:
            境界信息字典
        """
        if not self.knowledge_base:
            return {}
            
        realms = self.knowledge_base.get("cultivation_system", {}).get("realms", {})
        
        # 英文转中文映射
        realm_mapping = {
            "qi_refining": "炼气期",
            "foundation_establishment": "筑基期", 
            "core_formation": "结丹期",
            "nascent_soul": "元婴期",
            "炼气": "qi_refining",
            "筑基": "foundation_establishment",
            "结丹": "core_formation", 
            "元婴": "nascent_soul"
        }
        
        # 尝试直接匹配
        if realm_name in realms:
            return realms[realm_name]
        
        # 尝试映射匹配
        mapped_key = realm_mapping.get(realm_name)
        if mapped_key and mapped_key in realms:
            return realms[mapped_key]
        
        return {}
    
    def get_sect_info(self, sect_name: str) -> Dict[str, Any]:
        """
        获取门派信息
        
        Args:
            sect_name: 门派名称
            
        Returns:
            门派信息字典
        """
        if not self.knowledge_base:
            return {}
            
        sects = self.knowledge_base.get("sects_and_factions", {})
        
        # 搜索所有门派分类
        for category, sect_list in sects.items():
            if sect_name in sect_list:
                return sect_list[sect_name]
        
        # 在示例数据中查找
        if self.example_data:
            examples = self.example_data.get("filled_examples", {})
            sect_example = examples.get("sect_example", {})
            for sect_key, sect_info in sect_example.items():
                if sect_info.get("name") == sect_name:
                    return sect_info
        
        return {}
    
    def get_treasure_info(self, treasure_name: str) -> Dict[str, Any]:
        """
        获取法宝物品信息
        
        Args:
            treasure_name: 法宝名称
            
        Returns:
            法宝信息字典
        """
        if not self.knowledge_base:
            return {}
            
        treasures = self.knowledge_base.get("treasures_and_items", {})
        
        # 搜索所有法宝分类
        for category, treasure_list in treasures.items():
            if isinstance(treasure_list, dict):
                if treasure_name in treasure_list:
                    return treasure_list[treasure_name]
                
                # 搜索examples中的famous_examples
                if "famous_examples" in treasure_list:
                    for example in treasure_list["famous_examples"]:
                        if isinstance(example, str) and example == treasure_name:
                            return {"name": example, "category": category}
                        elif isinstance(example, dict) and example.get("name") == treasure_name:
                            return example
        
        # 在示例数据中查找
        if self.example_data:
            examples = self.example_data.get("filled_examples", {})
            treasure_example = examples.get("treasure_example", {})
            for treasure_key, treasure_info in treasure_example.items():
                if treasure_info.get("name") == treasure_name:
                    return treasure_info
        
        return {}
    
    def validate_character_consistency(self, character_name: str, behavior: str) -> Dict[str, Any]:
        """
        验证角色行为的一致性
        
        Args:
            character_name: 角色名称
            behavior: 要验证的行为描述
            
        Returns:
            验证结果字典
        """
        character_info = self.get_character_info(character_name)
        if not character_info:
            return {"valid": False, "reason": "角色信息未找到"}
        
        # 获取角色性格特征
        personality_traits = character_info.get("personality_traits", [])
        if isinstance(personality_traits, list):
            traits_text = "、".join(personality_traits)
        else:
            traits_text = str(personality_traits)
        
        # 基本验证逻辑（可以根据需要扩展）
        validation_rules = self.knowledge_base.get("rules_and_constraints", {}).get("character_consistency", {}) if self.knowledge_base else {}
        
        result = {
            "valid": True,
            "character": character_name,
            "traits": traits_text,
            "behavior": behavior,
            "warnings": []
        }
        
        # 检查韩立的核心特征
        if character_name.lower() in ["韩立", "han_li"]:
            if "鲁莽" in behavior or "冲动" in behavior:
                result["valid"] = False
                result["warnings"].append("韩立性格谨慎，不会鲁莽行事")
            
            if "轻信" in behavior or "轻易相信" in behavior:
                result["valid"] = False  
                result["warnings"].append("韩立多疑，不会轻易相信他人")
        
        return result
    
    def validate_cultivation_logic(self, realm1: str, realm2: str, action: str) -> Dict[str, Any]:
        """
        验证修炼逻辑的合理性
        
        Args:
            realm1: 角色当前境界
            realm2: 对手或目标境界
            action: 执行的动作
            
        Returns:
            验证结果字典
        """
        realm1_info = self.get_cultivation_realm(realm1)
        realm2_info = self.get_cultivation_realm(realm2)
        
        if not realm1_info or not realm2_info:
            return {"valid": False, "reason": "境界信息不完整"}
        
        # 简单的境界差距验证
        realm_order = ["炼气期", "筑基期", "结丹期", "元婴期", "化神期"]
        
        try:
            index1 = realm_order.index(realm1_info.get("name", realm1))
            index2 = realm_order.index(realm2_info.get("name", realm2))
            gap = index2 - index1
        except ValueError:
            return {"valid": False, "reason": "无法识别境界等级"}
        
        result = {
            "valid": True,
            "realm_gap": gap,
            "realm1": realm1_info.get("name", realm1),
            "realm2": realm2_info.get("name", realm2),
            "action": action,
            "warnings": []
        }
        
        # 如果境界差距超过2级，正面对抗通常不合理
        if gap > 2 and "正面" in action:
            result["valid"] = False
            result["warnings"].append(f"境界差距{gap}级，正面对抗不合理")
        
        if gap > 1 and "轻易" in action:
            result["warnings"].append(f"境界差距{gap}级，战斗不会轻易")
        
        return result
    
    def get_validation_checklist(self) -> Dict[str, List[str]]:
        """获取验证清单"""
        if not self.knowledge_base:
            return {"character_validation": [], "plot_validation": [], "world_validation": []}
        return self.knowledge_base.get("validation_checklist", {
            "character_validation": [],
            "plot_validation": [],
            "world_validation": []
        })
    
    def get_fanfiction_guidelines(self) -> Dict[str, Any]:
        """获取同人创作指南"""
        if not self.knowledge_base:
            return {}
        return self.knowledge_base.get("fanfiction_guidelines", {})
    
    def search_knowledge(self, keyword: str) -> List[Dict[str, Any]]:
        """
        在知识库中搜索关键词
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        def search_recursive(data, path="root"):
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}"
                    if keyword_lower in key.lower() or (isinstance(value, str) and keyword_lower in value.lower()):
                        results.append({
                            "path": current_path,
                            "key": key,
                            "value": value,
                            "type": "dict_item"
                        })
                    search_recursive(value, current_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    current_path = f"{path}[{i}]"
                    if isinstance(item, str) and keyword_lower in item.lower():
                        results.append({
                            "path": current_path,
                            "key": f"list_item_{i}",
                            "value": item,
                            "type": "list_item"
                        })
                    search_recursive(item, current_path)
        
        search_recursive(self.knowledge_base)
        
        # 如果有示例数据，也搜索
        if self.example_data:
            search_recursive(self.example_data, "example_data")
        
        return results
    
    def export_knowledge_summary(self) -> str:
        """导出知识库摘要"""
        if not self.knowledge_base:
            return "知识库为空"
        
        metadata = self.knowledge_base.get("metadata", {})
        title = metadata.get("title", "未知标题")
        version = metadata.get("version", "未知版本")
        
        summary = f"知识库: {title} (v{version})\n\n"
        
        # 统计各部分数据
        sections = [
            ("世界设定", "world_setting"),
            ("角色信息", "characters"), 
            ("修炼体系", "cultivation_system"),
            ("门派势力", "sects_and_factions"),
            ("法宝物品", "treasures_and_items"),
            ("规则限制", "rules_and_constraints")
        ]
        
        for section_name, section_key in sections:
            section_data = self.knowledge_base.get(section_key, {})
            if section_data:
                summary += f"[OK] {section_name}: {len(section_data)} 个条目\n"
            else:
                summary += f"[EMPTY] {section_name}: 暂无数据\n"
        
        return summary


# 使用示例和测试
if __name__ == "__main__":
    # 创建知识库管理器实例
    kb_manager = KnowledgeBaseManager()
    
    # 打印知识库摘要
    print("=== 知识库摘要 ===")
    print(kb_manager.export_knowledge_summary())
    print()
    
    # 测试角色查询
    print("=== 角色信息查询 ===")
    han_li_info = kb_manager.get_character_info("韩立")
    print(f"韩立信息: {han_li_info}")
    print()
    
    # 测试修炼境界查询
    print("=== 修炼境界查询 ===")
    qi_refining_info = kb_manager.get_cultivation_realm("炼气期")
    print(f"炼气期信息: {qi_refining_info}")
    print()
    
    # 测试验证功能
    print("=== 角色行为验证 ===")
    validation_result = kb_manager.validate_character_consistency("韩立", "鲁莽冲入陷阱")
    print(f"验证结果: {validation_result}")
    print()
    
    # 测试搜索功能
    print("=== 知识搜索 ===")
    search_results = kb_manager.search_knowledge("韩立")
    print(f"搜索结果: {len(search_results)} 条")
    for result in search_results[:3]:  # 只显示前3条
        print(f"  - {result['path']}: {result['value']}")