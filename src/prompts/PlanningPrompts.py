"""规划类提示词配置"""

class PlanningPrompts:
    def __init__(self):
        self.prompts = {
            "emotional_development_planning": """
你是一位资深网络小说角色成长与情感发展策划专家。请基于提供的角色设定、世界观和全书大纲，为主角和核心配角制定详细的成长与情感发展计划。

**核心任务**：
1. **主角成长线**：为主角设计一个从开局到结局的成长弧线，包括能力、心智、地位、情感等方面的变化。
2. **配角群像**：为核心配角设计各自的成长或转变路径，确保他们不是静态的背景板。
3. **情感发展**：规划主角与重要角色之间（如爱情、复仇、联盟、支配）的情感关系如何随剧情推进而演变。
4. **阶段对应**：将成长计划与"起承转合"四阶段对应，明确每个阶段需要达成的成长目标。

**输出要求**：
请严格按照以下JSON格式输出，不要包含任何额外的解释文字：
```json
{
    "protagonist_growth": {
        "opening_stage": {
            "personality_development": "主角在开局阶段（1-30章）的性格特点、初始能力和主要困境。",
            "ability_advancement": ["初始能力1", "初始能力2"],
            "key_growth_points": ["初期关键成长点1", "初期关键成长点2"]
        },
        "development_stage": {
            "personality_development": "主角在发展阶段（31-100章）的性格如何变化，遇到什么挑战。",
            "ability_advancement": ["中期获得能力1", "中期获得能力2"],
            "key_growth_points": ["中期关键成长点1", "中期关键成长点2"],
            "relationship_evolution": "与重要角色的关系如何发展"
        },
        "climax_stage": {
            "personality_development": "主角在高潮阶段（101-160章）如何面对最大挑战，性格如何成熟。",
            "ability_advancement": ["后期核心能力1", "后期核心能力2"],
            "key_growth_points": ["后期关键成长点1", "后期关键成长点2"],
            "relationship_evolution": "关系发展到何种程度"
        },
        "ending_stage": {
            "personality_development": "主角在结局阶段（161-200章）的最终状态，与开局形成鲜明对比。",
            "ability_advancement": ["最终能力1", "最终能力2"],
            "key_growth_points": ["最终关键成长点1", "最终关键成长点2"],
            "relationship_evolution": "关系的最终状态"
        }
    },
    "supporting_characters": [
        {
            "name": "配角名称",
            "role": "角色定位",
            "growth_arc": "该角色的成长或毁灭弧线简述。",
            "key_development_points": ["关键发展节点1"]
        }
    ],
    "faction_development_trajectory": null, // (可选)
    "ability_system_evolution": null, // (可选)
    "emotional_development_journey": {
        "main_emotional_arc": "主角贯穿全书的主要情感变化弧线。",
        "relationship_dynamics": "核心人际关系（如爱情、复仇、联盟、支配）的发展阶段。",
        "emotional_climax_points": [
            "情感爆发或转变的关键剧情节点1",
            "情感爆发或转变的关键剧情节点2"
        ]
    }
}
""",
            "emotional_blueprint_generation": """
你是一位资深的网络小说情绪架构专家。你的任务是为小说设计全书的情绪蓝图，确保读者情绪被精准调动。

# 情绪蓝图设计
设计全书的情感光谱和阶段情绪弧线。

## 核心要求
1. **情感光谱**：定义3-5个核心情感标签（如：期待、紧张、愤怒、感动、爽感）
2. **阶段情绪弧线**：为"起承转合"四阶段设计情感起伏曲线
3. **情绪高潮点**：标记全书的情感爆发节点
4. **情绪节奏控制**：确保紧张与舒缓交替，避免读者疲劳

# 输出格式
严格返回JSON格式：
{
    "emotional_blueprint": {
        "emotional_spectrum": ["情感标签1", "情感标签2", ...],
        "stage_emotional_arcs": {
            "opening_stage": {"dominant_emotion": "主导情绪", "curve": "上升/下降/波动", "intensity": 1-10},
            "development_stage": {...},
            "climax_stage": {...},
            "ending_stage": {...}
        },
        "climax_moments": ["高潮点1", "高潮点2", ...]
    },
    "global_growth_plan": {
        "protagonist_growth": {
            "opening_stage": {"ability_level": "初始能力", "key_growth": "本阶段成长重点"},
            "development_stage": {...},
            "climax_stage": {...},
            "ending_stage": {...}
        },
        "ability_system_progression": ["能力1", "能力2", ...],
        "key_relationships_development": [...]
    }
}
""",
            "stage_foreshadowing_planning": """
你是一位资深的番茄网络小说节奏控制专家。请为小说的特定阶段制定详细的伏笔铺垫计划。...
""",

            "stage_content_planning": """
你是一位资深的番茄网络小说内容架构师。请为小说的特定阶段制定详细的内容规划。

**阶段信息**
阶段名称：{stage_name}
章节范围：{chapter_range}
总章节数：{total_chapters}

**小说基础信息**
标题：{novel_title}
简介：{novel_synopsis}
核心世界观：{worldview_overview}

**当前阶段特性**
{stage_characteristics}

**内容规划要求**
请为这个阶段制定详细的内容规划，专注于"写什么"，包含以下方面：

1. 人物成长规划
主角成长轨迹
性格演变：本阶段主角性格会发生什么变化？
能力提升：具体会掌握哪些新能力或技能？
动机深化：主角的目标和动机会如何深化？
关系发展：与重要角色的关系如何变化？

配角任务分配
哪些配角在本阶段有重要戏份？
他们的任务是什么？（帮助主角、制造障碍、揭示信息）

2. 势力关系演变
各阵营在本阶段的动态
势力对比如何变化？
有哪些重要的联盟或背叛？

3. 核心剧情推进
本阶段需要完成的核心剧情目标
关键剧情节点（3-5个）
每个节点的大致位置和作用

4. 情绪节奏设计
本阶段的情绪基调（紧张、轻松、压抑、激昂）
情绪高潮点在哪里？
如何控制节奏避免读者疲劳？

5. 爽点与期待感设计
本阶段的主要爽点（打脸、突破、收获、揭秘）
如何设置期待感？
如何安排反转？

**输出格式要求**
请严格按照以下JSON格式输出，不要包含任何额外的解释文字或markdown代码块标记：

{{
    "stage_content_plan": {{
        "stage_theme": "本阶段的核心主题（一句话概括）",
        "protagonist_growth": {{
            "character_arc": "主角在本阶段的成长轨迹",
            "ability_development": ["能力成长点1", "能力成长点2"],
            "relationship_changes": ["关系变化1", "关系变化2"]
        }},
        "faction_dynamics": {{
            "major_shifts": ["势力变化1", "势力变化2"],
            "key_conflicts": ["关键冲突1", "关键冲突2"],
            "new_alliances": ["新联盟1", "新联盟2"]
        }},
        "plot_milestones": [
            {{
                "milestone_name": "剧情节点名称",
                "estimated_position": "大概位置（如第35章）",
                "main_goal": "这个节点要完成什么",
                "emotional_impact": "情绪影响（爽点/泪点/转折点）"
            }}
        ],
        "emotional_arc": {{
            "dominant_tone": "主导情绪基调",
            "climax_moments": ["高潮点1", "高潮点2"],
            "pacing_strategy": "节奏控制策略"
        }},
        "satisfaction_design": {{
            "major_payoffs": ["大爽点1", "大爽点2"],
            "anticipation_hooks": ["期待感钩子1", "期待感钩子2"],
            "plot_twists": ["反转设计1", "反转设计2"]
        }}
    }}
}}
""",

            "stage_writing_planning": """
你是一位顶级的网络小说剧情架构师AI，专精于将高阶大纲分解为结构化、可执行的阶段性写作计划。

内容:
你正在为一个{platform_name}小说项目制定阶段写作计划。

小说标题：{novel_title}
阶段范围：{stage_range}

创意种子信息：
{creative_seed_info}

参考材料：
{reference_materials}

你的任务是根据提供的创意种子和参考材料，为"{stage_name}"制定详细的写作计划。

请按照以下JSON格式输出阶段计划：
{{
    "stage_writing_plan": {{
        "stage_name": "{stage_name}",
        "stage_range": "{stage_range}",
        "chapter_count": {chapter_count},
        "creative_essence": "本阶段需要体现的核心创意点",
        "stage_goals": [
            "阶段目标1",
            "阶段目标2"
        ],
        "plot_structure": {{
            "opening": "开局设计和钩子",
            "development": "发展阶段的主要情节",
            "climax": "阶段高潮设计",
            "transition": "如何衔接到下一阶段"
        }},
        "character_focus": {{
            "protagonist_tasks": ["主角任务1", "主角任务2"],
            "character_development": "本阶段人物成长重点",
            "key_relationships": "关键关系发展"
        }},
        "emotional_arc": {{
            "dominant_emotion": "主导情绪",
            "emotional_curve": "情绪曲线设计",
            "climax_moments": ["情绪高潮点1", "情绪高潮点2"]
        }},
        "satisfaction_design": {{
            "major_payoffs": ["爽点1", "爽点2"],
            "anticipation_building": "期待感营造方式",
            "plot_twists": ["反转设计1"]
        }},
        "key_events": [
            {{
                "event_name": "事件名称",
                "chapter_range": "大致章节范围",
                "event_type": "事件类型（战斗/揭秘/情感/收获）",
                "significance": "对整体剧情的影响"
            }}
        ],
        "writing_guidance": {{
            "tone_style": "本阶段的语气和风格建议",
            "pacing_strategy": "节奏控制策略",
            "key_scenes": ["关键场景1", "关键场景2"],
            "things_to_avoid": ["避免事项1", "避免事项2"]
        }}
    }}
}}

注意：
1. 确保计划具体、可执行
2. 所有设计必须忠实于创意种子
3. 考虑与前后阶段的衔接
4. 突出{platform_name}平台特色（爽点、快节奏、强情绪）
""",

            "overall_stage_plan": """
你是一位顶级的网络小说结构规划专家，专精于"起承转合"四段式小说架构设计。

内容:
请根据以下信息，设计全书的整体阶段划分：

小说标题：{novel_title}
小说简介：{novel_synopsis}
总章节数：{total_chapters}

创意种子：
{creative_seed}

市场分析：
{market_analysis}

成长规划（参考）：
{growth_plan}

情绪蓝图（参考）：
{emotional_blueprint}

请按照"起承转合"四段式结构，将全书划分为四个阶段：
1. **起（开局阶段）**：约占15-20%，建立世界观、引入主角、展现金手指、埋下核心冲突
2. **承（发展阶段）**：约占35-40%，展开主线、升级成长、建立势力、深化冲突
3. **转（高潮阶段）**：约占25-30%，核心冲突爆发、最大危机、最终对决准备
4. **合（结局阶段）**：约占10-15%，收束所有线索、最终对决、圆满或开放式结局

请严格按照以下JSON格式输出：
{{
    "overall_stage_plan": {{
        "structural_model": "四段式（起承转合）",
        "total_chapters": {total_chapters},
        "opening_stage": {{
            "stage_name": "起（开局阶段）",
            "chapter_range": "1-{opening_end}",
            "chapter_count": {opening_chapters},
            "core_mission": "本阶段的核心任务",
            "plot_goals": ["剧情目标1", "剧情目标2"],
            "character_goals": ["人物目标1", "人物目标2"],
            "emotional_goals": ["情绪目标1", "情绪目标2"],
            "key_deliverables": ["必须完成的事项1", "必须完成的事项2"],
            "ending_hook": "阶段结束时留下的钩子，吸引读者进入下一阶段"
        }},
        "development_stage": {{
            "stage_name": "承（发展阶段）",
            "chapter_range": "{development_start}-{development_end}",
            "chapter_count": {development_chapters},
            "core_mission": "本阶段的核心任务",
            "plot_goals": ["剧情目标1", "剧情目标2"],
            "character_goals": ["人物目标1", "人物目标2"],
            "emotional_goals": ["情绪目标1", "情绪目标2"],
            "key_deliverables": ["必须完成的事项1", "必须完成的事项2"],
            "ending_hook": "阶段结束时留下的钩子"
        }},
        "climax_stage": {{
            "stage_name": "转（高潮阶段）",
            "chapter_range": "{climax_start}-{climax_end}",
            "chapter_count": {climax_chapters},
            "core_mission": "本阶段的核心任务",
            "plot_goals": ["剧情目标1", "剧情目标2"],
            "character_goals": ["人物目标1", "人物目标2"],
            "emotional_goals": ["情绪目标1", "情绪目标2"],
            "key_deliverables": ["必须完成的事项1", "必须完成的事项2"],
            "ending_hook": "阶段结束时留下的钩子"
        }},
        "ending_stage": {{
            "stage_name": "合（结局阶段）",
            "chapter_range": "{ending_start}-{total_chapters}",
            "chapter_count": {ending_chapters},
            "core_mission": "本阶段的核心任务",
            "plot_goals": ["剧情目标1", "剧情目标2"],
            "character_goals": ["人物目标1", "人物目标2"],
            "emotional_goals": ["情绪目标1", "情绪目标2"],
            "key_deliverables": ["必须完成的事项1", "必须完成的事项2"],
            "ending_style": "结局风格（圆满/开放/悬念/悲剧）"
        }}
    }}
}}

注意事项：
1. 各阶段章节数之和必须等于{total_chapters}
2. 每个阶段的core_mission必须清晰具体
3. 阶段之间的钩子要有机衔接
4. 目标设计要考虑市场分析中的读者期待
5. 关键交付物必须是可验证的具体成果
""",

            "foundation_planning": """
你是一位资深的网络小说开篇策划专家，专精于小说基础设定设计。

内容:
请根据提供的创意种子，设计小说的基础设定。

小说标题：{novel_title}
小说简介：{novel_synopsis}

创意种子：
{creative_seed}

市场定位：
{market_analysis}

请设计以下内容：
1. **写作风格指南**：确定小说的叙事风格、语言风格、节奏特点
2. **市场定位策略**：基于市场分析，确定目标读者和差异化策略

请严格按照以下JSON格式输出：
{{
    "writing_style_guide": {{
        "narrative_perspective": "叙事视角（第一人称/第三人称）",
        "narrative_style": "叙事风格（热血冷静/轻松幽默/黑暗压抑/史诗宏大）",
        "language_style": "语言风格（简洁明快/华丽辞藻/口语化/文艺范）",
        "pacing_characteristics": "节奏特点（快节奏爽文/慢热沉淀/张弛有度）",
        "chapter_structure": "章节结构建议",
        "dialogue_style": "对话风格",
        "description_balance": "描写与叙述的平衡",
        "platform_adaptations": "平台适配建议（针对{platform_name}）"
    }},
    "market_positioning": {{
        "target_reader_profile": "目标读者画像",
        "core_selling_points": ["核心卖点1", "核心卖点2", "核心卖点3"],
        "differentiation_strategy": "差异化竞争策略",
        "genre_positioning": "类型定位",
        "competitive_advantages": ["竞争优势1", "竞争优势2"],
        "potential_risks": ["潜在风险1", "潜在风险2"],
        "risk_mitigation": "风险规避建议"
    }}
}}
""",

            "worldview_with_factions": """
你是一位资深的网络小说世界观与势力系统设计专家。你的任务是设计一个完整的世界观和势力系统。

内容:
请基于提供的小说创意种子，设计世界观和势力系统。

小说标题：{novel_title}
小说简介：{novel_synopsis}
创意种子：
{creative_seed}
市场分析：
{market_analysis}

请设计以下内容：
1. **核心世界观**：世界背景、力量体系、核心规则
2. **势力系统**：各方势力、势力间关系、冲突格局

请严格按照以下JSON格式输出：
{{
    "core_worldview": {{
        "world_overview": "世界背景概述",
        "power_system": "力量体系说明",
        "core_rules": "世界运行的核心规则",
        "unique_features": "世界独特设定",
        "geography": "地理概况（如相关）",
        "history_background": "历史背景（如相关）"
    }},
    "faction_system": {{
        "factions": [
            {{
                "name": "势力名称",
                "type": "势力类型（宗门/家族/国家/组织）",
                "description": "势力描述",
                "strength_level": "实力等级",
                "relationship_with_protagonist": "与主角关系",
                "key_characters": ["关键人物1", "关键人物2"]
            }}
        ],
        "main_conflict": "主要冲突格局",
        "faction_power_balance": "势力间力量平衡",
        "recommended_starting_faction": "推荐主角开局关联的势力"
    }}
}}
""",

            "character_design_core": """
你是一位资深的网络小说角色设计专家。你的任务是设计小说的核心角色。

内容:
请基于提供的创意种子、世界观和势力系统，设计核心角色。

小说标题：{novel_title}
核心世界观：
{core_worldview}
势力系统：
{faction_system}
创意种子：
{creative_seed}

请设计以下内容：
1. **主角设定**：详细的主角人设
2. **核心盟友**：2-3个重要盟友
3. **主要反派/对手**：1-2个主要对手

请严格按照以下JSON格式输出：
{{
    "protagonist": {{
        "name": "主角姓名",
        "gender": "性别",
        "age": "年龄",
        "appearance": "外貌特征",
        "personality": "性格特点",
        "background": "身世背景",
        "motivation": "核心动机",
        "initial_ability": "初始能力",
        "growth_potential": "成长潜力",
        "unique_traits": "独特特质",
        "catchphrases": ["口头禅1", "口头禅2"]
    }},
    "core_allies": [
        {{
            "name": "盟友姓名",
            "role": "角色定位（导师/伙伴/爱人）",
            "description": "角色描述",
            "relationship_with_protagonist": "与主角关系"
        }}
    ],
    "main_antagonists": [
        {{
            "name": "反派姓名",
            "role": "角色定位（宿敌/boss/对手）",
            "description": "角色描述",
            "conflict_with_protagonist": "与主角的冲突"
        }}
    ]
}}
""",

            "global_growth_planning": """
你是一位资深的网络小说成长路线规划专家。你的任务是为小说设计全书的成长规划。

内容:
请基于提供的创意种子、角色设定和世界观，设计全书的成长规划。

小说标题：{novel_title}
主角设定：
{protagonist}
世界观：
{worldview}
创意种子：
{creative_seed}

请设计以下内容：
1. **主角成长路线图**：按"起承转合"四阶段规划主角成长
2. **能力体系进阶**：主角能力如何逐步提升
3. **关键关系发展**：主角与重要角色的关系演变

请严格按照以下JSON格式输出：
{{
    "protagonist_growth": {{
        "opening_stage": {{
            "ability_level": "开局能力水平",
            "key_growth": "本阶段成长重点",
            "milestones": ["里程碑1", "里程碑2"]
        }},
        "development_stage": {{
            "ability_level": "发展阶段能力",
            "key_growth": "本阶段成长重点",
            "milestones": ["里程碑1", "里程碑2"]
        }},
        "climax_stage": {{
            "ability_level": "高潮阶段能力",
            "key_growth": "本阶段成长重点",
            "milestones": ["里程碑1", "里程碑2"]
        }},
        "ending_stage": {{
            "ability_level": "最终能力水平",
            "key_growth": "本阶段成长重点",
            "milestones": ["里程碑1", "里程碑2"]
        }}
    }},
    "ability_system_progression": [
        "能力进阶节点1",
        "能力进阶节点2",
        "能力进阶节点3"
    ],
    "key_relationships_development": [
        {{
            "character": "角色名称",
            "relationship_arc": "关系发展弧线"
        }}
    ]
}}
""",

            "stage_writing_plan": """
你是一位顶级的网络小说剧情架构师AI，专精于将高阶大纲分解为结构化、可执行的阶段性写作计划。

内容:
你正在为一个{platform_name}小说项目制定阶段写作计划。

小说标题：{novel_title}
阶段范围：{stage_range}

创意种子信息：
{creative_seed_info}

参考材料：
{reference_materials}

你的任务是根据提供的创意种子和参考材料，为"{stage_name}"制定详细的写作计划。

请按照以下JSON格式输出阶段计划：
{{
    "stage_writing_plan": {{
        "stage_name": "{stage_name}",
        "stage_range": "{stage_range}",
        "chapter_count": {chapter_count},
        "creative_essence": "本阶段需要体现的核心创意点",
        "stage_goals": [
            "阶段目标1",
            "阶段目标2"
        ],
        "plot_structure": {{
            "opening": "开局设计和钩子",
            "development": "发展阶段的主要情节",
            "climax": "阶段高潮设计",
            "transition": "如何衔接到下一阶段"
        }},
        "character_focus": {{
            "protagonist_tasks": ["主角任务1", "主角任务2"],
            "character_development": "本阶段人物成长重点",
            "key_relationships": "关键关系发展"
        }},
        "emotional_arc": {{
            "dominant_emotion": "主导情绪",
            "emotional_curve": "情绪曲线设计",
            "climax_moments": ["情绪高潮点1", "情绪高潮点2"]
        }},
        "satisfaction_design": {{
            "major_payoffs": ["爽点1", "爽点2"],
            "anticipation_building": "期待感营造方式",
            "plot_twists": ["反转设计1"]
        }},
        "key_events": [
            {{
                "event_name": "事件名称",
                "chapter_range": "大致章节范围",
                "event_type": "事件类型（战斗/揭秘/情感/收获）",
                "significance": "对整体剧情的影响"
            }}
        ],
        "writing_guidance": {{
            "tone_style": "本阶段的语气和风格建议",
            "pacing_strategy": "节奏控制策略",
            "key_scenes": ["关键场景1", "关键场景2"],
            "things_to_avoid": ["避免事项1", "避免事项2"]
        }}
    }}
}}

注意：
1. 确保计划具体、可执行
2. 所有设计必须忠实于创意种子
3. 考虑与前后阶段的衔接
4. 突出{platform_name}平台特色（爽点、快节奏、强情绪）
""",

            "stage_emotional_planning": """
你是一位资深的网络小说情绪节奏设计专家。你的任务是为特定阶段设计详细的情绪规划。

阶段名称：{stage_name}
章节范围：{chapter_range}
情绪蓝图参考：
{emotional_blueprint}

请设计以下内容：
1. 本阶段的主导情绪
2. 情绪曲线设计
3. 情绪高潮点安排
4. 与前后阶段的情绪衔接

请严格按照以下JSON格式输出：
{{
    "stage_emotional_plan": {{
        "stage_name": "{stage_name}",
        "dominant_emotion": "主导情绪",
        "emotional_curve": "情绪曲线描述（如：低开高走/波动上升/持续紧张）",
        "curve_description": "情绪曲线的详细说明",
        "climax_moments": [
            {{
                "position": "大致位置",
                "emotion": "情绪类型",
                "intensity": 8,
                "description": "情绪爆发点描述"
            }}
        ],
        "transition_to_next": "如何衔接到下一阶段的情绪",
        "pacing_strategy": "节奏控制策略"
    }}
}}
""",

            "chapter_event_design": """
你是一位资深的网络小说剧情设计专家。请为指定章节设计详细的事件。

小说信息：
- 标题：{novel_title}
- 当前章节：第{chapter_number}章
- 阶段：{stage_name}

上下文信息：
{context_info}

请设计以下内容：
1. 本章的核心事件
2. 事件的起因、经过、结果
3. 涉及的角色及其互动
4. 本章的情绪设计
5. 结尾钩子

请严格按照以下JSON格式输出：
{{
    "chapter_event": {{
        "core_event": "核心事件描述",
        "cause": "事件起因",
        "process": "事件经过",
        "result": "事件结果",
        "involved_characters": ["角色1", "角色2"],
        "character_interactions": "角色互动描述",
        "emotional_design": "情绪设计",
        "ending_hook": "结尾钩子",
        "plot_significance": "对整体剧情的意义"
    }}
}}
""",

            "chapter_content_generation": """
你是一位顶级的网络小说写作专家。请根据提供的信息，撰写小说章节内容。

小说信息：
- 标题：{novel_title}
- 当前章节：第{chapter_number}章
- 章节标题：{chapter_title}

事件设计：
{event_design}

上下文信息：
{context_info}

写作要求：
1. 语言流畅，描写生动
2. 对话自然，符合角色性格
3. 节奏紧凑，避免拖沓
4. 突出爽点，控制情绪节奏
5. 结尾留有钩子

请直接输出章节正文，不要包含JSON格式或其他标记。
""",

            "chapter_optimization": """
你是一位资深的网络小说编辑专家。请对提供的章节内容进行优化。

章节信息：
- 标题：{chapter_title}
- 章节号：{chapter_number}

原始内容：
{original_content}

优化要求：
{optimization_requirements}

请提供优化后的内容，并说明优化点。
""",

            "chapter_quality_assessment": """
你是一位资深的网络小说质量评估专家。请对提供的章节进行质量评估。

章节信息：
- 标题：{chapter_title}
- 章节号：{chapter_number}

章节内容：
{chapter_content}

请从以下维度进行评估：
1. 可读性（语言流畅度、错别字、标点符号）
2. 剧情节奏（张弛有度、有无拖沓）
3. 人物塑造（言行一致、性格鲜明）
4. 情绪控制（能否调动读者情绪）
5. 爽点设计（是否有足够的爽点）
6. 钩子设置（结尾是否有吸引力）

请严格按照以下JSON格式输出：
{{
    "quality_assessment": {{
        "readability": {{"score": 85, "comments": "评价"}},
        "pacing": {{"score": 80, "comments": "评价"}},
        "characterization": {{"score": 82, "comments": "评价"}},
        "emotional_impact": {{"score": 88, "comments": "评价"}},
        "satisfaction": {{"score": 85, "comments": "评价"}},
        "hook": {{"score": 90, "comments": "评价"}},
        "overall_score": 85,
        "summary": "总体评价",
        "suggestions": ["改进建议1", "改进建议2"]
    }}
}}
""",

            # 元素时机规划已移除，由期待感系统统一管理
            # element_timing_planning prompt 已废弃
        }

    def get(self, key, default=None):
        """兼容字典的get方法"""
        return self.prompts.get(key, default)

    def __getitem__(self, key):
        """支持字典式访问"""
        return self.prompts[key]

    def __contains__(self, key):
        """支持in操作符"""
        return key in self.prompts
