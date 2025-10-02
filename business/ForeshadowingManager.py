from typing import Dict


class ForeshadowingManager:
    """伏笔管理器 - 负责重要角色、势力、物品的铺垫引入"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.foreshadowing_elements = {
            "factions": {},
            "characters": {},
            "items": {},
            "locations": {},
            "concepts": {}
        }
        self.introduced_elements = set()
    
    def register_element(self, element_type: str, name: str, importance: str, planned_intro_chapter: int):
        """注册需要铺垫的元素"""
        self.foreshadowing_elements[element_type][name] = {
            "importance": importance,
            "planned_intro_chapter": planned_intro_chapter,
            "foreshadowing_chapters": [],
            "foreshadowing_methods": [],
            "is_introduced": False
        }
    
    def get_foreshadowing_opportunities(self, current_chapter: int) -> Dict:
        """获取当前章节的铺垫机会"""
        opportunities = {}
        
        for element_type, elements in self.foreshadowing_elements.items():
            for name, data in elements.items():
                intro_chapter = data["planned_intro_chapter"]
                
                # 如果计划在后续章节出场，且距离出场还有3-10章，开始铺垫
                if current_chapter < intro_chapter and intro_chapter - current_chapter <= 10:
                    # 计算铺垫强度
                    if intro_chapter - current_chapter <= 3:
                        intensity = "strong"
                    elif intro_chapter - current_chapter <= 6:
                        intensity = "medium"
                    else:
                        intensity = "light"
                    
                    if element_type not in opportunities:
                        opportunities[element_type] = []
                    
                    opportunities[element_type].append({
                        "name": name,
                        "intensity": intensity,
                        "planned_intro_chapter": intro_chapter,
                        "chapters_until_intro": intro_chapter - current_chapter
                    })
        
        return opportunities
    
    def generate_foreshadowing_prompt(self, current_chapter: int) -> str:
        """生成铺垫提示词"""
        opportunities = self.get_foreshadowing_opportunities(current_chapter)
        
        if not opportunities:
            return "# 🎭 重要元素铺垫指导\n\n暂无需要铺垫的重要元素。"
        
        prompt_parts = ["\n\n# 🎭 重要元素铺垫指导"]
        
        for element_type, elements in opportunities.items():
            if elements:
                prompt_parts.append(f"\n## {self._get_element_type_name(element_type)}铺垫:")
                
                for element in elements:
                    methods = self._get_foreshadowing_methods(
                        element_type, element["name"], element["intensity"]
                    )
                    prompt_parts.extend([
                        f"- **{element['name']}** (计划第{element['planned_intro_chapter']}章出场):",
                        f"  距离出场还有{element['chapters_until_intro']}章，{element['intensity']}铺垫",
                        f"  建议铺垫方式: {methods}"
                    ])
        
        result = "\n".join(prompt_parts)
        return result if result.strip() else "# 🎭 重要元素铺垫指导\n\n暂无需要铺垫的重要元素。"
    
    def _get_element_type_name(self, element_type: str) -> str:
        """获取元素类型名称"""
        names = {
            "factions": "势力",
            "characters": "角色", 
            "items": "物品",
            "locations": "地点",
            "concepts": "概念"
        }
        return names.get(element_type, element_type)
    
    def _get_foreshadowing_methods(self, element_type: str, name: str, intensity: str) -> str:
        """根据元素类型和强度获取铺垫方法"""
        base_methods = {
            "factions": {
                "light": ["路人对话提及", "背景新闻暗示", "相关物品出现"],
                "medium": ["角色讨论其影响", "相关事件发生", "历史背景介绍"],
                "strong": ["直接冲突预兆", "关键人物关联", "重大事件关联"]
            },
            "characters": {
                "light": ["他人提及名字", "相关物品出现", "背景故事暗示"],
                "medium": ["详细背景介绍", "与他人的关系铺垫", "能力/特点传闻"],
                "strong": ["直接影响力展现", "关键事件关联", "主角目标关联"]
            },
            "items": {
                "light": ["传说/神话提及", "相关描述出现", "功能暗示"],
                "medium": ["具体信息介绍", "获取线索出现", "重要性强调"],
                "strong": ["直接线索出现", "获取方法明确", "关键作用展示"]
            }
        }
        
        methods_map = base_methods.get(element_type, base_methods["characters"])
        methods = methods_map.get(intensity, methods_map["medium"])
        return "、".join(methods[:2])
