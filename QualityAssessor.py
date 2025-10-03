"""质量评估器类 - 专注质量评估和优化"""

import re
import json
from typing import List, Dict, Optional, Tuple

class QualityAssessor:
    def __init__(self, api_client):
        self.api_client = api_client
        
        # 内化质量阈值配置
        self.quality_thresholds = {
            "excellent": 9.0,
            "good": 8.5,
            "acceptable": 8.0,
            "needs_optimization": 7.5,
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
        """评估章节质量"""
        user_prompt = self._generate_chapter_assessment_prompt(assessment_params)
        result = self.api_client.generate_content_with_retry(
            "chapter_quality_assessment", 
            user_prompt, 
            temperature=0.3, 
            purpose="章节质量评估"
        )
        return result
    
    def _generate_chapter_assessment_prompt(self, params: Dict) -> str:
        """生成章节质量评估提示词"""
        return f"""
请对以下小说章节进行全面质量评估：

小说标题: {params.get('novel_title', '未知')}
章节标题: {params.get('chapter_title', '未知')}
章节编号: 第{params.get('chapter_number', 0)}章
总章节数: {params.get('total_chapters', 0)}
字数: {params.get('word_count', 0)}

前情提要: {params.get('previous_summary', '无')}

章节内容预览:
{params.get('chapter_content', '')[:1000]}...

请从以下维度进行评估，并给出详细反馈：

1. 情节连贯性 (2分): 情节发展是否合理，逻辑是否清晰
2. 角色一致性 (2分): 角色行为是否符合设定，性格是否统一
3. 章节衔接 (2分): 与上一章的衔接是否自然，悬念处理是否得当
4. 文笔质量 (2分): 语言表达是否流畅，描写是否生动
5. AI痕迹检测 (2分): 是否存在明显的AI生成痕迹
6. 爽点设置 (2分): 情感高潮和爽点设置是否合理

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级(优秀/良好/合格/需要优化/需要重写)",
    "strengths": ["优点1", "优点2", "优点3"],
    "weaknesses": ["需要改进的方面1", "需要改进的方面2", "需要改进的方面3"],
    "detailed_scores": {{
        "plot_coherence": 情节连贯性得分,
        "character_consistency": 角色一致性得分,
        "chapter_connection": 章节衔接得分,
        "writing_quality": 文笔质量得分,
        "ai_artifacts_detected": AI痕迹检测得分,
        "emotional_impact": 爽点设置得分
    }},
    "optimization_suggestions": [
        "具体优化建议1",
        "具体优化建议2", 
        "具体优化建议3"
    ]
}}

评分说明：
- 优秀(9-10分): 质量很高，几乎无需修改
- 良好(8-8.9分): 质量良好，可轻微优化
- 合格(7-7.9分): 质量合格，建议优化提升
- 需要优化(6-6.9分): 需要重点优化
- 需要重写(<6分): 质量不合格，建议重写
"""
    
    def optimize_chapter_content(self, optimization_params: Dict) -> Optional[Dict]:
        """优化章节内容"""
        user_prompt = self._generate_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "chapter_optimization", 
            user_prompt, 
            purpose="章节内容优化"
        )
        return result
    
    def _generate_optimization_prompt(self, params: Dict) -> str:
        """生成章节优化提示词"""
        assessment = json.loads(params.get("assessment_results", "{}"))
        original_content = params.get("original_content", "")
        
        return f"""
请根据以下评估结果对章节内容进行优化：

质量评估结果:
- 总体评分: {assessment.get('overall_score', 0)}/10分
- 主要问题: {', '.join(assessment.get('weaknesses', []))}
- 优化强度: {params.get('optimization_intensity', '中度优化')}

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
4. 提升文笔质量和可读性
5. 确保章节衔接自然流畅
6. 保持字数在合理范围内(3000-5000字)

请返回优化后的完整章节内容，并按照以下JSON格式输出：
{{
    "content": "优化后的完整章节内容",
    "optimization_summary": "优化总结",
    "changes_made": ["具体修改1", "具体修改2", "具体修改3"],
    "word_count": 优化后字数,
    "quality_improvement": "质量提升说明"
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
        """判断是否需要优化章节"""
        score = assessment.get("overall_score", 0)
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

    def should_skip_optimization(self, assessment: Dict, chapter_data: Dict) -> Tuple[bool, str]:
        """判断是否应该跳过优化"""
        score = assessment.get("overall_score", 0)
        skip_config = self.optimization_settings["skip_optimization_conditions"]
        
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
    
    def get_optimization_intensity(self, score: float) -> Dict:
        """获取优化强度配置"""
        intensity_configs = self.optimization_settings["optimization_intensity"]
        
        if score < intensity_configs["high"]["threshold"]:
            return intensity_configs["high"]
        elif score < intensity_configs["medium"]["threshold"]:
            return intensity_configs["medium"]
        elif score < intensity_configs["low"]["threshold"]:
            return intensity_configs["low"]
        else:
            return {"max_issues": 0, "description": "无需优化"}
        
    def _quick_optimize_chapter(self, chapter_data: Dict, assessment: Dict) -> Optional[Dict]:
        """快速优化章节"""
        score = assessment.get("overall_score", 0)
        weaknesses = assessment.get("weaknesses", [])
        
        intensity_config = self.get_optimization_intensity(score)
        
        if intensity_config["max_issues"] == 0:
            return None
        
        priority_issues = weaknesses[:intensity_config["max_issues"]]
        
        if not priority_issues:
            if score < self.quality_thresholds["needs_optimization"]:
                priority_issues = ["提升情节连贯性", "增强角色表现", "改善文笔质量"]
            else:
                return None
        
        optimization_params = {
            "assessment_results": json.dumps({
                "weaknesses": priority_issues,
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
        """快速评估章节质量"""
        return self.assess_chapter_quality({
            "chapter_content": chapter_content,
            "chapter_title": chapter_title,
            "chapter_number": chapter_number,
            "novel_title": novel_title,
            "previous_summary": previous_summary,
            "total_chapters": 100,  # 默认值，实际使用时应该传入
            "word_count": word_count
        })
        
    def assess_foreshadowing_consistency(self, content: str, previous_chapters: List[str]) -> float:
        """评估伏笔一致性"""
        score = 2.0
        
        qg_patterns = [
            r"突然.*出现",
            r"没想到.*竟然",
            r"毫无征兆.*",
            r"凭空.*出现"
        ]
        
        for pattern in qg_patterns:
            if re.search(pattern, content):
                score -= 0.5
        
        return max(0, score)

    def _local_quality_check(self, content: str, title: str, word_count: int) -> float:
        """本地质量检查"""
        score = 10.0
        
        if word_count == 0:
            word_count = len(content)
        
        if word_count < 1800:
            score -= 2
        elif word_count > 3500:
            score -= 1
        
        if len(title) < 4 or len(title) > 20:
            score -= 1
        
        ai_artifacts = self.detect_ai_artifacts(content)
        if ai_artifacts:
            score -= len(ai_artifacts) * 0.5
        
        return max(0, score)

    def _lightweight_api_assessment(self, content: str, title: str, chapter_number: int, 
                                novel_title: str, previous_summary: str, word_count: int) -> Dict:
        """轻量级API评估"""
        lightweight_prompt = f"""
