"""质量评估器类"""

import re
import json
from typing import List, Dict, Optional, Tuple

class QualityAssessor:
    def __init__(self, api_client, config):
        self.api_client = api_client
        self.config = config
    
    def detect_ai_artifacts(self, content: str) -> List[str]:
        """检测章节内容中的AI痕迹"""
        artifacts = []
        
        # 检测明显的标记性语言
        marker_patterns = [
            # 原有模式
            r'\*\*.*?：\*\*',                    # **伏笔植入：** 等加粗标记
            r'【.*?】',                          # 【情节转折】等方括号标记
            r'第一[点、]|第二[点、]|第三[点、]',  # 编号式叙述
            r'首先，|其次，|然后，|最后，',        # 机械过渡词
            r'总的来说，|综上所述，|总而言之，',   # 模式化总结
            
            # 新增AI常用标记性表达
            # 1. 写作分析类标记
            r'伏笔植入|铺垫手法|情节设计|结构安排',
            r'人物塑造|角色刻画|性格描写|形象建立',
            r'主题表达|思想内涵|深层意义|价值取向',
            r'情感渲染|气氛营造|情绪铺垫|感染力',
            
            # 2. 技术性分析词汇
            r'叙事视角|叙述方式|描写手法|表现技巧',
            r'节奏控制|张弛有度|高潮部分|结局处理',
            r'象征意义|隐喻手法|对比运用|反复强调',
            
            # 3. AI常用过渡短语
            r'在此基础上，|进一步来说，|值得注意的是，',
            r'从另一个角度|换而言之|具体而言',
            r'需要指出的是|值得关注的是|不容忽视的是',
            
            # 4. 格式化小标题
            r'^[\d一二三四五六七八九十]、',          # 数字或中文编号
            r'^[•\-*]\s',                         # 项目符号
            r'^[A-Za-z]\.',                       # 字母编号
            
            # 5. 评价性总结语
            r'使故事更加|让情节更|增强了作品的',
            r'提升了文章的|丰富了内容的|深化了主题的',
            r'达到了.*效果|产生了.*影响|具有.*价值',
            
            # 6. 人物关系描述模式
            r'人物关系方面，|角色互动上，|彼此之间',
            r'父子关系|母女关系|夫妻关系|朋友关系',
            r'矛盾冲突|情感纠葛|关系发展|互动模式',
            
            # 7. 结构分析标记
            r'开头部分|中间段落|结尾处|整体结构',
            r'起承转合|前后呼应|层层递进|环环相扣',
            
            # 8. 文学分析术语
            r'艺术特色|文学价值|创作特点|风格特征',
            r'语言优美|文字精炼|表达生动|描写细腻'
        ]
        
        for pattern in marker_patterns:
            matches = re.findall(pattern, content)
            if matches:
                artifacts.append(f"模式化标记: {matches[:3]}")
        
        # 检测重复的句式结构
        sentences = re.split(r'[。！？]', content)
        
        for sentence in sentences:
            if len(sentence) > 10:  # 只分析较长的句子
                # 简单的句式模式检测
                if "一边" in sentence and sentence.count("一边") > 1:
                    artifacts.append("重复句式: 一边...一边...")
                if "不仅" in sentence and "而且" in sentence:
                    artifacts.append("重复句式: 不仅...而且...")
        
        # 检测过度使用的词汇
        overused_words = ["显然", "无疑", "实际上", "事实上", "可以说", "值得注意的是"]
        for word in overused_words:
            count = content.count(word)
            if count > 3:  # 出现超过3次
                artifacts.append(f"过度使用词汇: '{word}'出现{count}次")
        
        return artifacts[:10]
    
    def assess_chapter_quality(self, assessment_params: Dict) -> Optional[Dict]:
        """评估章节质量"""
        user_prompt = self.config["prompts"]["chapter_quality_assessment"].format(**assessment_params)
        result = self.api_client.generate_content_with_retry("chapter_quality_assessment", user_prompt, temperature=0.3, purpose="章节质量评估")
        return result
    
    def optimize_chapter_content(self, optimization_params: Dict) -> Optional[Dict]:
        """优化章节内容"""
        user_prompt = self.config["prompts"]["chapter_optimization"].format(**optimization_params)
        result = self.api_client.generate_content_with_retry("chapter_optimization", user_prompt, purpose="章节内容优化")
        return result
    
    def get_quality_verdict(self, score: float) -> Tuple[str, str]:
        """根据评分获取质量判定和建议"""
        thresholds = self.config.get("optimization_settings", {}).get("quality_thresholds", {
            "excellent": 9.0,
            "good": 8.5,
            "acceptable": 8.0,
            "needs_optimization": 7.5,
            "needs_rewrite": 6.0
        })
        
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
        thresholds = self.config["optimization_settings"]["quality_thresholds"]
        
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
        """智能判断是否跳过优化步骤"""
        score = assessment.get("overall_score", 0)
        skip_config = self.config["optimization_settings"]["skip_optimization_conditions"]
        
        # 高质量章节直接跳过优化
        if score >= skip_config["min_score_skip"]:
            return True, "质量优秀，跳过优化"
        
        # 检查AI痕迹得分
        ai_score = assessment.get("detailed_scores", {}).get("ai_artifacts_detected", 2)
        if ai_score >= skip_config["min_ai_score_skip"]:
            return True, "AI痕迹较少，跳过优化"
        
        # 检查字数是否合适
        word_count = chapter_data.get("word_count", 0)
        word_range = skip_config["word_count_range"]
        if word_range[0] <= word_count <= word_range[1]:
            # 字数合适且质量尚可的章节
            if score >= skip_config["min_score_with_good_words"]:
                return True, "字数合适且质量良好，跳过优化"
        
        return False, "需要优化"
    
    def get_optimization_intensity(self, score: float) -> Dict:
        """根据评分获取优化强度配置"""
        intensity_configs = self.config["optimization_settings"]["optimization_intensity"]
        
        if score < intensity_configs["high"]["threshold"]:
            return intensity_configs["high"]
        elif score < intensity_configs["medium"]["threshold"]:
            return intensity_configs["medium"]
        elif score < intensity_configs["low"]["threshold"]:
            return intensity_configs["low"]
        else:
            return {"max_issues": 0, "description": "无需优化"}
        
    def _quick_optimize_chapter(self, chapter_data: Dict, assessment: Dict) -> Optional[Dict]:
        """快速优化章节 - 基于配置的优化强度"""
        score = assessment.get("overall_score", 0)
        weaknesses = assessment.get("weaknesses", [])
        
        # 获取优化强度配置
        intensity_config = self.get_optimization_intensity(score)
        
        if intensity_config["max_issues"] == 0:
            return None  # 无需优化
        
        # 根据优化强度选择问题数量
        priority_issues = weaknesses[:intensity_config["max_issues"]]
        
        if not priority_issues:
            # 如果没有明确弱点，根据低分进行通用优化
            if score < self.config["optimization_settings"]["quality_thresholds"]["needs_optimization"]:
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
        
        print(f"  🔧 进行{intensity_config['description']}，处理问题: {', '.join(priority_issues)}")
        return self.optimize_chapter_content(optimization_params)   
         
    def quick_assess_chapter_quality(self, chapter_content: str, chapter_title: str, 
                                chapter_number: int, novel_title: str, previous_summary: str, 
                                word_count: int = 0) -> Dict:
        return self.assess_chapter_quality({
            "chapter_content": chapter_content,
            "chapter_title": chapter_title,
            "chapter_number": chapter_number,
            "novel_title": novel_title,
            "previous_summary": previous_summary,
            "total_chapters": self.config["defaults"]["total_chapters"],
            "word_count": word_count
        })
        
    def assess_foreshadowing_consistency(self, content: str, previous_chapters: List[str]) -> float:
        """评估伏笔连贯性"""
        score = 2.0  # 满分2分
        
        # 检查是否有突兀的新元素引入
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
        """本地质量快速检查 - 修复版本：使用传入的 word_count"""
        score = 10.0
        
        # 使用传入的字数，如果没有则计算
        if word_count == 0:
            word_count = len(content)
        
        # 检查字数
        if word_count < 1800:
            score -= 2
        elif word_count > 3500:
            score -= 1
        
        # 检查标题长度
        if len(title) < 4 or len(title) > 20:
            score -= 1
        
        # 检查AI痕迹
        ai_artifacts = self.detect_ai_artifacts(content)
        if ai_artifacts:
            score -= len(ai_artifacts) * 0.5
        
        return max(0, score)

    def _lightweight_api_assessment(self, content: str, title: str, chapter_number: int, 
                                novel_title: str, previous_summary: str, word_count: int) -> Dict:
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
    # 在 QualityAssessor 类中添加以下方法
    def assess_market_analysis_quality(self, market_analysis: Dict) -> Dict:
        """评估市场分析质量"""
        if not market_analysis:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self.config["prompts"]["market_analysis_quality_assessment"].format(
            content=json.dumps(market_analysis, ensure_ascii=False, indent=2)
        )
        
        result = self.api_client.generate_content_with_retry(
            "market_analysis_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="市场分析质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def assess_writing_plan_quality(self, writing_plan: Dict) -> Dict:
        """评估写作计划质量"""
        if not writing_plan:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self.config["prompts"]["writing_plan_quality_assessment"].format(
            content=json.dumps(writing_plan, ensure_ascii=False, indent=2)
        )
        
        result = self.api_client.generate_content_with_retry(
            "writing_plan_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="写作计划质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def assess_core_worldview_quality(self, worldview: Dict) -> Dict:
        """评估世界观质量"""
        if not worldview:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self.config["prompts"]["core_worldview_quality_assessment"].format(
            content=json.dumps(worldview, ensure_ascii=False, indent=2)
        )
        
        result = self.api_client.generate_content_with_retry(
            "core_worldview_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="世界观质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def assess_character_design_quality(self, character_design: Dict) -> Dict:
        """评估角色设计质量"""
        if not character_design:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self.config["prompts"]["character_design_quality_assessment"].format(
            content=json.dumps(character_design, ensure_ascii=False, indent=2)
        )
        
        result = self.api_client.generate_content_with_retry(
            "character_design_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="角色设计质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def optimize_market_analysis(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化市场分析"""
        priority_fixes = "\n".join([f"- {weakness}" for weakness in assessment.get("weaknesses", [])[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": json.dumps(assessment, ensure_ascii=False),
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self.config["prompts"]["market_analysis_optimization"].format(**optimization_params)
        result = self.api_client.generate_content_with_retry(
            "market_analysis_optimization", 
            user_prompt, 
            purpose="市场分析优化"
        )
        return result

    def optimize_writing_plan(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化写作计划"""
        priority_fixes = "\n".join([f"- {weakness}" for weakness in assessment.get("weaknesses", [])[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": json.dumps(assessment, ensure_ascii=False),
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self.config["prompts"]["writing_plan_optimization"].format(**optimization_params)
        result = self.api_client.generate_content_with_retry(
            "writing_plan_optimization", 
            user_prompt, 
            purpose="写作计划优化"
        )
        return result

    def optimize_core_worldview(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化世界观"""
        priority_fixes = "\n".join([f"- {weakness}" for weakness in assessment.get("weaknesses", [])[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": json.dumps(assessment, ensure_ascii=False),
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self.config["prompts"]["core_worldview_optimization"].format(**optimization_params)
        result = self.api_client.generate_content_with_retry(
            "core_worldview_optimization", 
            user_prompt, 
            purpose="世界观优化"
        )
        return result

    def optimize_character_design(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化角色设计"""
        priority_fixes = "\n".join([f"- {weakness}" for weakness in assessment.get("weaknesses", [])[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": json.dumps(assessment, ensure_ascii=False),
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self.config["prompts"]["character_design_optimization"].format(**optimization_params)
        result = self.api_client.generate_content_with_retry(
            "character_design_optimization", 
            user_prompt, 
            purpose="角色设计优化"
        )
        return result