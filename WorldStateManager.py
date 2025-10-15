"""世界状态管理器类 - 专注世界状态和角色发展管理"""

import re
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class WorldStateManager:
    def __init__(self, storage_path: str = "./quality_data"):
        self.storage_path = storage_path
        
        # 确保存储目录存在
        os.makedirs(storage_path, exist_ok=True)
        
        # 角色发展模板
        self.character_development_templates = {
            "core_character": {
                # 基础信息 - 会被系统维护
                "name": "",
                "status": "active", 
                "role_type": "主角/重要配角/次要配角",
                "importance": "major",
                "first_appearance_chapter": 0,  # 首次出场章节 - 系统维护
                "last_updated_chapter": 0,      # 最后更新章节 - 系统维护
                "total_appearances": 1,         # 总出场次数 - 系统维护
                
                # 性格特征 - 会被更新
                "personality_traits": {
                    "core_traits": [],  # 核心特质 - 会被更新
                    "contradictions": "",  # 性格矛盾点 - 可能被更新
                    "behavior_patterns": "",  # 行为模式 - 可能被更新
                    "speech_style": ""  # 语言风格 - 可能被更新
                },
                
                # 背景故事 - 会被更新
                "background_story": {
                    "basic_info": "",  # 基本信息 - 会被更新
                    "key_experiences": [],  # 关键经历 - 会被更新
                    "motivations": "",  # 动机和追求 - 可能被更新
                },
                
                # 名场面 - 会被更新
                "iconic_scenes": [],  # 改为空数组，实际数据会动态添加
                
                # 关系网络 - 会被更新
                "relationship_network": {
                    "allies": [],  # 盟友 - 会被更新
                    "rivals": [],  # 对手 - 会被更新
                    "complex_relationships": []  # 复杂关系 - 可能被更新
                },
                
                # 发展里程碑 - 会被更新
                "development_milestones": [],  # 改为空数组，实际数据会动态添加
            },
            
            "minor_character": {
                # 基础信息 - 会被系统维护
                "name": "",
                "status": "active",
                "role_type": "次要配角/路人角色", 
                "importance": "minor",  # 次要角色标识
                "first_appearance_chapter": 0,
                "last_updated_chapter": 0,
                "total_appearances": 1,
                
                # 基本信息 - 可能被更新
                "basic_description": "",  # 角色基本描述
                "purpose_in_story": ""  # 在故事中的用途
            },
            
            "unnamed_character": {
                # 基础信息 - 会被系统维护
                "name": "",
                "status": "active",
                "role_type": "路人/群众",
                "importance": "unnamed",  # 未命名角色标识
                "first_appearance_chapter": 0,
                "last_updated_chapter": 0, 
                "total_appearances": 1,
                
                # 场景信息 - 可能被更新
                "appearance_context": ""  # 出现场景描述
            }
        }
        
        # 角色重要性判断规则
        self.character_importance_rules = {
            "major_character_indicators": [
                "主角", "主要角色", "重要角色", "主人公", "主角团",
                "有名字且在多个章节出现",
                "有详细背景故事", 
                "有性格描写和发展轨迹"
            ],
            "minor_character_indicators": [
                "配角", "次要角色", "路人", "群众", "士兵", "村民",
                "只在单一章节出现",
                "没有名字或使用通用称谓",
                "没有性格描写"
            ],
            "unnamed_character_patterns": [
                r"路人[甲乙丙丁]?", r"士兵[一二三四]?", r"村民[ABCD]?",
                r"老者", r"少年", r"女子", r"男子", r"官员", r"侍卫",
                r"店小二", r"掌柜", r"大夫", r"书生"
            ]
        }
        
        # 当前小说的世界状态（用于一致性检查）
        self.current_world_state = {}

    def load_previous_assessments(self, novel_title: str, novel_data: Dict = None) -> Dict:
        """加载之前章节的评估数据，如果没有则从novel_data初始化"""
        state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载世界状态失败: {e}")
        
        # 如果没有找到世界状态文件且有novel_data，则初始化
        if novel_data:
            print(f"🔄 未找到现有世界状态，从novel_data初始化...")
            return self.initialize_world_state_from_novel_data(novel_title, novel_data)
        
        return {}

    def save_assessment_data(self, novel_title: str, chapter_number: int, assessment_data: Dict):
        """保存评估数据"""
        # 更新并保存世界状态
        if 'updated_world_state' in assessment_data:
            self.current_world_state = assessment_data['updated_world_state']
            state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
            try:
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(self.current_world_state, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存世界状态失败: {e}")

    def assess_character_importance(self, character_data: Dict, chapter_content: str = "") -> str:
        """评估角色重要性"""
        character_name = character_data.get("name", "")
        
        # 检查是否为未命名角色
        if self._is_unnamed_character(character_name):
            return "unnamed"
        
        # 检查角色类型
        role_type = character_data.get("role_type", "").lower()
        if any(indicator in role_type for indicator in ["主角", "主要", "重要"]):
            return "major"
        elif any(indicator in role_type for indicator in ["配角", "次要", "路人"]):
            return "minor"
        
        # 基于内容分析重要性
        if chapter_content:
            importance_score = self._analyze_character_importance_from_content(character_name, chapter_content)
            if importance_score >= 0.7:
                return "major"
            elif importance_score >= 0.3:
                return "minor"
            else:
                return "unnamed"
        
        # 默认作为次要角色
        return "minor"

    def _is_unnamed_character(self, character_name: str) -> bool:
        """判断是否为未命名角色"""
        if not character_name or len(character_name) <= 1:
            return True
        
        # 检查是否符合未命名角色模式
        for pattern in self.character_importance_rules["unnamed_character_patterns"]:
            if re.match(pattern, character_name):
                return True
        
        # 检查是否为通用称谓
        generic_titles = ["老者", "少年", "女子", "男子", "官员", "侍卫", "店小二", "掌柜", "大夫", "书生"]
        if character_name in generic_titles:
            return True
        
        return False

    def _analyze_character_importance_from_content(self, character_name: str, content: str) -> float:
        """从内容分析角色重要性得分"""
        if not character_name:
            return 0.0
        
        score = 0.0
        
        # 1. 提及频率（权重：0.4）
        total_words = len(content)
        mention_count = content.count(character_name)
        mention_frequency = mention_count / max(total_words / 1000, 1)  # 每千字提及次数
        score += min(mention_frequency / 5, 1.0) * 0.4
        
        # 2. 是否有对话（权重：0.3）
        dialogue_indicators = [f"{character_name}说：", f"{character_name}道：", f"{character_name}问："]
        has_dialogue = any(indicator in content for indicator in dialogue_indicators)
        score += 0.3 if has_dialogue else 0
        
        # 3. 是否有行动描写（权重：0.2）
        action_indicators = [f"{character_name}站起身", f"{character_name}走过去", f"{character_name}笑了笑"]
        has_actions = any(indicator in content for indicator in action_indicators)
        score += 0.2 if has_actions else 0
        
        # 4. 是否有心理活动（权重：0.1）
        thought_indicators = [f"{character_name}心想", f"{character_name}思考", f"{character_name}暗想"]
        has_thoughts = any(indicator in content for indicator in thought_indicators)
        score += 0.1 if has_thoughts else 0
        
        return min(score, 1.0)

    def _update_world_state_incrementally(self, novel_title: str, changes: Dict, chapter_number: int):
        """增量更新世界状态 - 使用清洗后的数据，并增加更新计数"""
        # 加载当前世界状态
        current_state = self.load_previous_assessments(novel_title)
        if not current_state:
            current_state = {
                "characters": {},
                "items": {}, 
                "relationships": {},
                "skills": {},
                "locations": {}
            }
        
        # 应用增量更新 - 现在数据已经是清洗后的格式
        for category, elements in changes.items():
            if category not in current_state:
                current_state[category] = {}
            
            for element_id, element_data in elements.items():
                if element_id in current_state[category]:
                    # 更新现有元素 - 只更新清洗后的字段
                    current_element = current_state[category][element_id]
                    
                    # 更新基础字段
                    for field in ['description']:
                        if field in element_data:
                            current_element[field] = element_data[field]
                    
                    # 更新attributes字段（如果存在）
                    if 'attributes' in element_data:
                        if 'attributes' not in current_element:
                            current_element['attributes'] = {}
                        current_element['attributes'].update(element_data['attributes'])
                    
                    # 增加更新计数
                    current_element['update_count'] = current_element.get('update_count', 0) + 1
                    current_element['last_updated'] = chapter_number
                else:
                    # 新增元素 - 初始化更新计数为1
                    element_data['first_appearance'] = chapter_number
                    element_data['last_updated'] = chapter_number
                    element_data['update_count'] = 1  # 新增元素的初始更新计数
                    current_state[category][element_id] = element_data
        
        # 保存更新后的世界状态
        self.current_world_state = current_state
        state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(current_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存世界状态失败: {e}")

    def _simplify_character_status(self, novel_title: str, character_name: str, status: str, chapter_number: int):
        """简化死亡/退场角色的信息，只保留状态和姓名"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        
        if not os.path.exists(character_file):
            return
        
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                characters = json.load(f)
            
            if character_name in characters:
                # 保留核心信息，删除详细设定
                characters[character_name] = {
                    "name": character_name,
                    "status": status,
                    "first_appearance_chapter": characters[character_name].get("first_appearance_chapter", chapter_number),
                    "last_updated_chapter": chapter_number,
                    "death_chapter": chapter_number if status == "dead" else None,
                    "total_appearances": characters[character_name].get("total_appearances", 1)
                }
                
                # 保存简化后的角色信息
                with open(character_file, 'w', encoding='utf-8') as f:
                    json.dump(characters, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 角色 {character_name} 状态已简化为 {status}")
                
        except Exception as e:
            print(f"❌ 简化角色状态失败: {e}")

    def _validate_and_clean_world_state_changes(self, changes: Dict, chapter_number: int) -> Dict:
        """验证和清洗世界状态变化数据，确保字段统一"""
        
        # 定义允许的字段结构
        ALLOWED_FIELDS = {
            "characters": {
                "description": str,
                "attributes": {
                    "status": str,
                    "location": str,
                    "title": str,
                    "occupation": str, 
                    "rank": str,
                    "faction": str
                }
            },
            "items": {
                "description": str,
                "owner": str,
                "status": str,
                "location": str
            },
            "relationships": {
                "type": str,
                "description": str,
                "status": str
            },
            "skills": {
                "description": str,
                "owner": str,
                "level": str,
                "status": str
            },
            "locations": {
                "description": str,
                "status": str
            }
        }
        
        cleaned_changes = {}
        
        for category, elements in changes.items():
            if category not in ALLOWED_FIELDS:
                print(f"⚠️ 跳过未知类别: {category}")
                continue
                
            cleaned_changes[category] = {}
            allowed_structure = ALLOWED_FIELDS[category]
            
            for element_id, element_data in elements.items():
                if not isinstance(element_data, dict):
                    print(f"⚠️ 跳过无效数据格式: {element_id}")
                    continue
                    
                cleaned_data = {}
                
                # 验证和清洗字段
                for field, field_type in allowed_structure.items():
                    if field in element_data:
                        if isinstance(field_type, dict):
                            # 嵌套字典字段（如attributes）
                            if isinstance(element_data[field], dict):
                                cleaned_nested = {}
                                for nested_field, nested_type in field_type.items():
                                    if nested_field in element_data[field]:
                                        if isinstance(element_data[field][nested_field], nested_type):
                                            cleaned_nested[nested_field] = element_data[field][nested_field]
                                        else:
                                            print(f"⚠️ 字段类型不匹配: {element_id}.{field}.{nested_field}")
                                cleaned_data[field] = cleaned_nested
                            else:
                                print(f"⚠️ 字段格式错误: {element_id}.{field}")
                        else:
                            # 简单字段
                            if isinstance(element_data[field], field_type):
                                cleaned_data[field] = element_data[field]
                            else:
                                print(f"⚠️ 字段类型不匹配: {element_id}.{field}")
                
                # 确保必要字段存在
                if category == "characters":
                    if "attributes" not in cleaned_data:
                        cleaned_data["attributes"] = {}
                    if "status" not in cleaned_data["attributes"]:
                        cleaned_data["attributes"]["status"] = "活跃"
                    if "location" not in cleaned_data["attributes"]:
                        cleaned_data["attributes"]["location"] = "未知"
                
                if cleaned_data:
                    cleaned_changes[category][element_id] = cleaned_data
                    print(f"✅ 已清洗: {category}.{element_id}")
                else:
                    print(f"❌ 数据无效已跳过: {category}.{element_id}")
        
        return cleaned_changes

    def initialize_world_state_from_novel_data(self, novel_title: str, novel_data: Dict):
        """基于小说数据初始化世界状态"""
        
        world_state = {
            "characters": {},
            "items": {},
            "relationships": {},
            "skills": {},
            "locations": {}
        }
        
        # 从角色设计中提取角色信息
        character_design = novel_data.get("character_design", {})
        if character_design:
            # 处理主角
            main_character = character_design.get("main_character", {})
            if main_character:
                name = main_character.get("name", "主角")
                world_state["characters"][name] = {
                    "first_appearance": 1,
                    "description": main_character.get("personality", ""),
                    "attributes": main_character.get("attributes", {}),
                    "last_updated": 1
                }
            
            # 处理配角
            supporting_characters = character_design.get("supporting_characters", [])
            for char in supporting_characters:
                name = char.get("name", "")
                if name:
                    world_state["characters"][name] = {
                        "first_appearance": 1,
                        "description": char.get("personality", ""),
                        "attributes": char.get("attributes", {}),
                        "last_updated": 1
                    }
        
        # 从世界观中提取地点、物品等信息
        worldview = novel_data.get("core_worldview", {})
        if worldview:
            # 提取地点
            locations = worldview.get("locations", [])
            for loc in locations:
                name = loc.get("name", "")
                if name:
                    world_state["locations"][name] = {
                        "description": loc.get("description", ""),
                        "first_appearance": 1,
                        "last_updated": 1
                    }
            
            # 提取物品
            items = worldview.get("items", [])
            for item in items:
                name = item.get("name", "")
                if name:
                    world_state["items"][name] = {
                        "owner": item.get("owner", ""),
                        "status": item.get("status", ""),
                        "first_appearance": 1,
                        "last_updated": 1
                    }
        
        # 保存初始世界状态
        state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(world_state, f, ensure_ascii=False, indent=2)
            print(f"✅ 从novel_data初始化世界状态成功，保存到 {state_file}")
        except Exception as e:
            print(f"❌ 保存初始世界状态失败: {e}")
        
        return world_state

    def manage_character_development_table(self, novel_title: str, character_data: Dict, 
                                        current_chapter: int, action: str = "update") -> Dict:
        """管理角色发展表 - 根据角色重要性使用不同的模板"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        
        # 加载现有数据
        if os.path.exists(character_file):
            with open(character_file, 'r', encoding='utf-8') as f:
                characters = json.load(f)
        else:
            characters = {}
        
        character_name = character_data.get("name")
        if not character_name:
            return characters
        
        # 评估角色重要性
        importance = self.assess_character_importance(character_data)
        
        if action == "add":
            # 首次出场时添加
            if character_name not in characters:
                # 根据重要性选择模板
                if importance == "major":
                    template = self.character_development_templates["core_character"]
                elif importance == "minor":
                    template = self.character_development_templates["minor_character"]
                else:
                    template = self.character_development_templates["unnamed_character"]
                
                characters[character_name] = {
                    **template,
                    **character_data,
                    "importance": importance,
                    "first_appearance_chapter": current_chapter,
                    "last_updated_chapter": current_chapter,
                    "total_appearances": 1
                }
                print(f"✅ 新增角色到发展表: {character_name} (重要性: {importance}, 第{current_chapter}章首次出场)")
            else:
                # 如果角色已存在，更新出场信息
                if "total_appearances" not in characters[character_name]:
                    characters[character_name]["total_appearances"] = 1
                else:
                    characters[character_name]["total_appearances"] += 1
                characters[character_name]["last_updated_chapter"] = current_chapter
                
        elif action == "update":
            # 更新现有角色
            if character_name in characters:
                # 更新出场次数和最后出场章节
                if "total_appearances" not in characters[character_name]:
                    characters[character_name]["total_appearances"] = 1
                else:
                    characters[character_name]["total_appearances"] += 1
                characters[character_name]["last_updated_chapter"] = current_chapter
                
                # 对于重要角色，更新详细信息；对于次要角色，只更新基本信息和重要性
                current_importance = characters[character_name].get("importance", "minor")
                
                if current_importance == "major":
                    # 重要角色：保留历史信息，合并新数据
                    preserved_fields = [
                        "first_appearance_chapter", "iconic_scenes", 
                        "development_milestones", "background_story",
                        "relationship_network", "personality_traits"
                    ]
                    
                    preserved_data = {}
                    for field in preserved_fields:
                        if field in characters[character_name]:
                            preserved_data[field] = characters[character_name][field]
                    
                    # 更新数据
                    characters[character_name].update(character_data)
                    
                    # 恢复保留的历史数据
                    for field, value in preserved_data.items():
                        if field in character_data and character_data[field]:
                            # 如果新数据中有该字段，则合并而不是覆盖
                            if isinstance(value, list) and isinstance(character_data[field], list):
                                characters[character_name][field] = value + character_data[field]
                            elif isinstance(value, dict) and isinstance(character_data[field], dict):
                                characters[character_name][field] = {**value, **character_data[field]}
                            else:
                                characters[character_name][field] = character_data[field] or value
                        else:
                            characters[character_name][field] = value
                
                else:
                    # 次要或未命名角色：只更新基本信息
                    basic_fields = ["name", "status", "role_type", "basic_description", "purpose_in_story", "appearance_context"]
                    for field in basic_fields:
                        if field in character_data and character_data[field]:
                            characters[character_name][field] = character_data[field]
                
                print(f"✅ 更新角色发展表: {character_name} (重要性: {current_importance}, 第{current_chapter}章)")
        
        # 保存数据
        with open(character_file, 'w', encoding='utf-8') as f:
            json.dump(characters, f, ensure_ascii=False, indent=2)
        
        return characters

    def get_character_development_suggestions(self, character_name: str, novel_title: str, current_chapter: int) -> List[Dict]:
        """获取角色发展建议 - 仅对重要角色提供建议"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        
        if not os.path.exists(character_file):
            return []
        
        with open(character_file, 'r', encoding='utf-8') as f:
            characters = json.load(f)
        
        if character_name not in characters:
            return []
        
        character = characters[character_name]
        character_status = character.get("status", "active")
        
        # 只对活跃的重要角色提供建议
        if character_status != "active" or character.get("importance") != "major":
            return []
        
        suggestions = []
        
        # 基于出场次数和章节进度生成建议
        appearance_gap = current_chapter - character.get("last_updated_chapter", 0)
        total_appearances = character.get("total_appearances", 1)
        
        # 判断角色是否已充分建立
        is_character_established = total_appearances >= 5 and appearance_gap <= 10
        
        # 检查是否需要添加名场面（只在角色未充分建立时建议）
        if not is_character_established:
            iconic_scenes = character.get("iconic_scenes", [])
            if len(iconic_scenes) < 3 and total_appearances >= 3:
                core_trait = character.get('personality_traits', {}).get('core_traits', ['性格'])[0]
                suggestions.append({
                    "type": "添加名场面",
                    "description": f"为{character_name}设计一个展现{core_trait}特质的名场面",
                    "priority": "高",
                    "implementation": f"在第{current_chapter}章安排一个关键场景，通过具体行动展示{character_name}的{core_trait}特质",
                    "reason": f"角色已出场{total_appearances}次，需要强化形象"
                })
    
        # 检查是否需要背景故事（在角色出场3-5章后，且未充分建立时）
        if not is_character_established:
            background_revealed = character.get("development_status", {}).get("background_revealed", False)
            if not background_revealed and total_appearances >= 3 and total_appearances <= 5:
                suggestions.append({
                    "type": "背景故事",
                    "description": f"为{character_name}添加背景故事，解释其性格形成原因",
                    "priority": "中",
                    "implementation": f"通过回忆、对话或第三方提及的方式，在第{current_chapter}章揭示{character_name}的过去经历",
                    "reason": f"角色已出场{total_appearances}次，是揭示背景的合适时机"
                })
        
        # 检查对话强化（如果超过5章没有特色对话，无论角色是否建立都需要）
        last_dialogue_chapter = character.get("last_dialogue_chapter", 0)
        if current_chapter - last_dialogue_chapter > 5:
            speech_style = character.get('personality_traits', {}).get('speech_style', '普通')
            suggestions.append({
                "type": "对话强化",
                "description": f"为{character_name}安排特色对话，强化'{speech_style}'语言风格",
                "priority": "中",
                "implementation": f"在第{current_chapter}章设计符合{character_name}语言风格的对话",
                "reason": f"已{current_chapter - last_dialogue_chapter}章没有特色对话"
            })
        
        # 检查关系发展（持续发展，无论角色是否建立）
        relationships = character.get("relationship_network", {})
        total_relationships = len(relationships.get("allies", [])) + len(relationships.get("rivals", []))
        if total_relationships < 2 and total_appearances >= 5:
            suggestions.append({
                "type": "关系发展",
                "description": f"为{character_name}建立新的人际关系",
                "priority": "中",
                "implementation": f"在第{current_chapter}章通过互动建立新的盟友或对手关系",
                "reason": f"角色人际关系网络较简单，需要丰富"
            })
        
        # 如果角色已充分建立，添加深化建议
        if is_character_established:
            suggestions.append({
                "type": "角色深化",
                "description": f"深化{character_name}的性格层次，展现更多复杂性",
                "priority": "低",
                "implementation": f"通过内心独白或矛盾选择展示{character_name}的性格多面性",
                "reason": f"角色基础已稳固，需要展现更深层次的特质"
            })
        
        return suggestions[:3]  # 返回前3个最高优先级的建议

    def assess_character_development(self, chapter_content: str, characters_in_chapter: List[str], 
                                novel_title: str, chapter_number: int) -> Dict:
        """评估角色发展质量并返回更新建议 - 基于章节编号"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        
        # 加载现有角色数据
        existing_characters = {}
        if os.path.exists(character_file):
            with open(character_file, 'r', encoding='utf-8') as f:
                existing_characters = json.load(f)
        
        assessment_result = {
            "chapter_number": chapter_number,
            "character_updates": {},
            "development_suggestions": [],
            "new_characters": []
        }
        
        for character_name in characters_in_chapter:
            if character_name in existing_characters:
                # 更新角色出场信息
                self.manage_character_development_table(
                    novel_title, 
                    {"name": character_name}, 
                    chapter_number, 
                    "update"
                )
                
                # 获取发展建议
                suggestions = self.get_character_development_suggestions(character_name, novel_title, chapter_number)
                
                # 分析角色表现
                character_presence = self._analyze_character_presence(character_name, chapter_content)
                
                assessment_result["character_updates"][character_name] = {
                    "presence_analysis": character_presence,
                    "development_suggestions": suggestions,
                    "current_appearance": chapter_number,
                    "total_appearances": existing_characters[character_name].get("total_appearances", 1) + 1
                }
                
                assessment_result["development_suggestions"].extend(suggestions)
            else:
                # 新角色首次出现
                assessment_result["new_characters"].append({
                    "name": character_name,
                    "first_appearance_chapter": chapter_number
                })
        
        return assessment_result

    def _analyze_character_presence(self, character_name: str, chapter_content: str) -> Dict:
        """分析角色在章节中的存在感"""
        # 统计角色提及次数
        mention_count = chapter_content.count(character_name)
        
        # 检测是否有对话
        has_dialogue = f"{character_name}说：" in chapter_content or f"{character_name}道：" in chapter_content
        
        # 检测是否有行动描写
        action_indicators = ["站起身", "走过去", "笑了笑", "皱眉头", "叹息", "握拳"]
        has_actions = any(indicator in chapter_content for indicator in action_indicators)
        
        # 检测是否有心理活动
        thought_indicators = ["心想", "思考", "暗想", "寻思"]
        has_thoughts = any(indicator in chapter_content for indicator in thought_indicators)
        
        return {
            "mention_count": mention_count,
            "has_dialogue": has_dialogue,
            "has_actions": has_actions,
            "has_thoughts": has_thoughts,
            "presence_score": min(10, mention_count * 2 + has_dialogue * 3 + has_actions * 2 + has_thoughts * 2)
        }

    def _load_character_development_data(self, novel_title: str) -> Dict:
        """加载角色发展数据"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        
        if not os.path.exists(character_file):
            return {}
        
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载角色发展数据失败: {e}")
            return {}

    def update_character_development_from_assessment(self, novel_title: str, assessment: Dict, chapter_number: int):
        """从评估结果更新角色发展表 - 根据角色重要性区分处理"""
        character_development = assessment.get("character_development_assessment", {})
        
        # 处理新角色
        for new_char in character_development.get("new_characters_introduced", []):
            char_name = new_char["name"]
            role_type = new_char.get("role_type", "次要配角")
            
            # 构建基础角色数据
            character_data = {
                "name": char_name,
                "role_type": role_type
            }
            
            # 评估角色重要性
            importance = self.assess_character_importance(character_data)
            
            # 根据重要性构建不同的数据
            if importance == "major":
                # 重要角色：保存完整信息
                character_data.update({
                    "personality_traits": {
                        "core_traits": [new_char.get("initial_impression", "待完善")],
                        "contradictions": "待发掘",
                        "behavior_patterns": "待观察", 
                        "speech_style": "待定义"
                    },
                    # ... 其他完整字段
                })
            elif importance == "minor":
                # 次要角色：保存基本信息
                character_data.update({
                    "basic_description": new_char.get("initial_impression", "待完善"),
                    "purpose_in_story": "推动情节发展"
                })
            else:
                # 未命名角色：极简信息
                character_data.update({
                    "appearance_context": "在场景中出现"
                })
            
            self.manage_character_development_table(novel_title, character_data, chapter_number, "add")

        # 处理名场面
        for scene in character_development.get("iconic_scenes_identified", []):
            char_name = scene["character"]
            self.manage_character_development_table(novel_title, {
                "name": char_name,
                "iconic_scenes": [{
                    "scene_type": "性格展示/情感爆发/高光时刻",
                    "chapter": scene.get("chapter", chapter_number),
                    "description": scene["scene_description"],
                    "purpose": scene["trait_demonstrated"],
                    "impact_level": scene.get("impact_level", "中")
                }]
            }, chapter_number, "update")
        
        # 处理性格揭示
        for revelation in character_development.get("personality_revelations", []):
            char_name = revelation["character"]
            self.manage_character_development_table(novel_title, {
                "name": char_name,
                "personality_traits": {
                    "core_traits": [revelation["trait_revealed"]]
                }
            }, chapter_number, "update")
        
        # 处理角色互动和关系发展
        for interaction in character_development.get("character_interactions", []):
            characters = interaction.get("characters", [])
            for char_name in characters:
                # 更新角色的关系网络
                relationship_type = "allies" if "合作" in interaction.get("interaction_type", "") else "rivals"
                other_chars = [c for c in characters if c != char_name]
                
                if other_chars:
                    self.manage_character_development_table(novel_title, {
                        "name": char_name,
                        "relationship_network": {
                            relationship_type: other_chars
                        }
                    }, chapter_number, "update")

    def cleanup_characters_by_strategy(self, novel_title: str, strategy_config: Dict) -> Dict:
        """根据策略清理角色数据 - 智能版本"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        
        if not os.path.exists(character_file):
            return {"cleaned_count": 0, "remaining_count": 0, "error": "角色文件不存在"}
        
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                characters = json.load(f)
            
            # 统计清理前的角色数量
            total_before = len(characters)
            importance_counts_before = self._count_characters_by_importance(characters)
            
            # 应用清理策略
            keep_major_only = strategy_config.get("keep_major_only", False)
            preserve_recent = strategy_config.get("preserve_recent_chapters", 5)
            current_chapter = strategy_config.get("current_chapter", 1)
            stage_type = strategy_config.get("stage_type", "normal")
            
            characters_after_cleanup = {}
            
            for char_name, char_data in characters.items():
                if self._should_keep_character(char_data, keep_major_only, preserve_recent, current_chapter, stage_type):
                    # 根据策略简化角色数据
                    simplified_data = self._simplify_character_data(char_data, strategy_config)
                    characters_after_cleanup[char_name] = simplified_data
            
            # 保存清理后的数据
            with open(character_file, 'w', encoding='utf-8') as f:
                json.dump(characters_after_cleanup, f, ensure_ascii=False, indent=2)
            
            # 统计清理后的角色数量
            total_after = len(characters_after_cleanup)
            importance_counts_after = self._count_characters_by_importance(characters_after_cleanup)
            
            result = {
                "cleaned_count": total_before - total_after,
                "remaining_count": total_after,
                "importance_distribution_before": importance_counts_before,
                "importance_distribution_after": importance_counts_after,
                "strategy_used": strategy_config
            }
            
            print(f"✅ 策略清理完成: 清理了 {result['cleaned_count']} 个角色，剩余 {total_after} 个角色")
            return result
            
        except Exception as e:
            print(f"❌ 策略清理失败: {e}")
            return {"cleaned_count": 0, "remaining_count": 0, "error": str(e)}

    def _should_keep_character(self, char_data: Dict, keep_major_only: bool, preserve_recent: int, 
                            current_chapter: int, stage_type: str) -> bool:
        """判断是否应该保留角色"""
        importance = char_data.get("importance", "minor")
        status = char_data.get("status", "active")
        
        # 已死亡或退场的角色总是保留极简信息
        if status in ["dead", "exited"]:
            return True
        
        # 重要角色总是保留
        if importance == "major":
            return True
        
        # 如果策略要求只保留重要角色
        if keep_major_only:
            return False
        
        # 检查角色是否最近活跃
        last_updated = char_data.get("last_updated_chapter", 0)
        if current_chapter - last_updated <= preserve_recent:
            return True
        
        # 根据阶段类型决定保留策略
        if stage_type == "opening" and importance == "minor":
            # 开局阶段保留所有次要角色
            return True
        elif stage_type == "climax" and importance == "unnamed":
            # 高潮阶段不保留未命名角色
            return False
        elif stage_type == "ending" and importance != "major":
            # 结局阶段只保留重要角色
            return False
        
        # 默认保留
        return True

    def _simplify_character_data(self, char_data: Dict, strategy_config: Dict) -> Dict:
        """根据策略简化角色数据"""
        importance = char_data.get("importance", "minor")
        stage_type = strategy_config.get("stage_type", "normal")
        
        # 基础保留字段
        base_fields = {
            "name", "status", "role_type", "importance", 
            "first_appearance_chapter", "last_updated_chapter", "total_appearances"
        }
        
        simplified_data = {field: char_data[field] for field in base_fields if field in char_data}
        
        # 根据重要性和阶段类型决定保留哪些额外字段
        if importance == "major":
            # 重要角色保留完整信息
            preserved_fields = [
                "personality_traits", "background_story", "relationship_network",
                "development_milestones", "iconic_scenes", "development_status"
            ]
            for field in preserved_fields:
                if field in char_data:
                    simplified_data[field] = char_data[field]
        
        elif importance == "minor":
            # 次要角色根据阶段类型决定保留程度
            if stage_type in ["opening", "development"]:
                # 开局和发展阶段保留基本信息
                simplified_data["basic_description"] = char_data.get("basic_description", "角色基本描述")
                simplified_data["purpose_in_story"] = char_data.get("purpose_in_story", "推动情节发展")
            else:
                # 其他阶段进一步简化
                simplified_data["basic_description"] = char_data.get("basic_description", "角色基本描述")[:50] + "..."
        
        else:  # unnamed
            # 未命名角色总是极简
            simplified_data["appearance_context"] = char_data.get("appearance_context", "在场景中出现")
        
        return simplified_data

    def _count_characters_by_importance(self, characters: Dict) -> Dict:
        """统计角色按重要性的分布"""
        counts = {"major": 0, "minor": 0, "unnamed": 0}
        for char_data in characters.values():
            importance = char_data.get("importance", "minor")
            if importance in counts:
                counts[importance] += 1
        return counts

    def get_novel_consistency_report(self, novel_title: str) -> Dict:
        """获取小说的整体一致性报告"""
        world_state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        if not os.path.exists(world_state_file):
            return {"error": "未找到该小说的世界状态数据"}
        
        try:
            with open(world_state_file, 'r', encoding='utf-8') as f:
                world_state = json.load(f)
            
            # 分析世界状态
            characters_count = len(world_state.get('characters', {}))
            items_count = len(world_state.get('items', {}))
            relationships_count = len(world_state.get('relationships', {}))
            skills_count = len(world_state.get('skills', {}))
            locations_count = len(world_state.get('locations', {}))
            
            return {
                "novel_title": novel_title,
                "world_state_summary": {
                    "characters": characters_count,
                    "items": items_count,
                    "relationships": relationships_count,
                    "skills": skills_count,
                    "locations": locations_count
                },
                "consistency_score": self._calculate_overall_consistency(world_state),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"生成一致性报告失败: {e}"}
    
    def _calculate_overall_consistency(self, world_state: Dict) -> float:
        """计算整体一致性分数"""
        # 简化的计算方法，实际可以根据具体需求调整
        total_elements = 0
        consistency_score = 0
        
        for category, elements in world_state.items():
            for element_id, element_data in elements.items():
                total_elements += 1
                # 检查元素是否有完整的更新记录
                if element_data.get('last_updated'):
                    consistency_score += 1
        
        return round(consistency_score / max(total_elements, 1) * 10, 2) if total_elements > 0 else 10.0