请快速评估以下章节的质量（满分10分）：
标题：{title}
章节：第{chapter_number}章
小说：{novel_title}
字数：{word_count}
前情提要：{previous_summary[:200] if previous_summary else "无"}
内容预览：{content[:500]}...

只需返回JSON格式：
{{
    "overall_score": 分数,
    "quick_feedback": "简要反馈",
    "detailed_scores": {{
        "plot_coherence": 1.8,
        "character_consistency": 1.8, 
        "chapter_connection": 1.8,
        "writing_quality": 1.8,
        "ai_artifacts_detected": 1.8,
        "emotional_impact": 1.8
    }}
}}
"""
        result = self.api_client.call_api('deepseek', "你是质量评估专家", lightweight_prompt, 0.3, purpose="快速质量评估")
        if result:
            parsed = self.api_client.parse_json_response(result)
            if parsed:
                return parsed
        return {
            "overall_score": 8.0, 
            "quick_feedback": "评估失败，使用默认分数",
            "detailed_scores": {
                "plot_coherence": 1.5,
                "character_consistency": 1.5,
                "chapter_connection": 1.5,
                "writing_quality": 1.5,
                "ai_artifacts_detected": 1.5,
                "emotional_impact": 1.5
            }
        }

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

评估维度：
1. 世界观完整性 (2分): 世界观设定是否完整自洽
2. 创新性 (2分): 是否有独特的创新元素
3. 逻辑合理性 (2分): 设定是否符合逻辑和常识
4. 故事适配性 (2分): 是否适合故事发展和角色成长
5. 细节丰富度 (2分): 设定细节是否丰富具体

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级",
    "strengths": ["优点列表"],
    "weaknesses": ["待改进方面列表"],
    "optimization_suggestions": ["优化建议列表"]
}}
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
请评估以下角色设计的质量：

角色设计内容:
{json.dumps(character_design, ensure_ascii=False, indent=2)}

评估维度：
1. 角色立体性 (2分): 角色性格和背景是否立体丰满
2. 动机合理性 (2分): 角色行为和动机是否合理
3. 成长空间 (2分): 角色是否有足够的成长空间
4. 关系设计 (2分): 角色关系设计是否合理有趣
5. 故事适配性 (2分): 角色是否适合故事发展和世界观

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级",
    "strengths": ["优点列表"],
    "weaknesses": ["待改进方面列表"],
    "optimization_suggestions": ["优化建议列表"]
}}
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

优化要求:
1. 保持核心设定不变
2. 重点解决评估中发现的问题
3. 提升世界观的完整性和逻辑性
4. 加强创新元素和独特性
5. 丰富设定细节和深度

请返回优化后的完整世界观内容。
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

优化要求:
1. 保持核心角色设定不变
2. 重点解决评估中发现的问题
3. 提升角色的立体性和真实感
4. 优化角色动机和成长设计
5. 加强角色关系和互动设计

请返回优化后的完整角色设计内容。
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