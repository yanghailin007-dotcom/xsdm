"""配置文件"""

CONFIG = {
    "api_keys": {
        "deepseek": "sk-1342f04c85c5452ab46c673aa1a12c0b",
        "yuanbao": "sk-1342f04c85c5452ab46c673aa1a12c0b"
    },
    "api_urls": {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "yuanbao": "https://api.deepseek.com/v1/chat/completions"
    },
    "models": {
        "deepseek": "deepseek-reasoner",
        "yuanbao": "deepseek-reasoner"
    },
    "prompts": {
        "three_plans": """你是一位资深的番茄小说平台编辑和营销专家。请根据用户提供的创意种子，基于番茄小说的流量趋势和热门元素，生成三套完整的小说方案。

每套方案需要包含：
1. 吸引人的小说标题（符合番茄风格，8-15字）
2. 精彩的小说简介（200字左右，包含核心冲突和悬念）核心卖点使用[如（系统流）]圈起来，符合当前番茄潮流
3. 创作核心方向（明确的故事定位和卖点）

请确保每套方案都有不同的侧重点和创意方向，分别针对不同的读者群体和流行趋势。

请按照以下JSON格式输出：
{
    "plans": [
        {
            "title": "方案一的小说标题",
            "synopsis": "方案一的小说简介",
            "core_direction": "方案一的创作核心方向和卖点",
            "target_audience": "针对的读者群体",
            "competitive_advantage": "竞争优势分析"
        },
        {
            "title": "方案二的小说标题",
            "synopsis": "方案二的小说简介", 
            "core_direction": "方案二的创作核心方向和卖点",
            "target_audience": "针对的读者群体",
            "competitive_advantage": "竞争优势分析"
        },
        {
            "title": "方案三的小说标题",
            "synopsis": "方案三的小说简介",
            "core_direction": "方案三的创作核心方向和卖点",
            "target_audience": "针对的读者群体",
            "competitive_advantage": "竞争优势分析"
        }
    ],
    "trend_analysis": "当前番茄小说平台的整体流量趋势分析"
}""",
        "market_analysis": """你是一位资深的网络小说编辑和营销专家，特别擅长番茄小说平台。请根据用户提供的创意种子，进行市场分析和卖点提炼。

请分析以下内容：
1. 目标读者群体
2. 核心卖点和差异化优势
3. 当前市场趋势和竞争分析
4. 商业化潜力评估
5. 推荐写作策略

请确保输出是严格的JSON格式，所有字符串值都必须用双引号括起来。

请按照以下JSON格式输出：
{
    "target_audience": "目标读者群体描述",
    "core_selling_points": ["卖点1", "卖点2", "卖点3"],
    "market_trend_analysis": "市场趋势分析",
    "competitive_advantage": "竞争优势分析",
    "commercial_potential": "商业化潜力评估",
    "recommended_strategies": ["策略1", "策略2", "策略3"]
}""",
        "writing_plan": """你是一位顶级网络小说策划编辑，擅长制定完整的写作计划。请根据市场分析和创意种子，制定详细的写作计划。

请包含以下内容：
1. 整体写作思路和风格定位
2. 章节节奏安排（请按照{total_chapters}章的总长度来规划）
3. 关键情节节点规划
4. 角色成长路线
5. 大型副本/高潮剧场/重大事件

请确保输出是严格的JSON格式，所有字符串值都必须用双引号括起来。

请按照以下JSON格式输出：
{
    "writing_approach": "整体写作思路",
    "style_positioning": "风格定位",
    "chapter_rhythm": {
        "opening_chapters": "开局章节节奏",
        "development_phase": "发展阶段节奏", 
        "climax_phase": "高潮阶段节奏",
        "ending_phase": "收尾阶段节奏"
    },
    "key_plot_points": ["关键情节1", "关键情节2", "关键情节3"],
    "character_growth_arc": "角色成长路线",
    "major_events": [
        {
            "name": "事件名称",
            "type": "major_dungeon",
            "start_chapter": 开始章节,
            "end_chapter": 结束章节,
            "duration": 持续时间,
            "significance": "事件重要性描述",
            "goals": ["目标1", "目标2"],
            "key_moments": ["关键时刻1", "关键时刻2"],
            "character_development": "角色成长重点",
            "aftermath": "后续影响",
            "special_elements": "特殊元素描述"
        }
}""",
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
        "chapter_generation": """你是一位优秀的网络小说作家。请根据以下故事框架，直接生成第{chapter_number}章的完整内容。

# 故事信息
**标题**: {novel_title}
**简介**: {novel_synopsis}
**世界观**: {worldview_info}
**角色设定**: {character_info}
**写作计划**: {writing_plan_info}
**前情提要**: {previous_chapters_summary}

# 专项指导
{major_event_info}

# 伏笔铺垫指导
{foreshadowing_guidance}

# 本章定位
第{chapter_number}/{total_chapters}章 - {plot_direction}
**重点推进**: {main_plot_progress}
**角色发展**: {character_development_focus}
**衔接要求**: {chapter_connection_note}

# 核心写作要求

## 1. 标题规范
- 8-15字，吸引力强，与内容高度相关
- 确保唯一性，不与已有章节重复
- 体现核心情节或转折点

## 2. 内容结构
- **字数**: 2100-3000字
- **分段**: 短小精悍，适合手机阅读
- **开头**: 直接承接上一章结尾，避免断裂
- **结尾**: 设置悬念，吸引继续阅读

## 3. 叙事风格
- **对话占比**: 50%以上，生活化，有火药味
- **爽点设置**: 至少1个小爽点（打脸、发现线索等）
- **网络热梗**: 自然融入，古今碰撞，不生硬
- **情感共鸣**: 日常场景中融入引发共鸣的细节

## 4. 质量控制
- 严格遵循已有设定，不擅自添加重大新设定
- 保持角色性格和世界观一致性
- 避免AI痕迹：不用标记性语言、机械化结构
- 语言自然流畅，避免模式化表达

5. 章节衔接控制：
- **开头衔接**: 本章开头必须自然承接上一章的结尾，不能突兀
- **情节连贯**: 确保时间、地点、人物状态的连续性
- **悬念处理**: 妥善处理上一章留下的悬念，同时设置新的悬念
- **过渡自然**: 场景转换和情节推进要流畅自然
- **结尾悬念**: 结尾尽可能保持悬念，增加读者阅读下一章

# 伏笔和铺垫技巧
1. **势力铺垫**: 通过路人对话、新闻报道、历史背景等方式提前介绍
2. **角色铺垫**: 通过他人评价、相关事件、背景故事等方式建立期待
3. **物品铺垫**: 通过传说描述、功能暗示、获取线索等方式提前引入
4. **概念铺垫**: 通过世界观介绍、角色讨论、事件关联等方式自然呈现

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
    "connection_to_previous": "与上一章的衔接"
}}""",
        
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

# 需要评估的内容：
{content}

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

# 需要评估的内容：
{content}

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

# 评估维度（满分10分）：
1. 主角设计立体性（2分）
2. 角色背景合理性（2分）
3. 动机和成长清晰度（2分）
4. 配角设计丰满度（2分）
5. 角色关系明确性（2分）

# 需要评估的内容：
{content}

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

# 原始内容：
{original_content}

# 评估结果：
{assessment_results}

# 优化重点：
{priority_fixes}

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

# 原始内容：
{original_content}

# 评估结果：
{assessment_results}

# 优化重点：
{priority_fixes}

# 优化要求：
请保持原有结构，针对评估指出的问题进行优化，提升内容质量。
请输出优化后的完整世界观框架，使用相同的JSON格式。""",

        "character_design_optimization": """你是一位角色设计优化专家。请根据以下评估结果优化角色设计。

# 原始内容：
{original_content}

# 评估结果：
{assessment_results}

# 优化重点：
{priority_fixes}

# 优化要求：
请保持原有结构，针对评估指出的问题进行优化，提升内容质量。
请输出优化后的完整角色设计，使用相同的JSON格式。"""
    },
    "optimization_settings": {
        # 质量评分优化阈值
        "quality_thresholds": {
            "excellent": 9.0,
            "good": 8.5,
            "acceptable": 8.0,
            "needs_optimization": 7.5,
            "needs_rewrite": 6.0
        },
        
        # 优化强度配置
        "optimization_intensity": {
            "high": {
                "threshold": 7.0,
                "max_issues": 3,
                "description": "高强度优化"
            },
            "medium": {
                "threshold": 7.5,
                "max_issues": 2,
                "description": "中等强度优化"
            },
            "low": {
                "threshold": 8.0,
                "max_issues": 1,
                "description": "轻度优化"
            }
        },
        
        # 跳过优化的条件
        "skip_optimization_conditions": {
            "min_score_skip": 8.5,
            "min_ai_score_skip": 1.8,
            "word_count_range": [2000, 3000],
            "min_score_with_good_words": 8.0
        }
    },
    "writing_requirements": {
        "platform_style": "番茄小说风格：开局高能、节奏明快、情绪拉动强、对话生动",
        "chapter_length": "每章2000-3000字，开头吸引人，结尾有悬念",
        "commercial_elements": "注重爽点、虐点、甜点的合理安排",
        "character_consistency": "保持人物性格一致，成长路线清晰",
        "plot_coherence": "情节连贯，前后呼应，伏笔合理"
    },
    "defaults": {
        "temperature": 0.7,
        "max_tokens": 4000,
        "max_retries": 2,
        "json_retries": 2,
        "total_chapters": 300,
        "chapters_per_batch": 3,
        "max_optimization_attempts": 1
    },
    "optimization": {
        "skip_optimization_threshold": 8.5,
        "quick_assessment_enabled": True,
        "cache_previous_summaries": True
    },
    "subplot_ratios": {
        "by_genre": {
            "都市情感": {"main": 0.6, "emotional": 0.3, "foreshadowing": 0.1},
            "玄幻修真": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15},
            "科幻末世": {"main": 0.75, "emotional": 0.1, "foreshadowing": 0.15},
            "历史权谋": {"main": 0.65, "emotional": 0.2, "foreshadowing": 0.15},
            "悬疑推理": {"main": 0.6, "emotional": 0.1, "foreshadowing": 0.3},
            "系统流": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15},
            "无限流": {"main": 0.65, "emotional": 0.15, "foreshadowing": 0.2},
            "穿越重生": {"main": 0.7, "emotional": 0.2, "foreshadowing": 0.1},
            "默认": {"main": 0.7, "emotional": 0.2, "foreshadowing": 0.1}
        },
        "presets": {
            "情感主导": {"main": 0.6, "emotional": 0.3, "foreshadowing": 0.1},
            "悬疑主导": {"main": 0.6, "emotional": 0.1, "foreshadowing": 0.3},
            "平衡发展": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15},
            "轻度暗线": {"main": 0.8, "emotional": 0.1, "foreshadowing": 0.1},
            "重度暗线": {"main": 0.6, "emotional": 0.2, "foreshadowing": 0.2},
            "主线优先": {"main": 0.85, "emotional": 0.1, "foreshadowing": 0.05}
        }
    },
    "major_event_settings": {
        "event_types": {
            "major_dungeon": {
                "name": "大型副本",
                "min_chapters": 3,
                "max_chapters": 20,
                "typical_chapters": 8,
                "description": "集中推进核心情节的大型连续剧情"
            },
            "climax_event": {
                "name": "高潮事件", 
                "min_chapters": 2,
                "max_chapters": 10,
                "typical_chapters": 5,
                "description": "故事关键转折点的重要事件"
            },
            "arc_finale": {
                "name": "篇章结局",
                "min_chapters": 3,
                "max_chapters": 15,
                "typical_chapters": 6,
                "description": "完整故事篇章的收尾事件"
            }
        },
        "distribution_guidelines": {
            "early_stage": {"min_chapter": 1, "max_chapter": 50, "recommended_events": 1},
            "mid_stage": {"min_chapter": 51, "max_chapter": 200, "recommended_events": 3},
            "late_stage": {"min_chapter": 201, "max_chapter": 300, "recommended_events": 2}
        },
        "writing_templates": {
            "opening_stage": "建立事件基础，引入核心冲突，展示事件规模和挑战",
            "development_stage": "深化矛盾，角色成长，推进事件核心目标",
            "climax_stage": "冲突激化，关键转折，情感爆发，决定性时刻", 
            "ending_stage": "解决主要冲突，展示后果，为后续影响做铺垫"
        }
    }
}