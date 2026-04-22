"""规划类提示词配置"""

class PlanningPrompts:
    def __init__(self):
        self.prompts = {
            "emotional_development_planning": """
你是一位资深爽文小说角色成长与爽感发展策划专家。请基于提供的角色设定、世界观和全书大纲，为主角和核心配角制定以"爽感"为核心的成长计划。

**核心任务（爽文专用）**：
1. **主角成长线**：为主角设计一个"能力跃迁→打脸升级→收获认可"的成长弧线。每次成长必须带来**具象爽感**（不是抽象变强，而是让读者感受到"他变强了，要打脸了"）。
2. **配角群像**：为核心配角设计功能定位——谁是"捧哏"（衬托主角）、谁是"打脸对象"（让读者爽）、谁是"助力"（帮助主角装X）、谁是"伏笔"（后期反转）。
3. **情感发展**：规划主角与重要角色的关系演变，重点是**关系变化带来的爽感**（从被看不起到被仰望、从敌对到臣服、从陌生到追随）。
4. **阶段对应**：将成长计划与"爽点单元制"对应，明确每个阶段的成长如何服务于爽点设计。

**输出要求**：
请严格按照以下JSON格式输出，不要包含任何额外的解释文字：
```json
{
    "protagonist_growth": {
        "opening_stage": {
            "personality_development": "开局阶段性格（建议：隐忍中带锋芒，或表面上淡然但内心有傲气）",
            "ability_advancement": ["初始能力1（带金手指）", "初始能力2"],
            "key_growth_points": ["成长点1：首次展现能力（让读者知道主角不简单）", "成长点2：首次小打脸（建立爽感预期）"],
            "payoff_growth": "本阶段成长如何转化为爽点（如：获得金手指→第3章打脸看不起他的人）"
        },
        "development_stage": {
            "personality_development": "发展阶段性格（建议：越来越自信，手段越来越果决）",
            "ability_advancement": ["中期能力1（每次升级都要有'碾压感'）", "中期能力2"],
            "key_growth_points": ["成长点1：能力质变（让读者觉得'这下要爽了'）", "成长点2：地位跃迁（从无名小卒到一方强者）"],
            "relationship_evolution": "关系演变中的爽感设计（如：曾经的敌人→现在的小弟；曾经看不起他的人→现在求他办事）"
        },
        "climax_stage": {
            "personality_development": "高潮阶段性格（建议：王者风范，云淡风轻中碾压一切）",
            "ability_advancement": ["后期核心能力1（终极碾压手段）", "后期核心能力2"],
            "key_growth_points": ["成长点1：终极突破（让读者等待已久的质变）", "成长点2：背景/身份全面揭露（震惊所有人的爽点）"],
            "relationship_evolution": "关系演变到最终态（如：从被追杀的蝼蚁→让整个世界颤抖的存在）"
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
你是一位资深的爽文小说情绪架构专家，专精于番茄小说市场的"爽点情绪工程"。

# 爽点情绪蓝图设计
设计全书的情绪节奏，核心目标：**让读者持续产生"爽感"，欲罢不能**。

## 核心要求（爽文专用）
1. **爽感情感光谱**：定义3-5个核心爽感标签（如：装逼快感、打脸宣泄、收获满足、逆袭狂喜、护短温暖）
2. **爽点节奏图**：不是传统的"起承转合"情绪弧线，而是"压抑→爆发→满足→期待"的爽点循环
3. **爽点爆发节点**：明确标记全书的爽点位置、类型和强度
4. **压抑设计**：爽感来自压抑的深度，必须设计足够的轻视、嘲讽、困境来支撑爆发
5. **情绪节奏控制**：爽点之间要有"呼吸空间"（收获+消化），但不能太长（避免读者流失）

# 输出格式
严格返回JSON格式（键名保持兼容）：
{
    "emotional_blueprint": {
        "emotional_spectrum": ["爽感标签1", "爽感标签2", ...],
        "stage_emotional_arcs": {
            "opening_stage": {
                "dominant_emotion": "主导情绪（如：快速代入+首次爽感）",
                "curve": "快速上升型（黄金三章必须快节奏）",
                "intensity": 7-9,
                "payoff_density": "每1-2章一个小爽点"
            },
            "development_stage": {
                "dominant_emotion": "主导情绪（如：持续期待+间歇爆发）",
                "curve": "波浪型（压抑→爆发→压抑→爆发）",
                "intensity": 6-8,
                "payoff_density": "每2-4章一个小爽点，每8-12章一个中爽点"
            },
            "climax_stage": {
                "dominant_emotion": "主导情绪（如：碾压快感+终极满足）",
                "curve": "持续高扬型（层层升级，越打越爽）",
                "intensity": 8-10,
                "payoff_density": "每3-5章一个大爽点，连续高潮"
            },
            "ending_stage": {
                "dominant_emotion": "主导情绪（如：圆满满足或新期待）",
                "curve": "顶峰收束型",
                "intensity": 9-10,
                "payoff_density": "最终大爽点 + 结局收束"
            }
        },
        "payoff_moments": [
            {"chapter": "X", "type": "装逼打脸/收获奖励/境界突破/势力碾压/揭秘反转", "intensity": 1-10, "description": "具体爽点描述"}
        ],
        "suppression_design": [
            {"chapter": "X", "type": "被轻视/被嘲讽/遇困境/被背叛", "purpose": "为后续哪个爽点做铺垫"}
        ]
    },
    "global_growth_plan": {
        "protagonist_growth": {
            "opening_stage": {"ability_level": "初始能力", "key_growth": "本阶段成长重点（必须包含首次能力展现）"},
            "development_stage": {"ability_level": "中期能力", "key_growth": "持续升级节奏（每次升级都要带来爽感）"},
            "climax_stage": {"ability_level": "后期能力", "key_growth": "质变级突破（让读者觉得'终于等到了'）"},
            "ending_stage": {"ability_level": "终极能力", "key_growth": "巅峰状态或新高度"}
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
你是一位顶级的爽文小说结构规划专家，专精于番茄小说市场的"爽点单元制"架构设计。

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

请按照"爽点单元制"结构，将全书划分为四个功能阶段。注意：以下四个阶段的键名保持兼容，但功能已按爽文重新定位：

1. **opening_stage（黄金开局阶段）**：约占10-15%，**不是慢热铺垫，而是快速引爆**
   - 核心功能：黄金三章强钩子 → 主角快速登场 → 首次小爽点（打脸/收获/突破）→ 留下大悬念
   - 爽文铁律：前300字必须有冲突，第1章结尾必须有卡点，第3章必须完成第一个正反馈循环
   
2. **development_stage（爽点展开阶段）**：约占35-45%，**爽点密度最高的核心区域**
   - 核心功能：建立"压抑→爆发→收获"的循环节奏
   - 爽点节奏：每2-4章一个小爽点，每8-12章一个中爽点，每20-30章一个大爽点
   - 压抑设计：主角必须经历足够的轻视/嘲讽/困境，让爆发更有爽感
   - 收获设计：每次爽点后必须有具象收获（财富/地位/能力/人脉）
   
3. **climax_stage（高潮碾压阶段）**：约占25-35%，**从个人爽点到势力碾压**
   - 核心功能：主角从"个人强大"升级到"势力/背景碾压"
   - 爽点升级：小反派→大反派→势力对抗→世界观揭秘
   - 打脸升级：从打脸个人到打脸家族/宗门/整个体系
   - 情绪设计：让读者产生"终于等到这一天"的满足感
   
4. **ending_stage（终局收束阶段）**：约占10-15%，**圆满收官或开启新篇章**
   - 核心功能：收束主线爽点、兑现所有伏笔、给出最终大爽点
   - 可选设计：圆满结局/悬念续作/无敌流继续碾压

请严格按照以下JSON格式输出（键名保持兼容，但内容按爽文设计）：
{{
    "overall_stage_plan": {{
        "structural_model": "爽点单元制（番茄爽文专用）",
        "total_chapters": {total_chapters},
        "opening_stage": {{
            "stage_name": "黄金开局阶段",
            "chapter_range": "1-{opening_end}",
            "chapter_count": {opening_chapters},
            "core_mission": "本阶段的核心任务（必须包含：黄金三章设计 + 首个爽点 + 强悬念钩子）",
            "plot_goals": ["剧情目标1", "剧情目标2"],
            "character_goals": ["人物目标1", "人物目标2"],
            "emotional_goals": ["情绪目标1：快速建立读者代入感", "情绪目标2：第3章前必须有一次爽感体验"],
            "key_deliverables": ["必须完成的事项1：主角身份/金手指清晰展示", "必须完成的事项2：至少1个爽点事件", "必须完成的事项3：强悬念钩子"],
            "payoff_schedule": ["爽点1（第X章）：类型-描述", "爽点2（第X章）：类型-描述"],
            "ending_hook": "阶段结束时留下的钩子，吸引读者进入下一阶段（必须是强悬念或新期待）"
        }},
        "development_stage": {{
            "stage_name": "爽点展开阶段",
            "chapter_range": "{development_start}-{development_end}",
            "chapter_count": {development_chapters},
            "core_mission": "本阶段的核心任务（必须包含：稳定的爽点节奏 + 主角持续升级 + 压抑-爆发循环）",
            "plot_goals": ["剧情目标1", "剧情目标2"],
            "character_goals": ["人物目标1", "人物目标2"],
            "emotional_goals": ["情绪目标1：让读者持续期待下一个爽点", "情绪目标2：压抑足够深，爆发足够爽"],
            "key_deliverables": ["必须完成的事项1：爽点密度≥每3章1个小爽点", "必须完成的事项2：主角能力/地位有明显跃迁", "必须完成的事项3：建立至少1个长期期待感"],
            "payoff_schedule": ["小爽点（第X章）：类型-描述", "中爽点（第X章）：类型-描述", "大爽点（第X章）：类型-描述"],
            "ending_hook": "阶段结束时留下的钩子"
        }},
        "climax_stage": {{
            "stage_name": "高潮碾压阶段",
            "chapter_range": "{climax_start}-{climax_end}",
            "chapter_count": {climax_chapters},
            "core_mission": "本阶段的核心任务（必须包含：从个人对抗升级到势力/世界观对抗 + 最大爽点设计）",
            "plot_goals": ["剧情目标1", "剧情目标2"],
            "character_goals": ["人物目标1", "人物目标2"],
            "emotional_goals": ["情绪目标1：让读者产生'终于等到这一天'的满足感", "情绪目标2：打脸层级从个人升级到体系"],
            "key_deliverables": ["必须完成的事项1：最大反派的全面溃败", "必须完成的事项2：主角背景/势力的全面展现", "必须完成的事项3：世界观核心秘密的揭示"],
            "payoff_schedule": ["阶段性大爽点（第X章）：类型-描述", "最终对决爽点（第X章）：类型-描述"],
            "ending_hook": "阶段结束时留下的钩子"
        }},
        "ending_stage": {{
            "stage_name": "终局收束阶段",
            "chapter_range": "{ending_start}-{total_chapters}",
            "chapter_count": {ending_chapters},
            "core_mission": "本阶段的核心任务（必须包含：所有伏笔收束 + 最终大爽点 + 结局设计）",
            "plot_goals": ["剧情目标1", "剧情目标2"],
            "character_goals": ["人物目标1", "人物目标2"],
            "emotional_goals": ["情绪目标1：圆满收官的满足感", "情绪目标2：或开启新期待的悬念感"],
            "key_deliverables": ["必须完成的事项1：所有主要伏笔的兑现", "必须完成的事项2：最终爽点的极致设计", "必须完成的事项3：结局风格的明确"],
            "payoff_schedule": ["最终爽点（第X章）：类型-描述"],
            "ending_style": "结局风格（圆满/开放/悬念/继续碾压）"
        }}
    }}
}}

爽文设计铁律（必须遵守）：
1. 各阶段章节数之和必须等于{total_chapters}
2. 每个阶段必须明确标注爽点节奏（payoff_schedule）
3. opening_stage 必须包含黄金三章设计，严禁慢热
4. development_stage 必须保持高爽点密度，严禁水文
5. 阶段之间的钩子必须让读者产生"下一章会更爽"的期待
6. 所有plot_goals必须围绕"爽点设计"展开，不要写传统文学式的目标
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
1. **主角成长路线图**：按"爽点单元制"四阶段规划主角成长（黄金开局→爽点展开→高潮碾压→终局收束）
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
            
            "expectation_batch_generation": """
你是一位资深网络小说期待感编排专家。你的任务是基于阶段计划，为每个重大事件设计最契合的期待感类型。

## 输入信息
用户会提供以下JSON格式的阶段信息：
- stage_name: 阶段名称
- stage_range: 阶段章节范围
- emotional_arc: 情绪弧线信息（start_emotion, end_emotion, arc_description）
- protagonist_growth_theme: 主角成长主题
- worldview_revelation_plan: 世界观展开计划
- conflict_theme: 冲突主题
- satisfaction_points: 爽点设计列表
- events: 重大事件列表，每个事件包含：
  - event_id: 事件ID
  - name: 事件名称
  - main_goal: 事件核心目标
  - emotional_focus: 情绪焦点
  - chapter_range: 章节范围
  - role_in_stage_arc: 在阶段弧线中的角色
  - position_in_emotional_arc: 在情绪曲线中的位置
  - related_events: 关联事件
  - is_turning_point: 是否转折点

## 20种期待类型说明

### 基础类型（6种）
1. **SHOWCASE** - 展示橱窗：提前展示奖励或能力的强大
2. **SUPPRESSION_RELEASE** - 压抑释放：制造阻碍后释放爽感
3. **NESTED_DOLL** - 套娃期待：大期待包着小期待
4. **EMOTIONAL_HOOK** - 情绪钩子：打脸、认同、身份揭秘
5. **POWER_GAP** - 实力差距：期待变强的过程
6. **MYSTERY_FORESHADOW** - 伏笔揭秘：埋下线索后揭晓

### 扩展类型（14种）
7. **PIG_EATS_TIGER** - 扮猪吃虎：隐藏实力后打脸
8. **SHOW_OFF_FACE_SLAP** - 装逼打脸：展示实力打脸
9. **IDENTITY_REVEAL** - 身份反转：隐藏身份揭晓
10. **BEAUTY_FAVOR** - 美人恩：女主好感进展
11. **FORTUITOUS_ENCOUNTER** - 机缘巧合：意外获得奇遇
12. **COMPETITION** - 比试切磋：宗门大比等
13. **AUCTION_TREASURE** - 拍卖会争宝
14. **SECRET_REALM_EXPLORATION** - 秘境探险
15. **ALCHEMY_CRAFTING** - 炼丹炼器
16. **FORMATION_BREAKING** - 阵法破解
17. **SECT_MISSION** - 宗门任务
18. **CROSS_WORLD_TELEPORT** - 跨界传送
19. **CRISIS_RESCUE** - 危机救援
20. **MASTER_INHERITANCE** - 师恩传承

## 编排原则

### 1. 情绪曲线匹配
- **压抑期** → MYSTERY_FORESHADOW(埋线), POWER_GAP(期待变强)
- **上升期** → SHOWCASE(展示), FORTUITOUS_ENCOUNTER(奇遇)
- **爆发期** → SUPPRESSION_RELEASE(释放), IDENTITY_REVEAL(揭秘)
- **收尾期** → CRISIS_RESCUE(救援), MASTER_INHERITANCE(传承)

### 2. 事件关联设计
- 事件A的释放可以是事件B的种植
- 设计"期待链"：A种植 → B发酵 → C释放

### 3. 爽点对齐
- satisfaction_points中的爽点，前置3章必须有对应期待

### 4. 类型多样化
- 同阶段同类型不超过2个
- 相邻事件期待类型尽量不重复

## 输出格式

请严格按照以下JSON格式输出：

```json
{
  "stage_expectation_strategy": "本阶段整体期待策略简述（50字内）",
  "event_expectations": [
    {
      "event_id": "事件ID",
      "expectation_type": "TYPE_NAME",
      "reasoning": "选择理由（基于情绪曲线/事件关联/世界观展开）",
      "planting_chapter": 1,
      "target_chapter": 4,
      "linked_events": ["关联事件ID"]
    }
  ]
}
```

请确保：
1. 每个事件都有合理的期待类型
2. 种植章节 ≤ 事件开始章节
3. 目标释放章节 ≥ 事件结束章节
4. 关联事件确实有关联逻辑
5. 输出必须是合法的JSON格式，不要包含任何注释或markdown标记
""",
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
