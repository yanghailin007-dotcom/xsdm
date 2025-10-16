"""质量评估器类 - 专注质量评估和优化"""

import re
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import WorldStateManager

class QualityAssessor:
    def __init__(self, api_client, storage_path: str = "./quality_data"):
        self.api_client = api_client
        self.storage_path = storage_path
        
        # 初始化世界状态管理器
        self.world_state_manager = WorldStateManager.WorldStateManager(storage_path)
        
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

    # ==================== 质量评估核心方法 ====================
    
    def assess_chapter_quality(self, assessment_params: Dict) -> Optional[Dict]:
        """评估章节质量（包含一致性检查）- 增强黄金三章评估"""
        user_prompt = self._generate_chapter_assessment_prompt(assessment_params)
        result = self.api_client.generate_content_with_retry(
            "chapter_quality_assessment", 
            user_prompt, 
            temperature=0.3, 
            purpose="章节质量评估"
        )
        
        # 如果评估成功，处理黄金三章的特殊逻辑
        if result and 'overall_score' in result:
            chapter_number = assessment_params.get('chapter_number', 0)
            
            # 如果是黄金三章，应用更严格的标准
            if 1 <= chapter_number <= 3:
                result = self._apply_golden_chapters_standards(result, chapter_number)
            
            # 原有的处理逻辑...
            novel_title = assessment_params.get('novel_title', 'unknown')
            
            # 处理角色状态变化
            character_status_changes = result.get('character_status_changes', [])
            for status_change in character_status_changes:
                character_name = status_change.get('character_name')
                status = status_change.get('status')
                if character_name and status in ['dead', 'exited']:
                    print(f"🔄 AI检测到角色状态变化: {character_name} -> {status}")
                    self.world_state_manager._simplify_character_status(novel_title, character_name, status, chapter_number)
            
            # 处理世界状态增量更新
            if 'world_state_changes' in result:
                print("🧹 清洗世界状态变化数据...")
                cleaned_changes = self.world_state_manager._validate_and_clean_world_state_changes(
                    result['world_state_changes'], 
                    chapter_number
                )
                
                if cleaned_changes:
                    self.world_state_manager._update_world_state_incrementally(novel_title, cleaned_changes, chapter_number)
                    result['updated_world_state'] = self.world_state_manager.current_world_state
                    result['world_state_changes'] = cleaned_changes
                else:
                    print("⚠️ 世界状态变化数据清洗后为空")
            
            self.world_state_manager.save_assessment_data(novel_title, chapter_number, result)
            self.world_state_manager.update_character_development_from_assessment(novel_title, result, chapter_number)
                
        return result

    def _apply_golden_chapters_standards(self, assessment_result: Dict, chapter_number: int) -> Dict:
        """对黄金三章应用更严格的评分标准"""
        
        # 黄金三章的特殊评分维度
        golden_chapters_criteria = {
            1: {
                "criteria": {
                    "opening_hook": 0.25,  # 开篇钩子权重25%
                    "protagonist_intro": 0.25,  # 主角介绍权重25%
                    "conflict_setup": 0.20,  # 冲突设置权重20%
                    "world_building": 0.15,  # 世界观展示权重15%
                    "pacing": 0.15  # 节奏控制权重15%
                },
                "minimum_acceptable": 8.5,
                "excellent_threshold": 9.2
            },
            2: {
                "criteria": {
                    "conflict_development": 0.25,
                    "character_relationship": 0.20,
                    "plot_progression": 0.20,
                    "suspense_building": 0.20,
                    "pacing": 0.15
                },
                "minimum_acceptable": 8.5,
                "excellent_threshold": 9.1
            },
            3: {
                "criteria": {
                    "climax_execution": 0.25,
                    "foreshadowing": 0.20,
                    "reader_engagement": 0.25,
                    "chapter_ending": 0.20,
                    "series_hook": 0.10
                },
                "minimum_acceptable": 8.5,
                "excellent_threshold": 9.0
            }
        }
        
        chapter_criteria = golden_chapters_criteria.get(chapter_number, {})
        if not chapter_criteria:
            return assessment_result
        
        # 调整总体评分
        original_score = assessment_result.get("overall_score", 0)
        
        # 如果有详细分数，按照黄金三章标准重新计算
        if "detailed_scores" in assessment_result:
            detailed = assessment_result["detailed_scores"]
            new_score = 0
            
            for criterion, weight in chapter_criteria["criteria"].items():
                # 将原有的分数映射到新标准
                criterion_score = detailed.get(criterion, original_score)
                new_score += criterion_score * weight
            
            assessment_result["overall_score"] = min(10.0, new_score * 2)  # 转换为10分制
        
        # 添加黄金三章特殊评估
        assessment_result["golden_chapters_assessment"] = {
            "chapter_number": chapter_number,
            "special_criteria": chapter_criteria["criteria"],
            "is_acceptable": assessment_result["overall_score"] >= chapter_criteria["minimum_acceptable"],
            "quality_tier": self._get_golden_chapters_quality_tier(assessment_result["overall_score"]),
            "improvement_suggestions": self._generate_golden_chapters_suggestions(assessment_result, chapter_number)
        }
        
        return assessment_result

    def _get_golden_chapters_quality_tier(self, score: float) -> str:
        """获取黄金三章质量等级"""
        if score >= 9.2:
            return "S级 - 完美开篇"
        elif score >= 8.8:
            return "A级 - 优秀开篇" 
        elif score >= 8.5:
            return "B级 - 合格开篇"
        else:
            return "C级 - 需要重写"

    def _generate_golden_chapters_suggestions(self, assessment: Dict, chapter_number: int) -> List[str]:
        """生成黄金三章改进建议"""
        score = assessment.get("overall_score", 0)
        weaknesses = assessment.get("weaknesses", [])
        
        suggestions = []
        
        # 基于章节号的特殊建议
        if chapter_number == 1 and score < 8.8:
            suggestions.extend([
                "检查开篇500字是否足够吸引人",
                "强化主角登场场景的冲击力", 
                "确保冲突在开篇立即展现",
                "优化世界观展示的自然程度"
            ])
        elif chapter_number == 2 and score < 8.8:
            suggestions.extend([
                "深化第一章引入的冲突",
                "加强主角与配角的互动质量",
                "确保情节推进的节奏感",
                "检查悬念设置的强度"
            ])
        elif chapter_number == 3 and score < 8.8:
            suggestions.extend([
                "强化章节小高潮的情感冲击",
                "优化伏笔设置的自然程度",
                "检查章节结尾的追读钩子强度",
                "确保读者有强烈继续阅读的欲望"
            ])
        
        # 基于弱点的具体建议
        for weakness in weaknesses[:3]:
            if "开篇" in weakness or "开头" in weakness:
                suggestions.append("重新设计开篇场景，增加冲击力")
            elif "节奏" in weakness:
                suggestions.append("调整节奏，删除冗余描写")
            elif "悬念" in weakness:
                suggestions.append("加强悬念设置，提高读者好奇心")
            elif "主角" in weakness:
                suggestions.append("强化主角魅力和特质展现")
        
        return suggestions[:5]  # 返回前5个最重要的建议

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

    def _generate_chapter_assessment_prompt(self, params: Dict) -> str:
        """生成章节质量评估提示词（重新组织修为+物品+功法结构）"""
        
        # 加载之前的世界状态
        novel_title = params.get('novel_title', 'unknown')
        previous_world_state = self.world_state_manager.load_previous_assessments(novel_title)
        
        world_state_str = json.dumps(previous_world_state, ensure_ascii=False, indent=2) if previous_world_state else "{}"

        character_development_data = self._load_character_development_data(novel_title)
        character_development_str = json.dumps(character_development_data, ensure_ascii=False, indent=2) if character_development_data else "{}"        
        
        return f"""
    内容：
    你是一位资深的番茄小说内容分析师与世界观架构师。
    你的任务是根据提供的章节信息和之前的世界观状态，进行全面的质量评估，并识别出本章节对世界观的具体变化。

    ### 重要字段约定 - 重新组织为修为+物品+功法结构
    在返回的world_state_changes中，请严格遵守以下字段结构：

    **角色 (characters):**
    - description: string (角色当前状态描述)
    - attributes: object (包含以下固定字段)
      - status: string (活跃/死亡/退场/重伤/失踪)
      - location: string (当前所在地点)
      - title: string (称号/头衔，可选)
      - occupation: string (职业/身份，可选)
      - faction: string (所属势力，可选)
      - cultivation_level: string (修为等级) # 核心：角色当前修为
      - cultivation_system: string (修为体系) # 核心：修仙/异能/武侠等
      - emotional_state: string (情绪状态) # 新增：愤怒/平静/喜悦/悲伤等

    **修炼物品 (cultivation_items):**
    - description: string (物品描述)
    - owner: string (拥有者)
    - type: string (类型：丹药/法宝/材料/符箓/功法典籍等)
    - quality: string (品质：凡品/黄阶/玄阶/地阶/天阶/神品)
    - status: string (物品状态：已使用/未使用/损坏/遗失)
    - location: string (物品位置)
    - effect: string (效果描述) # 新增

    **功法技能 (cultivation_skills):**
    - description: string (技能描述)
    - owner: string (拥有者)
    - type: string (类型：功法/神通/秘术/体质/心法等)
    - level: string (掌握程度：入门/小成/大成/圆满)
    - quality: string (品质：凡品/黄阶/玄阶/地阶/天阶/神品)
    - status: string (技能状态：已掌握/修炼中/封印中)

    **关系变化 (relationships):** # 增强关系描述
    - type: string (关系类型：师徒/道侣/兄弟/仇敌/盟友/主仆)
    - description: string (关系详细描述)
    - status: string (关系状态：稳固/紧张/破裂/改善)
    - intimacy_level: number (亲密度1-10) # 新增
    - conflict_level: number (冲突度1-10) # 新增

    **心理状态记录 (mental_states):** # 新增：专门记录心理状态
    - character: string (角色名)
    - emotional_state: string (情绪状态)
    - motivation: string (当前动机)
    - internal_conflict: string (内心矛盾)
    - recent_trauma: string (近期创伤)
    - hope_fear: string (希望与恐惧)

    **地点 (locations):**
    - description: string (地点描述)
    - status: string (地点状态：安全/危险/探索中/已废弃)
    - significance: string (重要性) # 新增

    ### 信息记录规则
    请按照以下分类准确记录：

    1. **角色修为信息**：
    - cultivation_level: 当前修为等级（如：练气三层、筑基中期、金丹后期）
    - cultivation_system: 修为体系（如：修仙、异能、武侠、科技）

    2. **修炼物品分类**：
    - 丹药类：修炼丹药、疗伤丹药、突破丹药等
    - 法宝类：武器、防具、辅助法宝等
    - 材料类：灵草、矿石、妖兽材料等
    - 符箓类：攻击符、防御符、辅助符等

    3. **功法技能分类**：
    - 功法类：修炼心法、基础功法等
    - 神通类：攻击神通、防御神通、辅助神通等
    - 秘术类：特殊秘法、禁术等
    - 体质类：特殊体质、天赋等

    ### 1. 小说信息
    - **小说标题**: {params.get('novel_title', '未知')}
    - **章节标题**: {params.get('chapter_title', '未知')}
    - **章节编号**: {params.get('chapter_number', '未知')}
    - **前情提要**: {params.get('previous_summary', '无')}

    ### 2. 目前章节的世界状态
    {world_state_str}

    现有角色发展数据:
    {character_development_str}

    章节内容预览:
    {params.get('chapter_content', '')}

    请按照以下JSON格式返回评估结果：
    {{
        "overall_score": "number (0-10，基于细分维度计算)",
        "quality_verdict": "string (根据分数评定，如'卓越', '优秀', '良好', '合格'等)",
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
                "type": "string (枚举: CHARACTER, ITEM, RELATIONSHIP, SKILL, TIMELINE, LOCATION, CULTIVATION)", 
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
            // 严格遵守字段约定，重新组织为修为+物品+功法结构
            "characters": {{
                "角色名": {{
                    "description": "string (角色描述)",
                    "attributes": {{
                        "status": "string (活跃/死亡/退场)",
                        "location": "string (当前所在地点)",
                        "title": "string (可选)",
                        "occupation": "string (可选)",
                        "faction": "string (可选)",
                        "cultivation_level": "string (修为等级)",
                        "cultivation_system": "string (修为体系)"
                    }}
                }}
            }},
            "cultivation_items": {{
                "物品名": {{
                    "description": "string (物品描述)",
                    "owner": "string (拥有者)",
                    "type": "string (丹药/法宝/材料/符箓等)",
                    "quality": "string (品质等级)",
                    "status": "string (物品状态)",
                    "location": "string (物品位置)"
                }}
            }},
            "cultivation_skills": {{
                "技能名": {{
                    "description": "string (技能描述)",
                    "owner": "string (拥有者)",
                    "type": "string (功法/神通/秘术/体质等)",
                    "level": "string (掌握程度)",
                    "quality": "string (品质等级)",
                    "status": "string (技能状态)"
                }}
            }},
            "relationships": {{
                "角色A-角色B": {{
                    "type": "string (关系类型)",
                    "description": "string (关系描述)",
                    "status": "string (目前的实际关系状态)"
                }}
            }},
            "locations": {{
                "地点名": {{
                    "description": "string (地点描述)",
                    "status": "string (地点状态)"
                }}
            }}
        }},
        "assessment_timestamp": "string (生成报告的ISO 8601格式时间戳，例如: '2024-05-16T12:00:00Z')"
    }}

    重要说明：
    1. 严格按照新的分类结构记录：修为+物品+功法
    2. 角色修为信息集中在characters的cultivation_level和cultivation_system字段
    3. 所有修炼相关物品归入cultivation_items，并按类型分类
    4. 所有功法技能归入cultivation_skills，并按类型分类
    5. world_state_changes只包含本章节新增或发生变化的世界状态元素
    """

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
        full_world_state = self.world_state_manager.load_previous_assessments(novel_title)
        
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

    # ==================== 质量决策方法 ====================

    def should_optimize_chapter(self, assessment: Dict) -> Tuple[bool, str]:
        """判断是否需要优化章节（考虑黄金三章特殊要求）"""
        score = assessment.get("overall_score", 0)
        consistency_issues = assessment.get("consistency_issues", [])
        chapter_info = assessment.get("golden_chapters_assessment", {})
        
        # 检查是否为黄金三章
        is_golden_chapter = chapter_info.get("chapter_number", 0) in [1, 2, 3]
        
        # 黄金三章的特殊优化逻辑
        if is_golden_chapter:
            golden_minimum = 8.5
            if score < golden_minimum:
                return True, f"黄金三章评分低于{golden_minimum}分，必须优化"
            elif not chapter_info.get("is_acceptable", True):
                return True, "黄金三章未达到可接受标准"
        
        # 原有的优化逻辑（严重一致性问题的处理）
        severe_consistency_issues = [issue for issue in consistency_issues 
                                if issue.get('severity') == '高']
        
        if severe_consistency_issues:
            return True, f"存在{len(severe_consistency_issues)}个严重一致性问題，需要优化"
        
        thresholds = self.quality_thresholds
        
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

    # ==================== 快速评估方法 ====================

    def quick_assess_chapter_quality(self, chapter_content: str, chapter_title: str, 
                                chapter_number: int, novel_title: str, previous_summary: str, 
                                word_count: int = 0) -> Dict:
        """快速评估章节质量（包含一致性检查）"""
        # 加载之前的世界状态
        self.world_state_manager.current_world_state = self.world_state_manager.load_previous_assessments(novel_title)
        
        return self.assess_chapter_quality({
            "chapter_content": chapter_content,
            "chapter_title": chapter_title,
            "chapter_number": chapter_number,
            "novel_title": novel_title,
            "previous_summary": previous_summary,
            "total_chapters": 100,  # 默认值，实际使用时应该传入
            "word_count": word_count
        })

    # ==================== 其他内容类型评估 ====================

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

    # ==================== 其他内容类型优化 ====================

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

    # ==================== 统计分析 ====================

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

    # ==================== 缺失的方法修复 ====================

    def _load_character_development_data(self, novel_title: str) -> Dict:
        """加载角色发展数据 - 修复缺失的方法"""
        return self.world_state_manager._load_character_development_data(novel_title)

    def get_comprehensive_previous_summary_enhanced(self, novel_title: str, chapter_number: int) -> str:
        """增强版前情提要生成"""
        character_status = self.world_state_manager.get_character_comprehensive_status_enhanced(novel_title)
        
        if not character_status:
            return "暂无角色状态信息"
        
        summary_parts = ["【主要角色状态】"]
        
        for char_name, status in character_status.items():
            char_summary = self._format_character_summary_enhanced(char_name, status, chapter_number)
            summary_parts.append(char_summary)
        
        return "\n".join(summary_parts)

    def _format_character_summary_enhanced(self, char_name: str, status: Dict, current_chapter: int) -> str:
        """增强版角色摘要格式化"""
        parts = []
        
        basic_info = status["basic_info"]
        cultivation_info = status["cultivation_info"]
        mental_state = status["mental_state"]
        
        # 基础状态行 - 增强位置和状态显示
        status_line = f"{char_name}"
        if cultivation_info.get("cultivation_level") and cultivation_info["cultivation_level"] != "未知":
            status_line += f"（{cultivation_info['cultivation_level']}）"
        
        location = cultivation_info.get("location", "")
        location_status = cultivation_info.get("location_status", "")
        
        if location_status == "移动中":
            status_line += f" 🚶{location}"
        else:
            status_line += f" 📍{location}"
        
        parts.append(status_line)
        
        # 心理状态和情绪 - 使用推断的情绪
        emotional_state = mental_state.get("recent_emotional_state", "平静")
        if mental_state.get("core_traits"):
            traits = "、".join(mental_state["core_traits"][:2])
            parts.append(f"  💭{traits}，情绪：{emotional_state}")
        
        # 重要关系 - 使用清理后的关系
        relationships = status["relationships"][:2]
        if relationships:
            rel_icons = {
                "师徒": "👥", "竞争师徒": "⚔️👥", "对手": "⚔️", 
                "敌对": "🔥", "盟友": "🤝", "道侣": "❤️"
            }
            
            rel_texts = []
            for rel in relationships:
                icon = rel_icons.get(rel["type"], "•")
                rel_texts.append(f"{icon}{rel['character']}（{rel['type']}）")
            
            parts.append(f"  🔗关系：{'，'.join(rel_texts)}")
        
        # 近期发展
        recent_dev = status["recent_development"]
        if recent_dev.get("milestones"):
            latest_milestone = recent_dev["milestones"][-1]
            milestone_icon = "⭐" if latest_milestone.get("type") in ["突破", "获得宝物"] else "📌"
            parts.append(f"  {milestone_icon}近期：{latest_milestone.get('description', '有所进展')}")
        
        return "\n".join(parts)

    def _get_recent_important_events(self, world_state: Dict, current_chapter: int) -> List[str]:
        """获取近期重要事件"""
        events = []
        
        # 检查角色状态变化（死亡、重伤等）
        characters = world_state.get("characters", {})
        for char_name, char_data in characters.items():
            attributes = char_data.get("attributes", {})
            last_updated = char_data.get("last_updated", 0)
            
            # 只关注最近3章内的事件
            if current_chapter - last_updated <= 3:
                status = attributes.get("status", "")
                if status in ["死亡", "重伤", "失踪"]:
                    events.append(f"• {char_name}{status}")
        
        return events[:3]  # 最多返回3个事件

    def _get_key_updates(self, world_state: Dict, current_chapter: int) -> List[str]:
        """获取关键物品和功法更新"""
        updates = []
        
        # 高品质物品获取
        cultivation_items = world_state.get("cultivation_items", {})
        for item_name, item_data in cultivation_items.items():
            last_updated = item_data.get("last_updated", 0)
            quality = item_data.get("quality", "")
            owner = item_data.get("owner", "")
            
            if (current_chapter - last_updated <= 3 and 
                quality in ["地阶", "天阶", "神品"] and owner):
                updates.append(f"• {owner}获得{quality}物品「{item_name}」")
        
        # 重要功法掌握
        cultivation_skills = world_state.get("cultivation_skills", {})
        for skill_name, skill_data in cultivation_skills.items():
            last_updated = skill_data.get("last_updated", 0)
            quality = skill_data.get("quality", "")
            owner = skill_data.get("owner", "")
            
            if (current_chapter - last_updated <= 3 and 
                quality in ["地阶", "天阶", "神品"] and owner):
                updates.append(f"• {owner}掌握{quality}功法「{skill_name}」")
        
        return updates[:3]  # 最多返回3个更新


    def load_previous_assessments(self, novel_title: str, novel_data: Dict = None) -> Dict:
        """向后兼容：加载之前章节的评估数据"""
        return self.world_state_manager.load_previous_assessments(novel_title, novel_data)

    def save_assessment_data(self, novel_title: str, chapter_number: int, assessment_data: Dict):
        """向后兼容：保存评估数据"""
        self.world_state_manager.save_assessment_data(novel_title, chapter_number, assessment_data)

    def assess_character_importance(self, character_data: Dict, chapter_content: str = "") -> str:
        """向后兼容：评估角色重要性"""
        return self.world_state_manager.assess_character_importance(character_data, chapter_content)

    def manage_character_development_table(self, novel_title: str, character_data: Dict, 
                                        current_chapter: int, action: str = "update") -> Dict:
        """向后兼容：管理角色发展表"""
        return self.world_state_manager.manage_character_development_table(novel_title, character_data, current_chapter, action)

    def get_character_development_suggestions(self, character_name: str, novel_title: str, current_chapter: int) -> List[Dict]:
        """向后兼容：获取角色发展建议"""
        return self.world_state_manager.get_character_development_suggestions(character_name, novel_title, current_chapter)

    def assess_character_development(self, chapter_content: str, characters_in_chapter: List[str], 
                                novel_title: str, chapter_number: int) -> Dict:
        """向后兼容：评估角色发展质量"""
        return self.world_state_manager.assess_character_development(chapter_content, characters_in_chapter, novel_title, chapter_number)

    def update_character_development_from_assessment(self, novel_title: str, assessment: Dict, chapter_number: int):
        """向后兼容：从评估结果更新角色发展表"""
        self.world_state_manager.update_character_development_from_assessment(novel_title, assessment, chapter_number)

    def initialize_world_state_from_novel_data(self, novel_title: str, novel_data: Dict):
        """向后兼容：基于小说数据初始化世界状态"""
        return self.world_state_manager.initialize_world_state_from_novel_data(novel_title, novel_data)

    def cleanup_characters_by_strategy(self, novel_title: str, strategy_config: Dict) -> Dict:
        """向后兼容：根据策略清理角色数据"""
        return self.world_state_manager.cleanup_characters_by_strategy(novel_title, strategy_config)

    def get_novel_consistency_report(self, novel_title: str) -> Dict:
        """向后兼容：获取小说的整体一致性报告"""
        return self.world_state_manager.get_novel_consistency_report(novel_title)