"""
简化的凡人修仙传知识库管理器
专为创意+背景设定生成设计，提供简洁高效的背景资料查询
"""

import json
import os
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

class SimplifiedKnowledgeBase:
    """简化的凡人修仙传知识库管理器"""
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化简化知识库管理器
        
        Args:
            knowledge_base_path: 知识库文件路径，默认使用简化版本
        """
        if knowledge_base_path is None:
            # 默认使用简化版知识库
            current_dir = Path(__file__).parent.parent.parent
            self.knowledge_base_path = current_dir / "knowledge_base" / "凡人修仙传" / "simplified_knowledge_base.json"
        else:
            self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base = None
        self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> None:
        """加载知识库数据"""
        try:
            if self.knowledge_base_path.exists():
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
            else:
                print(f"警告：简化知识库文件不存在: {self.knowledge_base_path}")
                self.knowledge_base = self._get_empty_knowledge_base()
        except Exception as e:
            print(f"加载简化知识库失败: {e}")
            self.knowledge_base = self._get_empty_knowledge_base()
    
    def _get_empty_knowledge_base(self) -> Dict[str, Any]:
        """获取空的知识库结构"""
        return {
            "worldview": {},
            "characters": {},
            "power_system": {},
            "sects_and_factions": {},
            "creation_guidelines": {}
        }
    
    def get_worldview(self) -> Dict[str, str]:
        """
        获取世界观设定
        
        Returns:
            包含世界名称、时代背景、社会结构的字典
        """
        if not self.knowledge_base:
            return {}
        return self.knowledge_base.get("worldview", {})
    
    def get_character_template(self, character_type: str = "主角模板") -> Dict[str, Any]:
        """
        获取角色模板
        
        Args:
            character_type: 角色类型，如"主角模板"、"女主角模板"
            
        Returns:
            角色模板信息
        """
        if not self.knowledge_base:
            return {}
        
        characters = self.knowledge_base.get("characters", {})
        
        # 先查找模板角色
        template_characters = characters.get("模板角色", {})
        if character_type in template_characters:
            return template_characters[character_type]
        
        # 如果不是模板，查找具体角色
        if character_type in characters:
            return characters[character_type]
        
        return {}
    
    def get_character_info(self, character_name: str) -> Dict[str, Any]:
        """
        获取具体角色信息
        
        Args:
            character_name: 角色名称
            
        Returns:
            角色详细信息
        """
        if not self.knowledge_base:
            return {}
        
        characters = self.knowledge_base.get("characters", {})
        
        # 直接查找角色
        if character_name in characters:
            return characters[character_name]
        
        # 在模板角色中查找
        template_characters = characters.get("模板角色", {})
        if character_name in template_characters:
            return template_characters[character_name]
        
        return {}
    
    def get_power_system(self) -> Dict[str, Any]:
        """
        获取修炼体系信息
        
        Returns:
            修炼体系和等级划分
        """
        if not self.knowledge_base:
            return {}
        return self.knowledge_base.get("power_system", {})
    
    def get_cultivation_realms(self) -> Dict[str, str]:
        """
        获取修炼境界描述
        
        Returns:
            境界名称和描述的映射
        """
        power_system = self.get_power_system()
        return power_system.get("等级划分", {})
    
    def get_special_abilities(self) -> Dict[str, str]:
        """
        获取特殊能力说明
        
        Returns:
            特殊能力类型和描述
        """
        power_system = self.get_power_system()
        return power_system.get("特殊能力", {})
    
    def get_sects_and_factions(self) -> Dict[str, Any]:
        """
        获取门派势力信息
        
        Returns:
            正道门派和魔道势力信息
        """
        if not self.knowledge_base:
            return {}
        return self.knowledge_base.get("sects_and_factions", {})
    
    def get_plot_elements(self) -> Dict[str, Any]:
        """
        获取剧情元素模板
        
        Returns:
            经典剧情模式和重要转折点
        """
        if not self.knowledge_base:
            return {}
        return self.knowledge_base.get("plot_elements", {})
    
    def get_creation_guidelines(self) -> Dict[str, Any]:
        """
        获取创作指南
        
        Returns:
            角色设定、剧情发展、创新空间的指导
        """
        if not self.knowledge_base:
            return {}
        return self.knowledge_base.get("creation_guidelines", {})
    
    def generate_character_background(self, character_type: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """
        生成角色背景设定
        
        Args:
            character_type: 角色类型（主角模板、女主角模板等）
            custom_name: 自定义角色名称
            
        Returns:
            生成的角色背景信息
        """
        template = self.get_character_template(character_type)
        if not template:
            return {}
        
        # 复制模板并添加自定义名称
        background = template.copy()
        if custom_name:
            background["姓名"] = custom_name
        
        # 添加生成时间戳
        import datetime
        background["生成时间"] = datetime.datetime.now().isoformat()
        
        return background
    
    def generate_story_prompt(self, focus_element: str = "worldview") -> str:
        """
        生成故事创作提示
        
        Args:
            focus_element: 重点关注元素（worldview、character、power_system等）
            
        Returns:
            创作提示文本
        """
        if not self.knowledge_base:
            return "知识库未加载，无法生成提示"
        
        prompts = []
        
        if focus_element == "worldview":
            worldview = self.get_worldview()
            if worldview:
                prompts.append(f"世界背景：{worldview.get('世界名称', '')}")
                prompts.append(f"时代背景：{worldview.get('时代背景', '')}")
                prompts.append(f"社会特点：{worldview.get('社会结构', '')}")
        
        elif focus_element == "character":
            protagonist = self.get_character_template("主角模板")
            if protagonist:
                prompts.append(f"主角设定：{protagonist.get('类型', '')}")
                prompts.append(f"角色背景：{protagonist.get('背景', '')}")
                prompts.append(f"当前处境：{protagonist.get('处境', '')}")
                prompts.append(f"终极目标：{protagonist.get('目标', '')}")
        
        elif focus_element == "power_system":
            realms = self.get_cultivation_realms()
            if realms:
                prompts.append("修炼体系：")
                for realm, description in realms.items():
                    prompts.append(f"  {realm}：{description}")
        
        elif focus_element == "plot":
            plot_elements = self.get_plot_elements()
            if plot_elements:
                classic_plots = plot_elements.get("经典剧情模式", {})
                if classic_plots:
                    prompts.append("可选剧情模式：")
                    for plot_type, description in classic_plots.items():
                        prompts.append(f"  {plot_type}：{description}")
        
        return "\n".join(prompts) if prompts else "未找到相关信息"
    
    def validate_character_setting(self, character_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证角色设定的合理性
        
        Args:
            character_info: 角色设定信息
            
        Returns:
            验证结果
        """
        guidelines = self.get_creation_guidelines()
        character_guidelines = guidelines.get("角色设定", {})
        
        validation_result = {
            "valid": True,
            "warnings": [],
            "suggestions": []
        }
        
        # 检查主角设定
        if character_info.get("类型") == "主角" or "主角" in str(character_info):
            protagonist_rules = character_guidelines.get("主角", "")
            if "金手指" not in str(character_info) and "金手指" not in protagonist_rules:
                validation_result["warnings"].append("主角应该具备金手指设定")
            if "谨慎" not in str(character_info) and "多疑" not in str(character_info):
                validation_result["suggestions"].append("建议加入谨慎多疑的性格特点")
        
        # 检查修为设定
        if "修为" in character_info:
            realms = self.get_cultivation_realms()
            realm_name = character_info["修为"]
            if realm_name not in realms and realm_name not in ["炼气", "筑基", "结丹", "元婴", "化神"]:
                validation_result["warnings"].append(f"修为境界'{realm_name}'不在标准体系中")
        
        return validation_result
    
    def search_creative_elements(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索创意相关元素
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        if not self.knowledge_base:
            return []
        
        results = []
        keyword_lower = keyword.lower()
        
        # 搜索所有创意相关的字段
        creative_sections = [
            ("世界观", self.knowledge_base.get("worldview", {})),
            ("角色模板", self.knowledge_base.get("characters", {}).get("模板角色", {})),
            ("剧情元素", self.knowledge_base.get("plot_elements", {})),
            ("创作指南", self.knowledge_base.get("creation_guidelines", {}))
        ]
        
        for section_name, section_data in creative_sections:
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if keyword_lower in key.lower() or (isinstance(value, str) and keyword_lower in value.lower()):
                        results.append({
                            "section": section_name,
                            "key": key,
                            "value": value,
                            "type": "creative_element"
                        })
        
        return results
    
    def export_creation_package(self, focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        导出创作素材包
        
        Args:
            focus_areas: 重点关注领域，如["worldview", "character", "plot"]
            
        Returns:
            创作素材包
        """
        if not self.knowledge_base:
            return {}
        
        if focus_areas is None:
            focus_areas = ["worldview", "character", "power_system", "plot_elements", "creation_guidelines"]
        
        creation_package = {
            "export_time": datetime.datetime.now().isoformat(),
            "package_name": "凡人修仙传同人创作素材包",
            "focus_areas": focus_areas
        }
        
        for area in focus_areas:
            if area == "worldview":
                creation_package["世界观设定"] = self.get_worldview()
            elif area == "character":
                creation_package["角色模板"] = self.knowledge_base.get("characters", {}).get("模板角色", {})
                creation_package["主要角色"] = {k: v for k, v in self.knowledge_base.get("characters", {}).items() if k != "模板角色"}
            elif area == "power_system":
                creation_package["修炼体系"] = self.get_power_system()
            elif area == "plot_elements":
                creation_package["剧情元素"] = self.get_plot_elements()
            elif area == "creation_guidelines":
                creation_package["创作指南"] = self.get_creation_guidelines()
        
        return creation_package


# 使用示例
if __name__ == "__main__":
    # 创建简化知识库管理器
    kb = SimplifiedKnowledgeBase()
    
    print("=== 简化知识库测试 ===")
    
    # 测试世界观查询
    print("\n1. 世界观设定:")
    worldview = kb.get_worldview()
    for key, value in worldview.items():
        print(f"  {key}: {value[:100]}...")
    
    # 测试角色模板
    print("\n2. 主角模板:")
    protagonist = kb.get_character_template("主角模板")
    for key, value in protagonist.items():
        print(f"  {key}: {value}")
    
    # 测试故事提示生成
    print("\n3. 故事提示:")
    prompt = kb.generate_story_prompt("character")
    print(prompt)
    
    # 测试创作素材导出
    print("\n4. 创作素材包:")
    package = kb.export_creation_package(["worldview", "character"])
    print(f"  包含领域: {package.get('focus_areas', [])}")
    print(f"  导出时间: {package.get('export_time', '')}")