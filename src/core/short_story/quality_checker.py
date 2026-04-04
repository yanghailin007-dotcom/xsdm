"""
短篇完读率质检器
检查章末悬念、情绪连贯性、字数达标等关键指标
"""

import json
import logging
from typing import Dict, List

from .prompt_builder import ShortStoryPromptBuilder

logger = logging.getLogger(__name__)


class ShortStoryQualityChecker:
    """短篇完读率质检器"""
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self.prompt_builder = ShortStoryPromptBuilder()
    
    def check_chapter(self, chapter_data: Dict, blueprint: Dict) -> Dict:
        """
        检查单章质量
        返回质检报告
        """
        issues = []
        score = 100.0
        
        content = chapter_data.get("content", "")
        title = chapter_data.get("title", "")
        word_count = len(content)
        
        # 1. 字数检查
        if word_count < 1500:
            issues.append(f"字数不足：{word_count} 字（要求 ≥1500）")
            score -= 20
        elif word_count > 3500:
            issues.append(f"字数过长：{word_count} 字（要求 ≤3500）")
            score -= 10
        
        # 2. 章末悬念检查
        ending_check = self._check_ending_hook(content)
        if not ending_check["has_hook"]:
            issues.append(f"章末悬念不足：{ending_check['reason']}")
            score -= 25
        
        # 3. 对话占比检查
        dialog_ratio = self._calculate_dialog_ratio(content)
        if dialog_ratio < 0.25:
            issues.append(f"对话占比过低：{dialog_ratio:.1%}（建议 >40%）")
            score -= 10
        
        # 4. 段落长度检查
        long_paragraphs = self._check_paragraph_length(content)
        if long_paragraphs > 3:
            issues.append(f"长段落过多：{long_paragraphs} 段超过 3 句话")
            score -= 5
        
        # 5. 禁止词汇检查（总结性/过渡性词汇）
        forbidden_check = self._check_forbidden_phrases(content)
        if forbidden_check:
            issues.append(f"发现总结性表述：{', '.join(forbidden_check[:3])}")
            score -= 5
        
        # 6. 与蓝图的钩子对齐检查
        cliffhanger = blueprint.get("cliffhanger", "")
        if cliffhanger and not self._verify_cliffhanger(content, cliffhanger):
            issues.append("章末内容与规划的悬念钩偏离较大")
            score -= 10
        
        score = max(0, score)
        passed = score >= 70 and word_count >= 1500
        
        report = {
            "chapter_number": chapter_data.get("chapter_number"),
            "title": title,
            "word_count": word_count,
            "dialog_ratio": round(dialog_ratio, 2),
            "score": round(score, 1),
            "passed": passed,
            "issues": issues,
            "ending_analysis": ending_check,
            "suggestions": self._generate_suggestions(issues)
        }
        
        logger.info(f"[QualityChecker] 第 {chapter_data.get('chapter_number')} 章质检："
                   f"分数={score:.1f} 字数={word_count} 通过={passed}")
        
        return report
    
    def _check_ending_hook(self, content: str) -> Dict:
        """检查章末是否有悬念钩"""
        if not content:
            return {"has_hook": False, "reason": "内容为空"}
        
        # 取最后 120 字
        ending = content[-120:] if len(content) > 120 else content
        
        # 悬念标记
        hook_markers = ["？", "?", "！", "!", "……", "...", "—", "——", 
                       "突然", "竟然", "难道", "谁知", "不料", "原来",
                       "门开了", "电话响了", "手机响了", "响起", "传来",
                       "出现", "走来", "冲进来", "拦住", "叫住"]
        
        # 总结性标记（负面）
        closing_markers = ["就这样", "结束了", "过去了", "陷入了沉思",
                          "想着", "回忆着", "睡着了", "离开了", "走了",
                          "一切都", "终于", "从此以后", "第二天"]
        
        has_hook_marker = any(m in ending for m in hook_markers)
        has_closing_marker = any(m in ending for m in closing_markers)
        
        if has_hook_marker and not has_closing_marker:
            return {"has_hook": True, "reason": "", "ending_snippet": ending}
        
        if has_closing_marker:
            return {"has_hook": False, 
                   "reason": "章末使用了总结性或过渡性表述，未停留在未完成的动作上",
                   "ending_snippet": ending}
        
        # 如果没有明显标记，检查最后一句是否以句号结尾（平淡结尾）
        last_sentence = ending.split("\n")[-1].strip()
        if last_sentence.endswith("。") and len(last_sentence) > 15:
            return {"has_hook": False,
                   "reason": "章末以陈述句平淡收尾，缺乏悬念张力",
                   "ending_snippet": ending}
        
        return {"has_hook": True, "reason": "", "ending_snippet": ending}
    
    def _calculate_dialog_ratio(self, content: str) -> float:
        """计算对话占比"""
        if not content:
            return 0.0
        
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        dialog_lines = 0
        for line in lines:
            if '"' in line or '"' in line or '"' in line or '"' in line or '：' in line or ':' in line:
                dialog_lines += 1
        
        return dialog_lines / len(lines) if lines else 0.0
    
    def _check_paragraph_length(self, content: str) -> int:
        """检查长段落数量（超过 3 句话的段落）"""
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        long_count = 0
        for p in paragraphs:
            sentences = [s.strip() for s in re.split(r'[。！？\n]', p) if s.strip()]
            if len(sentences) > 3:
                long_count += 1
        return long_count
    
    def _check_forbidden_phrases(self, content: str) -> List[str]:
        """检查禁止的总结性表述"""
        forbidden = [
            "这一天就这样过去了", "陷入了沉思", "回忆起了过去",
            "不知不觉中", "时间飞逝", "转眼间", "一切都结束了",
            "从此以后", "就这样", "终于平静下来", "一切都恢复了正常"
        ]
        found = []
        for phrase in forbidden:
            if phrase in content:
                found.append(phrase)
        return found
    
    def _verify_cliffhanger(self, content: str, planned_cliffhanger: str) -> bool:
        """验证章末是否与规划的悬念钩对齐"""
        ending = content[-150:] if len(content) > 150 else content
        # 提取规划悬念钩中的关键词
        keywords = [w for w in planned_cliffhanger.split() if len(w) >= 2]
        if not keywords:
            return True
        match_count = sum(1 for k in keywords if k in ending)
        return match_count >= 1 or len(keywords) == 0
    
    def _generate_suggestions(self, issues: List[str]) -> List[str]:
        """生成修改建议"""
        suggestions = []
        for issue in issues:
            if "字数不足" in issue:
                suggestions.append("补充细节描写、对话或内心活动，扩充到 1500 字以上")
            elif "字数过长" in issue:
                suggestions.append("删除冗余的环境描写和重复对话，压缩到 2500 字以内")
            elif "悬念" in issue:
                suggestions.append("章末改为\"未完成的动作\"：某人出现、话未说完、突发变故")
            elif "对话占比" in issue:
                suggestions.append("增加人物对话，用对话推动情节，减少旁白")
            elif "长段落" in issue:
                suggestions.append("将长段落拆分为 1-2 句话的短段落")
            elif "总结性" in issue:
                suggestions.append("删除总结性表述，让情节直接推进到下一章")
        return suggestions
    
    def deep_check(self, chapter_data: Dict, blueprint: Dict) -> Dict:
        """
        深度质检（调用 API）
        用于规则质检不通过时，获取更详细的分析和修改建议
        """
        if not self.api_client:
            return self.check_chapter(chapter_data, blueprint)
        
        prompt = f"""请对以下番茄短篇小说章节进行深度质检分析。\n\n章节标题：{chapter_data.get('title', '')}\n\n章节正文：\n{chapter_data.get('content', '')}\n\n规划要求：\n- 危机钩：{blueprint.get('crisis_hook', '')}\n- 爽点钩：{blueprint.get('payoff_hook', '')}\n- 悬念钩：{blueprint.get('cliffhanger', '')}\n\n请按 JSON 格式返回：\n{{\n  \"score\": \"0-100\",\n  \"passed\": true/false,\n  \"issues\": [\"问题1\", \"问题2\"],\n  \"suggestions\": [\"建议1\", \"建议2\"],\n  \"rewritten_ending\": \"如果章末悬念不足，请重写最后 100 字\"\n}}\n\n只输出 JSON。"""
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="general_writing",
                user_prompt=prompt,
                purpose="短篇深度质检"
            )
            result = json.loads(response)
            result["chapter_number"] = chapter_data.get("chapter_number")
            result["word_count"] = len(chapter_data.get("content", ""))
            return result
        except Exception as e:
            logger.error(f"[QualityChecker] 深度质检失败: {e}")
            return self.check_chapter(chapter_data, blueprint)
