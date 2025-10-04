"""配置文件"""

Prompts = {
    "prompts": {
        "character_naming": """
要求：
- 名字长度2-3个字
- 符合分类风格特点
- 容易记忆且有特色

请返回JSON格式：{{"name": "主角名字"}}""",    
        "one_plans": """你是一位资深的番茄小说平台编辑。请根据目前番茄的风向结合用户提供的创意种子、分类，生成一套完整的小说方案。

请生成包含以下内容的单一方案：
1. 吸引人的小说标题（符合分类风格，8-15字）必须符合当前番茄读者喜好
2. 适合番茄的精彩的小说简介（200字左右，包含核心冲突和悬念）核心卖点使用[如（系统流）]圈起，放在开头，简介中使用主角名字
3. 创作核心方向（明确的故事定位和卖点），需要有多个卖点
4. 目标读者群体
5. 竞争优势分析
6. 融入数据洞察: 参考番茄平台热门关键词，要求方案基于这些趋势优化。

请确保方案完全符合提供的分类风格和主角设定。

请按照以下JSON格式输出：
{
    "title": "小说标题",
    "synopsis": "小说简介",
    "core_direction": "创作核心方向和卖点",
    "target_audience": "针对的读者群体",
    "competitive_advantage": "竞争优势分析"
}""",
        "plan_quality_evaluation": """你是一位资深的网络小说编辑和营销专家，特别擅长番茄小说平台。请对提供的小说方案进行专业质量评价。

请从以下维度进行评价：
1. 书名吸引力：是否符合分类风格、是否吸引目标读者、是否易于传播
2. 简介质量：是否包含核心冲突和悬念、能否引发读者兴趣、文笔是否流畅
3. 与创意种子的匹配度：是否充分体现了创意种子的核心概念
4. 商业潜力：是否符合当前番茄小说平台的流行趋势

请严格按照以下JSON格式输出评价结果：
{
    "overall_score": 总体评分（0-10分）,
    "title_evaluation": {
        "score": 书名评分（0-10分）,
        "strengths": ["优点1", "优点2"],
        "weaknesses": ["缺点1", "缺点2"],
        "suggestions": ["改进建议1", "改进建议2"]
    },
    "synopsis_evaluation": {
        "score": 简介评分（0-10分）,
        "strengths": ["优点1", "优点2"],
        "weaknesses": ["缺点1", "缺点2"],
        "suggestions": ["改进建议1", "改进建议2"]
    },
    "creative_seed_match": 与创意种子的匹配度（0-10分）,
    "commercial_potential": 商业潜力评分（0-10分）,
    "quality_verdict": "质量判定（优秀/良好/合格/需要优化/不合格）",
    "recommendation": "是否推荐使用此方案（true/false）"
}

请确保评分客观公正，为每个维度提供具体的优缺点分析。""",
        "market_analysis": """你是一位资深的网络小说编辑和营销专家，特别擅长番茄小说平台。请根据用户提供的创意种子，进行市场分析和卖点提炼。

请分析以下内容：
1. 目标读者群体
2. 核心卖点和差异化优势
3. 当前市场趋势和竞争分析
4. 流量潜力评估
5. 推荐写作策略

请按照以下JSON格式输出：
{
    "target_audience": "目标读者群体描述",
    "core_selling_points": ["卖点1", "卖点2", "卖点3"],
    "market_trend_analysis": "市场趋势分析",
    "competitive_advantage": "竞争优势分析",
    "commercial_potential": "流量潜力评估",
    "recommended_strategies": ["策略1", "策略2", "策略3"]
}""",
        "global_growth_planning": """你是一位资深的网络小说架构师。请根据目前番茄的风向结合为整部小说制定全面的成长规划。

# 制定要求
请基于提供的小说基础信息、世界观、角色设计和市场分析，制定一个贯穿全书的完整成长体系。

## 规划原则：
1. **系统性** - 所有成长系统要相互协调，形成有机整体
2. **渐进性** - 成长要循序渐进，符合读者期待
3. **戏剧性** - 关键成长节点要具有戏剧张力
4. **合理性** - 成长速度要符合逻辑，不能过快或过慢
5. **多样性** - 不同角色、势力要有不同的成长轨迹

## 重点考虑：
- 主角的成长曲线要满足全书的内容需求
- 势力发展要创造足够的冲突和转折
- 物品升级要提供持续的成就感
- 阶段性角色要服务各阶段的剧情需要

请按照以下结构化格式输出：
{
    "overview": "全书成长规划总体概述",
    "stage_framework": [
        {
            "stage_name": "阶段名称",
            "chapter_range": "章节范围",
            "core_objectives": ["核心目标1", "核心目标2"],
            "key_growth_themes": ["成长主题1", "成长主题2"],
            "milestone_events": ["里程碑事件1", "里程碑事件2"]
        }
    ],
    "character_growth_arcs": {
        "protagonist": {
            "overall_arc": "主角完整成长弧线",
            "stage_specific_growth": {
                "stage_name": {
                    "personality_development": "性格发展",
                    "ability_progression": "能力进展", 
                    "relationship_evolution": "关系演变"
                }
            }
        },
        "supporting_characters": {
            "character_name": {
                "growth_arc": "成长弧线",
                "key_development_stages": ["关键发展阶段"]
            }
        }
    },
    "faction_development_trajectory": {
        "faction_name": {
            "development_path": "发展路径",
            "key_expansion_points": ["关键扩张点"],
            "relationship_evolution": "关系演变"
        }
    },
    "ability_system_evolution": {
        "skill_progression_path": "技能进展路径",
        "equipment_upgrade_roadmap": "装备升级路线图",
        "breakthrough_milestones": ["突破里程碑"]
    },
    "emotional_development_journey": {
        "main_emotional_arc": "主要情感弧线",
        "relationship_development_phases": ["关系发展阶段"],
        "emotional_climax_points": ["情感高潮点"]
    }
}
""",
        "core_worldview": """你是一位顶级网络小说世界构建专家。请根据创意种子构建核心世界观框架。

请按照以下结构化格式输出：
{
    "era": "时代背景",
    "core_conflict": "核心冲突", 
    "overview": "世界概述",
    "hot_elements": ["热门元素1", "热门元素2"],
    "power_system": "力量体系描述",
    "social_structure": "社会结构",
    "main_plot_direction": "主线发展方向"
}""",
        "character_design": """你是一位资深角色设计师。请设计小说的主要角色。

请按照以下格式设计主角和重要配角：
{
    "main_character": {
        "name": "主角姓名",
        "personality": "性格特点",
        "background": "背景故事",
        "motivation": "核心动机",
        "growth_arc": "成长路线",
        "special_ability": "特殊能力",
        "character_flaws": "性格缺陷",
        "goal": "最终目标"
    },
    "important_characters": [
        {
            "name": "角色姓名",
            "role": "角色定位",
            "relationship": "与主角关系",
            "personality": "性格特点",
            "purpose": "在故事中的作用",
            "impact_on_plot": "对主线的影响"
        }
    ]
}""",
        "character_growth_design": """你是一位角色成长设计专家。请为主角和重要配角设计完整的成长路线。

请按照以下格式输出：
{
    "main_character_growth": {
        "power_progression": [
            {
                "stage": "成长阶段名称",
                "chapter_range": "章节范围",
                "abilities_gained": ["新能力1", "新能力2"],
                "personality_changes": "性格变化描述",
                "key_events": ["关键事件1", "关键事件2"]
            }
        ],
        "relationship_evolution": [
            {
                "character": "角色名称",
                "relationship_changes": [
                    {
                        "chapters": "章节范围", 
                        "relationship": "关系状态",
                        "key_interactions": ["关键互动"]
                    }
                ]
            }
        ]
    },
    "supporting_characters_growth": [
        {
            "character_name": "配角姓名",
            "growth_arc": "成长轨迹描述",
            "interaction_with_main": "与主角的互动发展",
            "final_destiny": "最终命运"
        }
    ]
}""",

        "faction_development_plan": """你是一位势力发展设计专家。请设计小说中主要势力的发展轨迹和冲突。

请按照以下格式输出：
{
    "factions_development": {
        "faction_name": {
            "development_stages": [
                {
                    "stage": "发展阶段",
                    "chapters": "章节范围", 
                    "power_level": "势力水平",
                    "key_events": ["关键事件"],
                    "territory_changes": "领土变化",
                    "relationship_changes": {
                        "allies": ["盟友变化"],
                        "enemies": ["敌人变化"]
                    }
                }
            ],
            "conflict_timeline": [
                {
                    "conflict_type": "冲突类型",
                    "involved_factions": ["涉及势力"],
                    "chapters": "发生章节", 
                    "outcome": "冲突结果",
                    "impact": "对格局影响"
                }
            ]
        }
    },
    "power_balance_evolution": [
        {
            "chapters": "章节范围",
            "balance_description": "势力平衡描述",
            "dominant_faction": "主导势力",
            "rising_threats": ["新兴威胁"]
        }
    ]
}""",

        "item_upgrade_system": """你是一位游戏系统设计专家。请设计小说中的物品升级体系。

请按照以下格式输出：
{
    "cultivation_system": {
        "realm_stages": [
            {
                "realm": "境界名称",
                "sub_stages": ["子境界1", "子境界2"],
                "lifespan": "寿命增长",
                "special_abilities": ["特殊能力"],
                "breakthrough_requirements": ["突破要求"],
                "typical_chapters": "通常达到的章节"
            }
        ]
    },
    "equipment_system": {
        "tiers": {
            "tier_name": {
                "levels": ["等级1", "等级2"],
                "materials": ["升级材料"],
                "special_effects": ["特殊效果"]
            }
        }
    },
    "skill_system": {
        "skill_trees": [
            {
                "tree_name": "技能树名称",
                "skills": [
                    {
                        "skill_name": "技能名称",
                        "unlock_condition": "解锁条件",
                        "upgrade_path": "升级路径",
                        "max_level": "最高等级"
                    }
                ]
            }
        ]
    }
}""",
        "stage_foreshadowing_planning": """你是一位资深的网络小说节奏控制专家。请为小说的特定阶段制定详细的伏笔铺垫计划。...""",
        "stage_content_planning": """你是一位资深的网络小说内容架构师。请为小说的特定阶段制定详细的内容规划。

# 阶段信息
**阶段名称**: {stage_name}
**章节范围**: {chapter_range}
**总章节数**: {total_chapters}

# 小说基础信息
**标题**: {novel_title}
**简介**: {novel_synopsis}
**核心世界观**: {worldview_overview}

# 当前阶段特性
{stage_characteristics}

# 内容规划要求
请为这个阶段制定详细的内容规划，专注于"写什么"，包含以下方面：

## 1. 人物成长规划
### 主角成长轨迹
- **性格演变**: 本阶段主角性格会发生什么变化？
- **能力提升**: 具体会掌握哪些新能力或技能？
- **动机深化**: 主角的目标和动机会如何深化？
- **关系发展**: 与重要角色的关系如何变化？

### 配角发展计划
- **重要配角**: 哪些配角需要重点发展？
- **新角色引入**: 需要引入哪些新角色？
- **关系网络**: 角色关系网络如何演变？

## 2. 势力发展规划
### 势力格局变化
- **权力转移**: 势力间的权力平衡如何变化？
- **新联盟**: 会形成哪些新的联盟关系？
- **冲突升级**: 现有冲突如何升级或转化？
- **新兴势力**: 是否有新势力登场？

### 世界观扩展
- **新地域**: 需要展现哪些新地点或场景？
- **文化揭示**: 可以揭示哪些世界观细节？
- **体系完善**: 力量体系或社会体系如何完善？

## 3. 物品功法规划
### 能力突破路线
- **技能解锁**: 主角会解锁哪些新技能？
- **装备升级**: 重要装备如何升级或获得？
- **境界突破**: 修行境界或能力等级如何突破？
- **特殊机缘**: 会获得哪些特殊机缘或物品？

### 系统完善
- **规则揭示**: 需要揭示哪些系统规则？
- **限制突破**: 现有的限制如何被突破？
- **新功能解锁**: 系统会解锁哪些新功能？

## 4. 情感发展计划
### 情感线索
- **主要情感**: 主角的主要情感线如何发展？
- **次要情感**: 配角的情感线如何安排？
- **情感冲突**: 会有什么情感冲突或转折？

## 5. 关键里程碑
列出本阶段必须达成的关键成长节点，每个节点应包含：
- 具体成就
- 发生的大致章节位置
- 对后续剧情的影响

# 输出格式
{
    "stage_name": "{stage_name}",
    "chapter_range": "{chapter_range}",
    "character_growth_plan": {
        "protagonist_development": {
            "personality_evolution": "性格演变描述",
            "ability_advancement": ["新能力1", "新能力2"],
            "motivation_deepening": "动机深化描述",
            "key_growth_moments": [
                {
                    "moment": "成长时刻描述",
                    "approximate_chapter": "大致章节",
                    "impact": "对后续的影响"
                }
            ]
        },
        "supporting_characters_development": {
            "focus_characters": ["需要重点发展的配角"],
            "new_characters": ["需要引入的新角色"],
            "relationship_evolution": {
                "character1_character2": "关系变化描述"
            }
        }
    },
    "faction_development_plan": {
        "power_structure_changes": {
            "rising_powers": ["新兴势力"],
            "declining_powers": ["衰落势力"],
            "new_alliances": ["新联盟关系"]
        }
        "conflict_escalation": {
            "ongoing_conflicts": ["持续冲突及其升级"],
            "new_conflicts": ["新出现的冲突"]
        },
        "world_building_expansion": {
            "new_locations": ["新地点"],
            "cultural_revelations": ["文化揭示"],
            "system_refinements": ["体系完善"]
        }
    },
    "ability_equipment_plan": {
        "skill_progression": {
            "new_skills": ["新技能1", "新技能2"],
            "skill_upgrades": ["技能升级1", "技能升级2"]
        },
        "equipment_advancement": {
            "new_equipment": ["新装备"],
            "equipment_upgrades": ["装备升级"]
        },
        "breakthrough_moments": [
            {
                "breakthrough": "突破描述",
                "requirements": "突破条件",
                "consequences": "突破后果"
            }
        ],
        "system_evolution": {
            "rule_revelations": ["规则揭示"],
            "limitation_breakthroughs": ["限制突破"],
            "new_features": ["新功能解锁"]
        }
    },
    "emotional_development_plan": {
        "main_emotional_arc": "主要情感线发展",
        "secondary_emotional_arcs": ["次要情感线"],
        "emotional_conflicts": ["情感冲突"]
    },
    "key_milestones": [
        {
            "milestone": "里程碑描述",
            "chapter_range": "发生章节范围",
            "significance": "重要性说明"
        }
    ],
    "content_synopsis": "本阶段内容总体概述"
}
请确保规划具体、可执行，并与前后阶段自然衔接。
""",
        "stage_writing_planning": """你是一位资深的网络小说剧情架构师。请基于内容规划和伏笔计划，为小说的特定阶段制定详细的写作计划。
# 制定当前阶段写作计划
请根据以上信息，制定当前阶段的详细写作计划，特别包含事件体系设计：

## 1. 阶段目标分解
- **主要目标**: 本阶段需要完成的核心目标
- **次要目标**: 支撑主要目标的次要目标
- **里程碑**: 关键节点和检查点

## 2. 事件体系设计（本阶段重点）
请为本阶段设计完整的事件体系：

### 重大事件 (1-2个)
- **事件名称**: 体现阶段核心冲突的重大事件
- **持续时间**: 3-8章
- **目标**: 推动阶段核心目标
- **关键节点**: 开始、发展、高潮、结束

### 大事件 (2-3个) 
- **事件名称**: 支撑重大事件的次级事件
- **持续时间**: 2-4章
- **目标**: 为重大事件做准备或收尾
- **关联性**: 与重大事件的逻辑关系

### 普通事件 (若干)
- **事件名称**: 日常推进事件
- **发生章节**: 具体章节位置
- **目标**: 推进支线或角色发展

## 3. 情节推进策略
- **主线推进**: 如何通过事件推进主要情节
- **支线安排**: 支线剧情的安排和时机
- **节奏控制**: 快慢节奏的分布

## 4. 角色发展计划
- **主角成长**: 主角在本阶段的发展轨迹
- **配角塑造**: 重要配角的塑造计划
- **关系发展**: 角色关系的变化和发展

## 5. 冲突设计
- **主要冲突**: 本阶段的核心冲突
- **次要冲突**: 辅助冲突和矛盾
- **冲突升级**: 如何逐步升级冲突

## 6. 伏笔管理
- **新伏笔**: 需要埋设的新伏笔
- **旧伏笔**: 需要回收的旧伏笔
- **伏笔网络**: 伏笔之间的关联

# 输出格式
{{
    "stage_writing_plan": {{
        "stage_overview": "本阶段总体写作概述",
        "targets": {{
            "main_target": "主要目标",
            "secondary_targets": ["次要目标1", "次要目标2"],
            "milestones": ["里程碑1", "里程碑2"]
        }},
        "event_system": {{
            "overall_approach": "本阶段事件驱动方法论",
            "major_events": [
                {{
                    "name": "重大事件名称",
                    "type": "major_event",
                    "start_chapter": 开始章节,
                    "end_chapter": 结束章节,
                    "duration": 持续时间,
                    "significance": "事件重要性描述",
                    "main_goal": "主要目标",
                    "sub_goals": ["子目标1", "子目标2"],
                    "key_moments": ["关键时刻1", "关键时刻2"],
                    "character_development": "角色成长重点",
                    "aftermath": "后续影响"
                }}
            ],
            "big_events": [
                {{
                    "name": "大事件名称",
                    "type": "big_event", 
                    "start_chapter": 开始章节,
                    "end_chapter": 结束章节,
                    "main_goal": "主要目标",
                    "connection_to_major": "与重大事件的关联",
                    "role": "在阶段中的作用"
                }}
            ],
            "events": [
                {{
                    "name": "事件名称",
                    "type": "event",
                    "chapter": 发生章节,
                    "goal": "事件目标",
                    "connection_to_big": "与大事件的关联",
                    "outcome": "事件结果"
                }}
            ]
        }},
        "plot_strategy": {{
            "main_plot_advancement": "主线推进策略",
            "subplot_arrangement": "支线安排策略",
            "pace_control": "节奏控制策略"
        }},
        "character_development": {{
            "protagonist_growth": "主角成长计划",
            "supporting_characters": "配角塑造计划", 
            "relationship_development": "关系发展计划"
        }},
        "conflict_design": {{
            "main_conflict": "主要冲突设计",
            "secondary_conflicts": ["次要冲突1", "次要冲突2"],
            "conflict_escalation": "冲突升级策略"
        }},
        "foreshadowing_management": {{
            "new_foreshadowing": ["新伏笔1", "新伏笔2"],
            "old_foreshadowing_reveal": ["回收伏笔1", "回收伏笔2"],
            "foreshadowing_network": "伏笔网络设计"
        }}
    }},
    "chapter_specific_guidance": "基于当前章节位置的特别指导"
}}""",
        "overall_stage_plan": """你是一位顶级网络小说策划编辑。请根据创意种子和市场分析，制定全书的阶段计划。

# 输出格式
{
    "overall_stage_plan": {
        "opening_stage": {
            "chapter_range": "第1章-第{opening_end}章",
            "core_tasks": ["任务1", "任务2", "任务3"],
            "key_content": ["内容重点1", "内容重点2"],
            "writing_focus": "开局阶段详细写作重点描述"
        },
        "development_stage": {
            "chapter_range": "第{development_start}章-第{development_end}章",
            "core_tasks": ["任务1", "任务2", "任务3"],
            "key_content": ["内容重点1", "内容重点2"],
            "writing_focus": "发展阶段详细写作重点描述"
        },
        "climax_stage": {
            "chapter_range": "第{climax_start}章-第{climax_end}章", 
            "core_tasks": ["任务1", "任务2", "任务3"],
            "key_content": ["内容重点1", "内容重点2"],
            "writing_focus": "高潮阶段详细写作重点描述"
        },
        "ending_stage": {
            "chapter_range": "第{ending_start}章-第{ending_end}章",
            "core_tasks": ["任务1", "任务2", "任务3"],
            "key_content": ["内容重点1", "内容重点2"],
            "writing_focus": "收尾阶段详细写作重点描述"
        },
        "final_stage": {
            "chapter_range": "第{final_start}章-第{total_chapters}章",
            "core_tasks": ["任务1", "任务2", "任务3"],
            "key_content": ["内容重点1", "内容重点2"],
            "writing_focus": "结局阶段详细写作重点描述"
        }
    },
    "stage_transitions": {
        "opening_to_development": "从开局到发展的过渡重点",
        "development_to_climax": "从发展到高潮的过渡重点", 
        "climax_to_ending": "从高潮到收尾的过渡重点",
        "ending_to_final": "从收尾到结局的过渡重点"
    }
}""",
        "stage_writing_plan": """你是一位资深的网络小说策划编辑。请根据全书阶段计划和当前章节位置，制定当前阶段的详细写作计划，包括事件设计。

请严格按照以下JSON格式输出
""",
        "chapter_design": """你是一位资深的网络小说策划编辑。请为本章制定详细的写作设计方案。

# 设计要求
请制定详细的章节设计方案，必须严格遵循上述基础设定，包含以下要素：

## 1. 情节结构设计
- **开场场景**: 如何承接上一章结尾，吸引读者
- **冲突发展**: 本章的核心冲突和矛盾推进，必须与世界观和角色设定一致
- **高潮设置**: 本章的情感高潮或转折点
- **结尾悬念**: 如何设置悬念吸引下一章阅读

## 2. 角色表现设计
- **主角发展**: 主角在本章的性格展示和成长，必须符合角色设定
- **配角互动**: 重要配角的出场和作用，保持角色一致性
- **对话设计**: 关键对话的内容和目的，体现角色性格

## 3. 场景与环境设计
- **主要场景**: 本章发生的主要地点和环境，必须符合世界观
- **氛围营造**: 如何通过环境描写营造氛围
- **场景转换**: 不同场景之间的自然过渡

## 4. 写作技巧设计
- **叙事视角**: 采用的叙事角度和手法
- **节奏控制**: 快慢节奏的分布和把控
- **细节描写**: 重点细节的选择和描写方式

## 5. 伏笔与铺垫设计
- **新伏笔设置**: 本章需要埋设的新伏笔，与整体情节协调
- **旧伏笔回收**: 需要回收的前期伏笔
- **线索安排**: 重要线索的分布和揭示

## 6. 设定一致性检查
- **世界观一致性**: 确保所有元素符合世界观设定
- **角色一致性**: 确保角色行为符合性格设定
- **情节连贯性**: 确保与前后章节衔接自然

## 7. 阶段性角色运用设计
- **新角色引入**: 如何自然引入本章新出场的阶段性角色
- **现有角色互动**: 如何安排阶段性角色与主角的互动
- **角色功能实现**: 确保阶段性角色完成其剧情使命
- **退场铺垫**: 为即将退场的角色做好铺垫

## 8. 成长规划遵循
- **人物成长状态**: 确保角色表现符合当前成长阶段的能力和性格
- **势力发展状态**: 情节要反映当前的势力格局和冲突状态  
- **物品升级状态**: 角色使用的技能和装备要符合当前等级
- **阶段角色预期**: 如有需要，引入符合当前阶段需求的临时角色

# 输出格式
{{
    "chapter_number": {chapter_number},
    "design_overview": "本章设计总体概述，说明如何体现基础设定",
    "plot_structure": {{
        "opening_scene": "开场场景设计（包含如何承接上一章）",
        "conflict_development": "冲突发展设计（基于世界观和角色）", 
        "climax_point": "高潮点设计（情感或情节转折）",
        "ending_hook": "结尾悬念设计（吸引下一章）"
    }},
    "character_performance": {{
        "main_character_development": "主角发展设计（必须符合角色设定）",
        "supporting_characters_interaction": "配角互动设计（保持角色一致性）",
        "key_dialogues": ["关键对话1（体现角色性格）", "关键对话2"]
    }},
    "scene_environment": {{
        "main_scenes": ["场景1（符合世界观）", "场景2"],
        "atmosphere_building": "氛围营造设计",
        "scene_transitions": "场景转换设计"
    }},
    "writing_techniques": {{
        "narrative_perspective": "叙事视角设计",
        "pace_control": "节奏控制设计", 
        "detail_description": "细节描写重点"
    }},
    "foreshadowing_plan": {{
        "new_foreshadowing": ["新伏笔1", "新伏笔2"],
        "old_foreshadowing_reveal": ["回收伏笔1", "回收伏笔2"],
        "clue_arrangement": "线索安排设计"
    }},
    "consistency_check": {{
        "worldview_consistency": "世界观一致性说明",
        "character_consistency": "角色一致性说明", 
        "plot_continuity": "情节连贯性说明"
    }},
    "chapter_focus": "本章核心重点（必须包含：{main_plot_progress}）",
    "word_count_target": 2500,
    "setting_adherence": "如何遵循基础设定的说明"
}}""",

        "chapter_content_generation": """你是一位优秀的网络小说作家。请根据以下详细设计方案和基础设定，生成第{chapter_number}章的完整内容。

# 基础设定（必须严格遵循）
**小说标题**: 
{novel_title}
**小说简介**: 
{novel_synopsis}
{main_character_instruction}

# 章节详细设计方案
{chapter_design}

# 核心写作要求

## 1. 严格遵循设定
- **世界观一致性**: 所有元素必须符合世界观设定：
{worldview_info}
- **角色一致性**: 角色行为必须符合角色设定：
{character_info}
- **情节连贯性**: 必须遵循写作计划：
{stage_writing_plan}

## 2. 标题规范
- 8-15字，吸引力强，与内容高度相关
- 确保唯一性，不与已有章节重复
- 体现核心情节或转折点

## 3. 内容结构
- **字数**: 2200-3000字
- **开头**: 直接承接上一章结尾，避免断裂
- **结尾**: 设置悬念，吸引继续阅读

## 4. 叙事风格
- **对话占比**: 50%以上，生活化，有火药味
- **爽点设置**: 至少1个小爽点（打脸、发现线索等）
- **网络热梗**: 自然融入，古今碰撞，不生硬
- **情感共鸣**: 日常场景中融入引发共鸣的细节

## 5. 质量控制
- 严格遵循设计方案和基础设定，不擅自添加重大新设定
- 保持角色性格和世界观一致性
- 避免AI痕迹：不用标记性语言、机械化结构
- 语言自然流畅，避免模式化表达

## 6. 章节衔接控制
- **开头衔接**: 本章开头必须自然承接上一章的结尾，不能突兀
- **情节连贯**: 确保时间、地点、人物状态的连续性
- **悬念处理**: 妥善处理上一章留下的悬念，同时设置新的悬念
- **过渡自然**: 场景转换和情节推进要流畅自然
- **结尾悬念**: 结尾尽可能保持悬念，增加读者阅读下一章

## 段落分段要求：
- **对话分段**：每个角色的对话单独成段，增强可读性
- **场景转换**：时间、地点、视角变化时必须分段
- **情绪节奏**：紧张、舒缓等情绪变化处合理分段
- **段落长度**：单段一般不超过200字，避免大段文字
- **手机友好**：考虑手机屏幕显示，段落要短小精悍
- **悬念设置**：关键信息或悬念点可单独成段强调
- **动作描写**：重要动作描写可独立分段突出视觉效果

## 必须满足：
- **内容长度**：必须2000字以上
- **内容格式**：必须中文符号习惯

# 输出格式
{{
    "chapter_number": {chapter_number},
    "chapter_title": "章节标题",
    "content": "章节内容",
    "word_count": 字数,
    "plot_advancement": "推动的主要情节",
    "character_development": "角色成长变化", 
    "key_events": ["关键事件1", "关键事件2"],
    "next_chapter_hook": "下一章悬念",
    "connection_to_previous": "与上一章的衔接",
    "design_followed": "是否遵循设计方案",
    "setting_adherence": "基础设定遵循情况"
}}
""",
        
        "chapter_quality_assessment": """你是一位资深的网络小说编辑和质量评估专家。请对以下章节内容进行专业评估。

# 评估标准（满分10分）
1. 情节连贯性（2分）：
2. 角色一致性（2分）：
3. 章节衔接（2分）：
4. 文笔质量（2分）：
5. AI痕迹检测（2分）：

# 需要评估的章节信息
**章节信息**：
- 章节编号：第{chapter_number}章
- 章节标题：{chapter_title}
- 总字数：{word_count}字

**上下文信息**：
- 小说标题：{novel_title}
- 前情提要：{previous_summary}
- 本章在整体结构中的位置：第{chapter_number}/{total_chapters}章

**章节内容**：
{chapter_content}

# 评估要求
请严格按照以下JSON格式输出评估结果：
{{
    "overall_score": 总体评分（0-10分）,
    "detailed_scores": {{
        "plot_coherence": 情节连贯性得分,
        "character_consistency": 角色一致性得分, 
        "chapter_connection": 章节衔接得分,
        "writing_quality": 文笔质量得分,
        "ai_artifacts_detected": AI痕迹得分（满分2分，发现一处痕迹-1分）,
        "emotional_impact": 爽点设置得分
    }},
    "strengths": ["优点1", "优点2", "优点3"],
    "weaknesses": ["缺点1", "缺点2", "缺点3"],
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "quality_verdict": "质量判定（优秀/良好/合格/需要优化/需要重写）",
    "connection_analysis": "本章与上一章的衔接分析",
    "ai_artifacts_analysis": "检测到的AI痕迹类型和具体位置分析",
    "consistency_check": "与整体设定的一致性检查"
}}""",

        "chapter_optimization": """你是一位经验丰富的网络小说优化编辑。请根据质量评估结果对以下章节内容进行优化。

# 优化要求
基于以下评估结果，对章节内容进行针对性优化：
{assessment_results}

# 特别注意消除AI痕迹
- 移除所有明显的标记性语言（如**伏笔植入：**等）
- 避免机械化的结构提示和编号式叙述
- 减少模式化表达和固定句式
- 使语言更加自然流畅，符合人类写作习惯

# 需要优化的章节
**原始章节内容**：
{original_content}

# 优化重点
1. {priority_fix_1}
2. {priority_fix_2}
3. {priority_fix_3}

# 优化原则
- 保持原有情节主线不变
- 优化语言表达，增强可读性
- 加强章节衔接，确保情节连贯
- 强化爽点设置，提升阅读体验
- 保持角色性格一致性
- 重点消除AI生成痕迹，使内容更加自然

# 输出要求
请输出优化后的完整章节内容（2000-3000字），严格按照以下JSON格式：
{{
    "optimized_content": "优化后的完整章节内容",
    "optimization_summary": "优化内容总结",
    "changes_made": ["具体修改1", "具体修改2", "具体修改3"],
    "word_count": 优化后字数,
    "quality_improvement": "质量提升说明",
    "ai_artifacts_removed": "已消除的AI痕迹列表"
}}""",

        "market_analysis_quality_assessment": """你是一位网络小说市场分析专家。请评估以下市场分析报告的质量。

# 评估维度（满分10分）：
1. 目标读者定位准确性（2分）
2. 核心卖点突出性（2分） 
3. 市场趋势分析合理性（2分）
4. 竞争优势分析深度（2分）
5. 推荐策略可行性（2分）

# 评估要求：
请严格按照以下JSON格式输出评估结果：
{{
    "overall_score": 总体评分（0-10分）,
    "detailed_scores": {{
        "audience_targeting": 目标读者定位得分,
        "selling_points": 核心卖点得分,
        "trend_analysis": 趋势分析得分,
        "competitive_analysis": 竞争分析得分,
        "strategy_feasibility": 策略可行性得分
    }},
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["缺点1", "缺点2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "quality_verdict": "质量判定（优秀/良好/合格/需要优化）"
}}""",

        "writing_plan_quality_assessment": """你是一位网络小说策划专家。请评估以下写作计划的质量。

# 评估维度（满分10分）：
1. 写作思路清晰度（2分）
2. 章节节奏合理性（2分）
3. 关键情节规划质量（2分）
4. 角色成长路线明确性（2分）
5. 重大事件设计精彩度（2分）

# 需要评估的内容：
{content}

# 评估要求：
请严格按照以下JSON格式输出评估结果：
{{
    "overall_score": 总体评分（0-10分）,
    "detailed_scores": {{
        "writing_approach": 写作思路得分,
        "chapter_rhythm": 章节节奏得分,
        "plot_planning": 情节规划得分,
        "character_growth": 角色成长得分,
        "event_design": 事件设计得分
    }},
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["缺点1", "缺点2"], 
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "quality_verdict": "质量判定（优秀/良好/合格/需要优化）"
}}""",

        "core_worldview_quality_assessment": """你是一位网络小说世界构建专家。请评估以下世界观框架的质量。

# 评估维度（满分10分）：
1. 时代背景吸引力（2分）
2. 核心冲突张力（2分）
3. 世界概述完整性（2分）
4. 热门元素契合度（2分）
5. 力量体系合理性（2分）

# 评估要求：
请严格按照以下JSON格式输出评估结果：
{{
    "overall_score": 总体评分（0-10分）,
    "detailed_scores": {{
        "era_background": 时代背景得分,
        "core_conflict": 核心冲突得分,
        "world_overview": 世界概述得分,
        "hot_elements": 热门元素得分,
        "power_system": 力量体系得分
    }},
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["缺点1", "缺点2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "quality_verdict": "质量判定（优秀/良好/合格/需要优化）"
}}""",

        "character_design_quality_assessment": """你是一位角色设计专家。请评估以下角色设计的质量。

评估维度：
1. 角色立体性 (2分): 角色性格和背景是否立体丰满
2. 动机合理性 (2分): 角色行为和动机是否合理
3. 成长空间 (2分): 角色是否有足够的成长空间
4. 关系设计 (2分): 角色关系设计是否合理有趣
5. 故事适配性 (2分): 角色是否适合故事发展和世界观

# 评估要求：
请严格按照以下JSON格式输出评估结果：
{{
    "overall_score": 总体评分（0-10分）,
    "detailed_scores": {{
        "main_character": 主角设计得分,
        "background": 背景合理性得分,
        "motivation": 动机清晰度得分,
        "supporting_characters": 配角设计得分,
        "relationships": 角色关系得分
    }},
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["缺点1", "缺点2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "quality_verdict": "质量判定（优秀/良好/合格/需要优化）"
}}""",

        # 添加优化提示词
        "market_analysis_optimization": """你是一位市场分析优化专家。请根据以下评估结果优化市场分析报告。

# 优化要求：
请保持原有结构，针对评估指出的问题进行优化，提升内容质量。
请输出优化后的完整市场分析报告，使用相同的JSON格式。""",

        "writing_plan_optimization": """你是一位写作计划优化专家。请根据以下评估结果优化写作计划。

# 原始内容：
{original_content}

# 评估结果：
{assessment_results}

# 优化重点：
{priority_fixes}

# 优化要求：
请保持原有结构，针对评估指出的问题进行优化，提升内容质量。
请输出优化后的完整写作计划，使用相同的JSON格式。""",

        "core_worldview_optimization": """你是一位世界观优化专家。请根据以下评估结果优化世界观框架。


优化要求:
1. 保持核心设定不变
2. 重点解决评估中发现的问题
3. 提升世界观的完整性和逻辑性
4. 加强创新元素和独特性
5. 丰富设定细节和深度

请保持原有结构，针对评估指出的问题进行优化，提升内容质量。
请输出优化后的完整世界观框架，使用相同的JSON格式。""",

        "character_design_optimization": """你是一位角色设计优化专家。请根据以下评估结果优化角色设计。

# 优化要求：

1. 保持核心角色设定不变
1. 保持核心角色设定不变
2. 重点解决评估中发现的问题
3. 提升角色的立体性和真实感
2. 重点解决评估中发现的问题
3. 提升角色的立体性和真实感
4. 优化角色动机和成长设计
4. 优化角色动机和成长设计
5. 加强角色关系和互动设计

请输出优化后的完整角色设计，使用相同的JSON格式。"""
    }
}