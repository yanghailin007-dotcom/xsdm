"""质量评估器类 - 专注质量评估和优化"""

import re
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class QualityAssessor:
    def __init__(self, api_client, storage_path: str = "./quality_data"):
        self.api_client = api_client
        self.storage_path = storage_path
        
        # 确保存储目录存在
        os.makedirs(storage_path, exist_ok=True)
        
        # 内化质量阈值配置
        self.quality_thresholds = {
            "excellent": 9.5,
            "good": 9.0,
            "acceptable": 8.5,
            "needs_optimization": 8.0,
            "needs_rewrite": 6.0
        }
        
        # 优化配置
        self.optimization_settings = {
            "quality_thresholds": self.quality_thresholds,
            "skip_optimization_conditions": {
                "min_score_skip": 8.5,
                "min_ai_score_skip": 1.8,
                "word_count_range": [2500, 3500],
                "min_score_with_good_words": 8.0
            },
            "optimization_intensity": {
                "high": {"threshold": 7.0, "max_issues": 5, "description": "重点优化"},
                "medium": {"threshold": 8.0, "max_issues": 3, "description": "中度优化"}, 
                "low": {"threshold": 8.5, "max_issues": 2, "description": "轻微优化"}
            }
        }
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
        # 保存章节评估数据
        chapter_file = os.path.join(self.storage_path, f"{novel_title}_chapter_{chapter_number}.json")
        try:
            with open(chapter_file, 'w', encoding='utf-8') as f:
                json.dump(assessment_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存章节评估数据失败: {e}")
        
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

    def detect_ai_artifacts(self, content: str) -> List[str]:
        """检测AI痕迹"""
        artifacts = []
        
        marker_patterns = [
            r'\*\*.*?：\*\*',
            r'【.*?】',
            r'第一[点、]|第二[点、]|第三[点、]',
            r'首先，|其次，|然后，|最后，',
            r'总的来说，|综上所述，|总而言之，',
            r'伏笔植入|铺垫手法|情节设计|结构安排',
            r'人物塑造|角色刻画|性格描写|形象建立',
            r'主题表达|思想内涵|深层意义|价值取向',
            r'情感渲染|气氛营造|情绪铺垫|感染力',
            r'叙事视角|叙述方式|描写手法|表现技巧',
            r'节奏控制|张弛有度|高潮部分|结局处理',
            r'象征意义|隐喻手法|对比运用|反复强调',
            r'在此基础上，|进一步来说，|值得注意的是，',
            r'从另一个角度|换而言之|具体而言',
            r'需要指出的是|值得关注的是|不容忽视的是',
            r'^[\d一二三四五六七八九十]、',
            r'^[•\-*]\s',
            r'^[A-Za-z]\.',
            r'使故事更加|让情节更|增强了作品的',
            r'提升了文章的|丰富了内容的|深化了主题的',
            r'达到了.*效果|产生了.*影响|具有.*价值',
            r'人物关系方面，|角色互动上，|彼此之间',
            r'父子关系|母女关系|夫妻关系|朋友关系',
            r'矛盾冲突|情感纠葛|关系发展|互动模式',
            r'开头部分|中间段落|结尾处|整体结构',
            r'起承转合|前后呼应|层层递进|环环相扣',
            r'艺术特色|文学价值|创作特点|风格特征',
            r'语言优美|文字精炼|表达生动|描写细腻'
        ]
        
        for pattern in marker_patterns:
            matches = re.findall(pattern, content)
            if matches:
                artifacts.append(f"模式化标记: {matches[:3]}")
        
        sentences = re.split(r'[。！？]', content)
        
        for sentence in sentences:
            if len(sentence) > 10:
                if "一边" in sentence and sentence.count("一边") > 1:
                    artifacts.append("重复句式: 一边...一边...")
                if "不仅" in sentence and "而且" in sentence:
                    artifacts.append("重复句式: 不仅...而且...")
        
        overused_words = ["显然", "无疑", "实际上", "事实上", "可以说", "值得注意的是"]
        for word in overused_words:
            count = content.count(word)
            if count > 3:
                artifacts.append(f"过度使用词汇: '{word}'出现{count}次")
        
        return artifacts[:10]
    
    def assess_chapter_quality(self, assessment_params: Dict) -> Optional[Dict]:
        """评估章节质量（包含一致性检查）"""
        user_prompt = self._generate_chapter_assessment_prompt(assessment_params)
        result = self.api_client.generate_content_with_retry(
            "chapter_quality_assessment", 
            user_prompt, 
            temperature=0.3, 
            purpose="章节质量评估"
        )
        
        # 如果评估成功，保存数据并处理角色状态
        if result and 'overall_score' in result:
            novel_title = assessment_params.get('novel_title', 'unknown')
            chapter_number = assessment_params.get('chapter_number', 0)
            
            # 处理角色状态变化
            character_status_changes = result.get('character_status_changes', [])
            for status_change in character_status_changes:
                character_name = status_change.get('character_name')
                status = status_change.get('status')
                if character_name and status in ['dead', 'exited']:
                    print(f"🔄 AI检测到角色状态变化: {character_name} -> {status}")
                    self._simplify_character_status(novel_title, character_name, status, chapter_number)
            
            # 处理世界状态增量更新
            if 'world_state_changes' in result:
                self._update_world_state_incrementally(novel_title, result['world_state_changes'], chapter_number)
                # 移除changes，保存完整的世界状态到结果中用于后续处理
                result['updated_world_state'] = self.current_world_state
            
            self.save_assessment_data(novel_title, chapter_number, result)
            self.update_character_development_from_assessment(novel_title, result, chapter_number)
                
        return result

    def _update_world_state_incrementally(self, novel_title: str, changes: Dict, chapter_number: int):
        """增量更新世界状态 - 地点用最新状态覆盖"""
        # 加载当前世界状态
        current_state = self.load_previous_assessments(novel_title)
        if not current_state:
            current_state = {
                "characters": {},
                "items": {}, 
                "relationships": {},
                "skills": {},
                "locations": {}  # 地点初始化为空
            }
        
        # 应用增量更新
        for category, elements in changes.items():
            if category not in current_state:
                current_state[category] = {}
            
            # 特殊处理地点：完全覆盖，不保留旧状态
            if category == "locations":
                # 清空现有地点，用最新的覆盖
                current_state[category] = {}
                for element_id, element_data in elements.items():
                    # 只保存最新状态，不保留历史
                    element_data['first_appearance'] = chapter_number
                    element_data['last_updated'] = chapter_number
                    current_state[category][element_id] = element_data
            else:
                # 其他类别（角色、物品、关系、技能）保持增量更新
                for element_id, element_data in elements.items():
                    if element_id in current_state[category]:
                        # 更新现有元素
                        current_state[category][element_id].update(element_data)
                        current_state[category][element_id]['last_updated'] = chapter_number
                    else:
                        # 新增元素
                        element_data['first_appearance'] = chapter_number
                        element_data['last_updated'] = chapter_number
                        current_state[category][element_id] = element_data
        
        # 保存更新后的世界状态
        self.current_world_state = current_state
        state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(current_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存世界状态失败: {e}")

    def _generate_chapter_assessment_prompt(self, params: Dict) -> str:
        """生成章节质量评估提示词（包含一致性检查）- 简化角色发展评估"""
        
        # 加载之前的世界状态
        novel_title = params.get('novel_title', 'unknown')
        previous_world_state = self.load_previous_assessments(novel_title)
        
        world_state_str = json.dumps(previous_world_state, ensure_ascii=False, indent=2) if previous_world_state else "{}"

        character_development_data = self._load_character_development_data(novel_title)
        character_development_str = json.dumps(character_development_data, ensure_ascii=False, indent=2) if character_development_data else "{}"        
        
        return f"""
    你是一位资深的番茄小说内容分析师与世界观架构师。
    你的任务是根据提供的章节信息和之前的世界观状态，进行全面的质量评估，并识别出本章节对世界观的具体变化。

    ### 1. 小说信息
    - **小说标题**: {params.get('novel_title', '未知')}
    - **章节标题**: {params.get('chapter_title', '未知')}
    - **章节编号**: {params.get('chapter_number', '未知')}
    - **前情提要**: {params.get('previous_summary', '无')}

    ### 2. 上一章世界观状态 (用于一致性检查)
    {world_state_str}

    现有角色发展数据:
    {character_development_str}

    章节内容预览:
    {params.get('chapter_content', '')}

    请按照以下JSON格式返回评估结果：
    {{
        "overall_score": "number (0-10，基于细分维度计算)",
        "quality_verdict": "string (根据分数评定，如'优秀', '良好', '合格'等)",
        "strengths": "array of strings (列出章节的主要优点)",
        "weaknesses": "array of strings (列出章节的主要待改进方面)",
        "detailed_scores": {{
            "plot_pacing_and_appeal": "number (0-2)",
            "characterization_and_consistency": "number (0-2)", 
            "writing_quality_and_immersion": "number (0-2)",
            "structure_and_cohesion": "number (0-2)",
            "world_state_consistency": "number (0-2)"
        }},
        "consistency_issues": [
            {{
                "type": "string (枚举: CHARACTER, ITEM, RELATIONSHIP, SKILL, TIMELINE, LOCATION)",
                "description": "string (具体问题描述)", 
                "severity": "string (枚举: High, Medium, Low)",
                "suggestion": "string (修复建议)"
            }}
        ],
        "character_status_changes": [
            {{
                "character_name": "string",
                "status": "string (枚举: active, dead, exited)", 
                "reason": "string (状态变化原因)",
                "chapter": "number"
            }}
        ],
        "world_state_changes": {{
            // 只包含本章节新增或发生变化的世界状态元素
            "characters": {{
                // 只包含本章节新出现或属性发生变化的角色
                "新角色名或变化角色名": {{
                    "description": "string (角色描述)",
                    "attributes": "object (角色属性)",
                    // 注意：不要包含first_appearance和last_updated，系统会自动处理
                }}
            }},
            "items": {{
                // 只包含本章节新出现或状态发生变化的物品
                "新物品名或变化物品名": {{
                    "owner": "string (拥有者)",
                    "status": "string (物品状态)",
                    // 注意：不要包含first_appearance和last_updated，系统会自动处理
                }}
            }},
            "relationships": {{
                // 只包含本章节新建立或发生变化的关系
                "角色A-角色B": {{
                    "type": "string (关系类型)",
                    "description": "string (关系描述)",
                    // 注意：不要包含last_updated，系统会自动处理
                }}
            }},
            "skills": {{
                // 只包含本章节新出现或发生变化的技能
                "新技能名或变化技能名": {{
                    "owner": "string (拥有者)", 
                    "level": "string (技能等级)",
                    "description": "string (技能描述)",
                    // 注意：不要包含first_appearance和last_updated，系统会自动处理
                }}
            }},
            "locations": {{
                // 只包含本章节新出现或发生变化的地点
                "新地点名或变化地点名": {{
                    "description": "string (地点描述)",
                    // 注意：不要包含first_appearance和last_updated，系统会自动处理
                }}
            }}
        }},
        "character_development_assessment": {{
            // 专注于本章节的角色发展和名场面，不包含完整的角色模板
            "new_characters_introduced": [
                {{
                    "name": "string",
                    "role_type": "string (主角/重要配角/次要配角)", 
                    "initial_impression": "string (给读者的第一印象)",
                    "development_potential": "string (未来发展潜力)"
                }}
            ],
            "existing_characters_development": [
                {{
                    "name": "string",
                    "growth_shown": "string (本章展现的成长或变化)",
                    "consistency_issues": "string (与过往设定的不一致之处，若无则为'无')", 
                    "development_suggestions": [
                        "具体的发展建议1",
                        "具体的发展建议2"
                    ]
                }}
            ],
            "iconic_scenes_identified": [
                {{
                    "character": "string",
                    "scene_description": "string (场景具体描述)",
                    "trait_demonstrated": "string (场景展现的角色特质)",
                    "impact_level": "string (High/Medium/Low)",
                    "chapter": "number (发生章节)"
                }}
            ],
            "character_interactions": [
                {{
                    "characters": ["角色A", "角色B"],
                    "interaction_type": "string (对话/合作/冲突/情感交流等)",
                    "significance": "string (互动的重要性)",
                    "relationship_development": "string (对关系发展的影响)"
                }}
            ],
            "personality_revelations": [
                {{
                    "character": "string",
                    "trait_revealed": "string (揭示的性格特质)", 
                    "context": "string (揭示的情境)",
                    "consistency": "boolean (是否与之前设定一致)"
                }}
            ]
        }},
        "assessment_timestamp": "string (生成报告的ISO 8601格式时间戳，例如: '2024-05-16T12:00:00Z')"
    }}

    重要说明：
    1. world_state_changes 只包含本章节新增或发生变化的世界状态元素
    2. character_development_assessment 专注于角色发展和名场面，不包含完整的角色模板
    3. 对于已存在但未变化的元素，不要包含在返回数据中
    4. 系统会自动处理first_appearance和last_updated字段
    5. 保持与之前世界状态的一致性，只报告本章节带来的变化
    """

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
    
    def optimize_chapter_content(self, optimization_params: Dict) -> Optional[Dict]:
        """优化章节内容（包含一致性修复）"""
        user_prompt = self._generate_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "chapter_optimization", 
            user_prompt, 
            purpose="章节内容优化"
        )
        return result
    
    def _generate_optimization_prompt(self, params: Dict) -> str:
        """生成章节优化提示词（包含一致性修复）"""
        assessment = json.loads(params.get("assessment_results", "{}"))
        original_content = params.get("original_content", "")
        
        # 获取一致性问题和世界状态
        consistency_issues = assessment.get('consistency_issues', [])
        world_state_changes = assessment.get('world_state_changes', {})
        
        consistency_fixes = ""
        if consistency_issues:
            consistency_fixes = "需要修复的一致性问题和建议：\n"
            for issue in consistency_issues[:3]:  # 只处理前3个最严重的问题
                consistency_fixes += f"- {issue.get('type')}: {issue.get('description')} (严重程度: {issue.get('severity')})\n"
                consistency_fixes += f"  建议: {issue.get('suggestion')}\n"
        
        # 获取完整的世界状态用于参考
        novel_title = params.get('novel_title', 'unknown')
        full_world_state = self.load_previous_assessments(novel_title)
        
        return f"""
    请根据以下评估结果对章节内容进行优化，特别关注一致性问题的修复：

    质量评估结果:
    - 总体评分: {assessment.get('overall_score', 0)}/10分
    - 主要问题: {', '.join(assessment.get('weaknesses', []))}
    - 优化强度: {params.get('optimization_intensity', '中度优化')}

    {consistency_fixes}

    本章节世界状态变化:
    {json.dumps(world_state_changes, ensure_ascii=False, indent=2) if world_state_changes else "无新增变化"}

    完整世界状态参考:
    {json.dumps(full_world_state, ensure_ascii=False, indent=2) if full_world_state else "无"}

    需要重点优化的方面:
    1. {params.get('priority_fix_1', '提升整体质量')}
    2. {params.get('priority_fix_2', '')}
    3. {params.get('priority_fix_3', '')}

    原始内容:
    {original_content}

    优化要求:
    1. 保持原有情节和核心内容不变
    2. 重点解决上述质量问题
    3. 消除明显的AI生成痕迹
    4. 修复所有一致性相关问题
    5. 确保与之前章节的世界状态保持一致

    ## 2. 写作风格要求
    **写作风格**: {params.get('writing_style_guide', '无特定要求，请保持语言流畅自然。')}

    ## 3. 内容要求
    - 输出正文超过2000字
    - 章节结尾设置悬念，引导读者继续阅读
    - 保持情节推进和角色发展
    - 确保角色、物品、关系、技能等要素的一致性

    请返回优化后的完整章节内容，并按照以下JSON格式输出：
    {{
        "content": "优化后的完整章节内容",
        "optimization_summary": "优化总结", 
        "changes_made": ["具体修改1", "具体修改2", "具体修改3"],
        "consistency_fixes": ["一致性修复1", "一致性修复2"],
        "word_count": 优化后字数,
        "quality_improvement": "质量提升说明",
        "world_state_changes": {{
            // 优化过程中产生的世界状态变化（增量）
        }}
    }}
    """
    
    def get_quality_verdict(self, score: float) -> Tuple[str, str]:
        """获取质量评级"""
        thresholds = self.quality_thresholds
        
        if score >= thresholds["excellent"]:
            return "优秀", "质量很高，无需优化"
        elif score >= thresholds["good"]:
            return "良好", "质量良好，可轻微优化"
        elif score >= thresholds["acceptable"]:
            return "合格", "建议优化以提升质量"
        elif score >= thresholds["needs_optimization"]:
            return "需要优化", "需要重点优化"
        else:
            return "需要重写", "质量不合格，建议重写"
    
    def should_optimize_chapter(self, assessment: Dict) -> Tuple[bool, str]:
        """判断是否需要优化章节（考虑一致性因素）"""
        score = assessment.get("overall_score", 0)
        consistency_issues = assessment.get("consistency_issues", [])
        
        # 如果有严重的一致性问題，即使分数较高也需要优化
        severe_consistency_issues = [issue for issue in consistency_issues 
                                   if issue.get('severity') == '高']
        
        thresholds = self.quality_thresholds
        
        if severe_consistency_issues:
            return True, f"存在{len(severe_consistency_issues)}个严重一致性问題，需要优化"
        
        if score >= thresholds["excellent"]:
            return False, "质量优秀，无需优化"
        elif score >= thresholds["good"]:
            return False, "质量良好，可选优化"
        elif score >= thresholds["acceptable"]:
            return True, "质量合格，建议优化"
        elif score >= thresholds["needs_optimization"]:
            return True, "需要优化提升质量"
        else:
            return True, "质量不合格，需要重点优化"

    def should_skip_optimization(self, assessment: Dict, chapter_data: Dict) -> Tuple[bool, str]:
        """判断是否应该跳过优化（考虑一致性因素）"""
        score = assessment.get("overall_score", 0)
        consistency_issues = assessment.get("consistency_issues", [])
        skip_config = self.optimization_settings["skip_optimization_conditions"]
        
        # 如果有严重一致性问題，不跳过优化
        severe_consistency_issues = [issue for issue in consistency_issues 
                                   if issue.get('severity') == '高']
        if severe_consistency_issues:
            return False, f"存在{len(severe_consistency_issues)}个严重一致性问題，需要优化"
        
        if score >= skip_config["min_score_skip"]:
            return True, "质量优秀，跳过优化"
        
        ai_score = assessment.get("detailed_scores", {}).get("ai_artifacts_detected", 2)
        if ai_score >= skip_config["min_ai_score_skip"]:
            return True, "AI痕迹较少，跳过优化"
        
        word_count = chapter_data.get("word_count", 0)
        word_range = skip_config["word_count_range"]
        if word_range[0] <= word_count <= word_range[1]:
            if score >= skip_config["min_score_with_good_words"]:
                return True, "字数合适且质量良好，跳过优化"
        
        return False, "需要优化"
    
    def get_optimization_intensity(self, score: float, consistency_issues: List = None) -> Dict:
        """获取优化强度配置（考虑一致性因素）"""
        intensity_configs = self.optimization_settings["optimization_intensity"]
        
        # 如果有严重一致性问題，提高优化强度
        severe_issues = [issue for issue in (consistency_issues or []) 
                        if issue.get('severity') == '高']
        
        if severe_issues:
            return {
                "max_issues": len(severe_issues) + 2,
                "description": f"重点优化（包含{len(severe_issues)}个严重一致性问題）"
            }
        
        if score < intensity_configs["high"]["threshold"]:
            return intensity_configs["high"]
        elif score < intensity_configs["medium"]["threshold"]:
            return intensity_configs["medium"]
        elif score < intensity_configs["low"]["threshold"]:
            return intensity_configs["low"]
        else:
            return {"max_issues": 0, "description": "无需优化"}
        
    def _quick_optimize_chapter(self, chapter_data: Dict, assessment: Dict) -> Optional[Dict]:
        """快速优化章节（包含一致性修复）"""
        score = assessment.get("overall_score", 0)
        weaknesses = assessment.get("weaknesses", [])
        consistency_issues = assessment.get("consistency_issues", [])
        
        intensity_config = self.get_optimization_intensity(score, consistency_issues)
        
        if intensity_config["max_issues"] == 0:
            return None
        
        # 优先处理一致性问題
        priority_issues = []
        severe_consistency = [issue for issue in consistency_issues 
                            if issue.get('severity') == '高']
        
        # 添加严重一致性问題
        for issue in severe_consistency[:2]:
            priority_issues.append(f"修复一致性问題: {issue.get('description')}")
        
        # 添加其他弱点
        remaining_slots = intensity_config["max_issues"] - len(priority_issues)
        if remaining_slots > 0:
            priority_issues.extend(weaknesses[:remaining_slots])
        
        if not priority_issues:
            if score < self.quality_thresholds["needs_optimization"]:
                priority_issues = ["提升情节连贯性", "增强角色表现", "改善文笔质量"]
            else:
                return None
        
        optimization_params = {
            "assessment_results": json.dumps({
                "weaknesses": weaknesses,
                "consistency_issues": consistency_issues,
                "updated_world_state": assessment.get("updated_world_state", {}),
                "overall_score": score,
                "optimization_intensity": intensity_config["description"]
            }, ensure_ascii=False),
            "original_content": chapter_data.get("content", ""),
            "priority_fix_1": priority_issues[0] if len(priority_issues) > 0 else "提升整体质量",
            "priority_fix_2": priority_issues[1] if len(priority_issues) > 1 else "",
            "priority_fix_3": priority_issues[2] if len(priority_issues) > 2 else "",
            "optimization_intensity": intensity_config["description"]
        }
        
        return self.optimize_chapter_content(optimization_params)   
         
    def quick_assess_chapter_quality(self, chapter_content: str, chapter_title: str, 
                                chapter_number: int, novel_title: str, previous_summary: str, 
                                word_count: int = 0) -> Dict:
        """快速评估章节质量（包含一致性检查）"""
        # 加载之前的世界状态
        self.current_world_state = self.load_previous_assessments(novel_title)
        
        return self.assess_chapter_quality({
            "chapter_content": chapter_content,
            "chapter_title": chapter_title,
            "chapter_number": chapter_number,
            "novel_title": novel_title,
            "previous_summary": previous_summary,
            "total_chapters": 100,  # 默认值，实际使用时应该传入
            "word_count": word_count
        })
    
    def assess_market_analysis_quality(self, market_analysis: Dict) -> Dict:
        """评估市场分析质量"""
        if not market_analysis:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_market_analysis_assessment_prompt(market_analysis)
        
        result = self.api_client.generate_content_with_retry(
            "market_analysis_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="市场分析质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_market_analysis_assessment_prompt(self, market_analysis: Dict) -> str:
        """生成市场分析评估提示词"""
        return f"""
请评估以下市场分析内容的质量：

市场分析内容:
{json.dumps(market_analysis, ensure_ascii=False, indent=2)}

评估维度：
1. 市场洞察深度 (2分): 对目标市场和读者需求的分析是否深入
2. 竞争分析准确性 (2分): 对竞争环境和自身优势的分析是否准确
3. 卖点提炼有效性 (2分): 核心卖点和差异化优势是否清晰有力
4. 数据支撑充分性 (2分): 是否有充分的数据和市场依据支撑分析
5. 可行性评估 (2分): 提出的策略和方向是否具备可行性

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级",
    "strengths": ["优点列表"],
    "weaknesses": ["待改进方面列表"],
    "optimization_suggestions": ["优化建议列表"]
}}
"""

    def assess_writing_plan_quality(self, writing_plan: Dict) -> Dict:
        """评估写作计划质量"""
        if not writing_plan:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_writing_plan_assessment_prompt(writing_plan)
        
        result = self.api_client.generate_content_with_retry(
            "writing_plan_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="写作计划质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_writing_plan_assessment_prompt(self, writing_plan: Dict) -> str:
        """生成写作计划评估提示词"""
        return f"""
请评估以下写作计划的质量：

写作计划内容:
{json.dumps(writing_plan, ensure_ascii=False, indent=2)}

评估维度：
1. 结构合理性 (2分): 章节节奏和情节分布是否合理
2. 角色成长设计 (2分): 主角成长轨迹是否清晰合理
3. 冲突设计质量 (2分): 主要冲突和矛盾设计是否吸引人
4. 伏笔设计 (2分): 伏笔线和情感线设计是否有机融合
5. 可行性评估 (2分): 计划是否具备可执行性

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级",
    "strengths": ["优点列表"],
    "weaknesses": ["待改进方面列表"],
    "optimization_suggestions": ["优化建议列表"]
}}
"""

    def assess_core_worldview_quality(self, worldview: Dict) -> Dict:
        """评估世界观质量"""
        if not worldview:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_worldview_assessment_prompt(worldview)
        
        result = self.api_client.generate_content_with_retry(
            "core_worldview_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="世界观质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_worldview_assessment_prompt(self, worldview: Dict) -> str:
        """生成世界观评估提示词"""
        return f"""
请评估以下世界观设定的质量：

世界观内容:
{json.dumps(worldview, ensure_ascii=False, indent=2)}

"""

    def assess_character_design_quality(self, character_design: Dict) -> Dict:
        """评估角色设计质量"""
        if not character_design:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_character_design_assessment_prompt(character_design)
        
        result = self.api_client.generate_content_with_retry(
            "character_design_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="角色设计质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_character_design_assessment_prompt(self, character_design: Dict) -> str:
        """生成角色设计评估提示词"""
        return f"""
内容:
请根据你作为角色设计顾问的专业身份，使用系统提示中定义的评估体系和JSON格式，对以下角色设计进行全面评估。

待评估的角色设计内容：
{json.dumps(character_design, ensure_ascii=False, indent=2)}

"""

    def optimize_market_analysis(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化市场分析"""
        priority_fixes = "\n".join([f"- {weakness}" for weakness in assessment.get("weaknesses", [])[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": json.dumps(assessment, ensure_ascii=False),
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_market_analysis_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "market_analysis_optimization", 
            user_prompt, 
            purpose="市场分析优化"
        )
        return result

    def _generate_market_analysis_optimization_prompt(self, params: Dict) -> str:
        """生成市场分析优化提示词"""
        return f"""
请根据以下评估结果优化市场分析内容：

评估结果:
{params.get('assessment_results', '{}')}

需要重点优化的方面:
{params.get('priority_fixes', '')}

原始市场分析内容:
{params.get('original_content', '')}

优化要求:
1. 保持核心分析和结论不变
2. 重点解决评估中发现的问题
3. 提升分析的深度和说服力
4. 确保数据支撑充分
5. 优化表达方式和结构

请返回优化后的完整市场分析内容。
"""

    def optimize_writing_plan(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化写作计划"""
        priority_fixes = "\n".join([f"- {weakness}" for weakness in assessment.get("weaknesses", [])[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": json.dumps(assessment, ensure_ascii=False),
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_writing_plan_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "writing_plan_optimization", 
            user_prompt, 
            purpose="写作计划优化"
        )
        return result

    def _generate_writing_plan_optimization_prompt(self, params: Dict) -> str:
        """生成写作计划优化提示词"""
        return f"""
请根据以下评估结果优化写作计划：

评估结果:
{params.get('assessment_results', '{}')}

需要重点优化的方面:
{params.get('priority_fixes', '')}

原始写作计划内容:
{params.get('original_content', '')}

优化要求:
1. 保持核心情节结构不变
2. 重点解决评估中发现的问题
3. 提升计划的合理性和可行性
4. 优化节奏安排和情节分布
5. 加强角色成长和冲突设计

请返回优化后的完整写作计划内容。
"""

    def optimize_core_worldview(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化世界观"""
        priority_fixes = "\n".join([f"- {weakness}" for weakness in assessment.get("weaknesses", [])[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": json.dumps(assessment, ensure_ascii=False),
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_worldview_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "core_worldview_optimization", 
            user_prompt, 
            purpose="世界观优化"
        )
        return result

    def _generate_worldview_optimization_prompt(self, params: Dict) -> str:
        """生成世界观优化提示词"""
        return f"""
请根据以下评估结果优化世界观设定：

评估结果:
{params.get('assessment_results', '{}')}

需要重点优化的方面:
{params.get('priority_fixes', '')}

原始世界观内容:
{params.get('original_content', '')}

"""

    def optimize_character_design(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化角色设计"""
        priority_fixes = "\n".join([f"- {weakness}" for weakness in assessment.get("weaknesses", [])[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": json.dumps(assessment, ensure_ascii=False),
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_character_design_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "character_design_optimization", 
            user_prompt, 
            purpose="角色设计优化"
        )
        return result

    def _generate_character_design_optimization_prompt(self, params: Dict) -> str:
        """生成角色设计优化提示词"""
        return f"""
请根据以下评估结果优化角色设计：

评估结果:
{params.get('assessment_results', '{}')}

需要重点优化的方面:
{params.get('priority_fixes', '')}

原始角色设计内容:
{params.get('original_content', '')}

"""

    def calculate_quality_statistics(self, quality_records: Dict) -> Dict:
        """计算质量统计数据"""
        if not quality_records:
            return {}
        
        scores = []
        ai_scores = []
        detailed_scores = {
            "plot_coherence": [],
            "character_consistency": [],
            "chapter_connection": [],
            "writing_quality": [],
            "ai_artifacts_detected": [],
            "emotional_impact": []
        }
        
        for chapter_num, record in quality_records.items():
            assessment = record.get("assessment", {})
            overall_score = assessment.get("overall_score", 0)
            scores.append(overall_score)
            
            # 收集详细分数
            detailed = assessment.get("detailed_scores", {})
            for key in detailed_scores.keys():
                if key in detailed:
                    detailed_scores[key].append(detailed[key])
            
            # 特别收集AI痕迹分数
            ai_score = detailed.get('ai_artifacts_detected', 2)
            ai_scores.append(ai_score)
        
        if not scores:
            return {}
        
        # 计算统计信息
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        avg_ai_score = sum(ai_scores) / len(ai_scores) if ai_scores else 2
        
        # 计算质量分布
        quality_distribution = {
            "优秀": len([s for s in scores if s >= self.quality_thresholds["excellent"]]),
            "良好": len([s for s in scores if self.quality_thresholds["good"] <= s < self.quality_thresholds["excellent"]]),
            "合格": len([s for s in scores if self.quality_thresholds["acceptable"] <= s < self.quality_thresholds["good"]]),
            "需要优化": len([s for s in scores if s < self.quality_thresholds["acceptable"]])
        }
        
        # 计算AI痕迹分布
        ai_distribution = {
            "优秀(2分)": len([s for s in ai_scores if s == 2]),
            "良好(1.5-2分)": len([s for s in ai_scores if 1.5 <= s < 2]),
            "需改进(1-1.5分)": len([s for s in ai_scores if 1 <= s < 1.5]),
            "较差(<1分)": len([s for s in ai_scores if s < 1])
        }
        
        # 计算详细分数平均值
        avg_detailed_scores = {}
        for key, values in detailed_scores.items():
            if values:
                avg_detailed_scores[key] = round(sum(values) / len(values), 2)
        
        return {
            "total_chapters_assessed": len(scores),
            "average_score": round(avg_score, 2),
            "max_score": max_score,
            "min_score": min_score,
            "quality_distribution": quality_distribution,
            "average_detailed_scores": avg_detailed_scores,
            "ai_quality": {
                "average_ai_score": round(avg_ai_score, 2),
                "ai_distribution": ai_distribution,
                "chapters_with_ai_artifacts": len([s for s in ai_scores if s < 2])
            }
        }

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