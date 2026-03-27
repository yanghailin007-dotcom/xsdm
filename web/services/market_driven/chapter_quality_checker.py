"""
章节质量检查器 - AI驱动的生成前质检系统
========================================

在每章生成前，让AI自检并优化提示词，确保输出质量。

核心功能：
1. 提示词质量评估（完整性、可操作性）
2. 章节结构检查（黄金三章合规性）
3. 番茄算法指标验证
4. 题材专项检查
5. 自动修复建议

版本：1.0.0
日期：2026-03-26
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CheckSeverity(Enum):
    """检查严重程度"""
    INFO = "info"        # 建议性
    WARNING = "warning"  # 警告，建议修复
    ERROR = "error"      # 错误，必须修复
    CRITICAL = "critical"  # 严重，阻止生成


@dataclass
class QualityIssue:
    """质量问题"""
    category: str                    # 问题类别
    severity: CheckSeverity          # 严重程度
    message: str                     # 问题描述
    suggestion: str                  # 修复建议
    auto_fixable: bool = False       # 是否可自动修复
    fix_code: Optional[str] = None   # 自动修复代码（如果有）


@dataclass
class QualityReport:
    """质检报告"""
    chapter_num: int
    total_checks: int
    passed_checks: int
    issues: List[QualityIssue]
    score: float                     # 0-100分
    can_generate: bool               # 是否可以通过生成
    optimized_prompt: Optional[str]  # 优化后的提示词
    
    def get_critical_issues(self) -> List[QualityIssue]:
        """获取严重问题"""
        return [i for i in self.issues if i.severity == CheckSeverity.CRITICAL]
    
    def get_errors(self) -> List[QualityIssue]:
        """获取错误"""
        return [i for i in self.issues if i.severity == CheckSeverity.ERROR]
    
    def get_warnings(self) -> List[QualityIssue]:
        """获取警告"""
        return [i for i in self.issues if i.severity == CheckSeverity.WARNING]


class ChapterQualityChecker:
    """
    章节质量检查器
    
    在生成前对提示词进行全面检查，确保符合v3.0标准
    """
    
    # 检查类别
    CHECK_CATEGORIES = [
        "structure",      # 结构检查
        "tomato_algo",    # 番茄算法
        "genre",          # 题材专项
        "emotion",        # 情绪曲线
        "micro_innov",    # 微创新
        "completeness",   # 完整性
    ]
    
    def __init__(self, novel_data: Dict, optimizer_v3=None):
        """
        初始化质检器
        
        Args:
            novel_data: 小说数据
            optimizer_v3: v3.0优化器实例（可选）
        """
        # 确保 novel_data 是字典类型
        if isinstance(novel_data, list):
            logger.warning(f"[QualityChecker] novel_data 是列表类型，转换为字典")
            novel_data = novel_data[0] if novel_data else {}
        if not isinstance(novel_data, dict):
            logger.warning(f"[QualityChecker] novel_data 类型异常: {type(novel_data)}，使用空字典")
            novel_data = {}
        self.novel_data = novel_data
        self.optimizer = optimizer_v3
        
        # 确保plan是字典类型
        plan = novel_data.get('plan', {})
        if not isinstance(plan, dict):
            novel_data['plan'] = {}
        
        self.genre_type = self._detect_genre_type()
        
        logger.info(f"[QualityChecker] 初始化 | 书名: {novel_data.get('title', '未命名')} | 题材: {self.genre_type}")
    
    def _detect_genre_type(self) -> str:
        """检测题材类型"""
        genre = self.novel_data.get('genre', '')
        plan = self.novel_data.get('plan', {})
        
        if '国运' in genre or '直播' in genre:
            return '国运文'
        elif '神豪' in genre or '花钱' in genre or '返利' in genre:
            return '神豪文'
        elif '模拟' in genre or '模拟器' in genre:
            return '模拟器文'
        elif '修仙' in genre or '修真' in genre:
            return '修仙文'
        elif '奶爸' in genre:
            return '奶爸文'
        elif '签到' in genre:
            return '签到文'
        elif '末日' in genre or '求生' in genre:
            return '末日文'
        elif '同人' in genre:
            return '同人'
        
        # 从金手指类型判断
        golden_finger = plan.get('golden_finger', {}) if isinstance(plan, dict) else {}
        gf_type = golden_finger.get('type', '') if isinstance(golden_finger, dict) else ''
        
        if '国运' in gf_type:
            return '国运文'
        elif '神豪' in gf_type or '花钱' in gf_type:
            return '神豪文'
        elif '模拟' in gf_type:
            return '模拟器文'
        
        return '通用'
    
    def check_chapter(self, chapter_num: int, prompt: str, 
                     blueprint: Dict = None) -> QualityReport:
        """
        检查章节质量
        
        Args:
            chapter_num: 章节号
            prompt: 当前提示词
            blueprint: 章节规划
            
        Returns:
            质检报告
        """
        logger.info(f"[QualityChecker] 开始检查第{chapter_num}章")
        
        issues = []
        
        # 1. 结构检查（黄金三章）
        structure_issues = self._check_structure(chapter_num, prompt, blueprint)
        issues.extend(structure_issues)
        
        # 2. 番茄算法检查
        algo_issues = self._check_tomato_algorithm(chapter_num, prompt)
        issues.extend(algo_issues)
        
        # 3. 题材专项检查
        genre_issues = self._check_genre_specific(chapter_num, prompt)
        issues.extend(genre_issues)
        
        # 4. 情绪曲线检查
        emotion_issues = self._check_emotion_curve(chapter_num, prompt, blueprint)
        issues.extend(emotion_issues)
        
        # 5. 微创新检查
        innov_issues = self._check_micro_innovation(chapter_num, prompt)
        issues.extend(innov_issues)
        
        # 6. 完整性检查
        completeness_issues = self._check_completeness(chapter_num, prompt)
        issues.extend(completeness_issues)
        
        # 计算分数
        total_checks = len(self.CHECK_CATEGORIES) * 3  # 每个类别约3个检查点
        error_count = len([i for i in issues if i.severity == CheckSeverity.ERROR])
        critical_count = len([i for i in issues if i.severity == CheckSeverity.CRITICAL])
        warning_count = len([i for i in issues if i.severity == CheckSeverity.WARNING])
        
        # 分数计算：基础分100，错误-15，严重-30，警告-5
        score = max(0, 100 - error_count * 15 - critical_count * 30 - warning_count * 5)
        
        # 是否可以通过生成
        can_generate = critical_count == 0 and error_count <= 2
        
        # 生成优化后的提示词
        optimized_prompt = self._optimize_prompt(prompt, issues) if issues else prompt
        
        report = QualityReport(
            chapter_num=chapter_num,
            total_checks=total_checks,
            passed_checks=total_checks - len(issues),
            issues=issues,
            score=score,
            can_generate=can_generate,
            optimized_prompt=optimized_prompt
        )
        
        logger.info(f"[QualityChecker] 第{chapter_num}章检查完成 | 分数: {score} | 问题数: {len(issues)} | 可通过: {can_generate}")
        
        return report
    
    def _check_structure(self, chapter_num: int, prompt: str, 
                        blueprint: Dict) -> List[QualityIssue]:
        """检查章节结构（黄金三章合规性）"""
        issues = []
        
        # 黄金三章特殊检查
        if chapter_num <= 3:
            # 检查是否有结构分配
            if "0-500字" not in prompt and "500字" not in prompt:
                issues.append(QualityIssue(
                    category="structure",
                    severity=CheckSeverity.ERROR,
                    message=f"第{chapter_num}章缺少字数分配结构",
                    suggestion="添加'0-500字困境+500-2000字系统+2000-2500字钩子'的结构说明"
                ))
            
            # 检查是否包含必要的节拍
            required_beats = self._get_required_beats_for_golden_chapter(chapter_num)
            for beat in required_beats:
                if beat not in prompt.lower():
                    issues.append(QualityIssue(
                        category="structure",
                        severity=CheckSeverity.WARNING,
                        message=f"可能缺少必要节拍: {beat}",
                        suggestion=f"在提示词中明确包含'{beat}'的要求"
                    ))
        
        # 通用结构检查
        if "【" not in prompt or "】" not in prompt:
            issues.append(QualityIssue(
                category="structure",
                severity=CheckSeverity.WARNING,
                message="提示词缺少清晰的章节标记（【】）",
                suggestion="使用【】标记各部分，提高可读性"
            ))
        
        return issues
    
    def _get_required_beats_for_golden_chapter(self, chapter_num: int) -> List[str]:
        """获取黄金三章的必要节拍"""
        if chapter_num == 1:
            return ["困境", "系统", "钩子"]
        elif chapter_num == 2:
            return ["验证", "爽点", "冲突"]
        else:  # chapter_num == 3
            return [["打脸"], "收获", "震惊"]
    
    def _check_tomato_algorithm(self, chapter_num: int, prompt: str) -> List[QualityIssue]:
        """检查番茄算法指标"""
        issues = []
        
        # 检查前300字冲突要求
        if "前300字" not in prompt and "300字" not in prompt:
            issues.append(QualityIssue(
                category="tomato_algo",
                severity=CheckSeverity.ERROR,
                message="缺少'前300字必须出现冲突'的要求",
                suggestion="在提示词中明确添加：'前300字必须出现冲突或羞辱场景'"
            ))
        
        # 检查对话占比
        if "对话" not in prompt or ("40%" not in prompt and "50%" not in prompt):
            issues.append(QualityIssue(
                category="tomato_algo",
                severity=CheckSeverity.WARNING,
                message="未明确对话占比要求",
                suggestion="添加'对话占比≥50%'的要求"
            ))
        
        # 检查段落长度
        if "每段" not in prompt and "3行" not in prompt:
            issues.append(QualityIssue(
                category="tomato_algo",
                severity=CheckSeverity.WARNING,
                message="未明确段落长度限制",
                suggestion="添加'每段1-3行，多用换行'的要求"
            ))
        
        # 检查章尾钩子
        if "钩子" not in prompt:
            issues.append(QualityIssue(
                category="tomato_algo",
                severity=CheckSeverity.ERROR,
                message="提示词缺少钩子要求",
                suggestion="添加'章尾最后50字必须是钩子'的要求"
            ))
        
        return issues
    
    def _check_genre_specific(self, chapter_num: int, prompt: str) -> List[QualityIssue]:
        """检查题材专项要求"""
        issues = []
        
        if self.genre_type == "国运文":
            # 检查是否有弹幕要求
            if "弹幕" not in prompt:
                issues.append(QualityIssue(
                    category="genre",
                    severity=CheckSeverity.WARNING,
                    message="国运文缺少弹幕设计要求",
                    suggestion="添加'每章至少3-5条弹幕'的要求"
                ))
        
        elif self.genre_type == "神豪文":
            # 检查是否有精确数字要求
            if "精确" not in prompt and "小数" not in prompt:
                issues.append(QualityIssue(
                    category="genre",
                    severity=CheckSeverity.WARNING,
                    message="神豪文缺少数字精确度要求",
                    suggestion="添加'金额精确到小数点后2位'的要求"
                ))
        
        elif self.genre_type == "模拟器文":
            # 检查是否有模拟过程要求
            if "模拟" not in prompt or "剪辑" not in prompt:
                issues.append(QualityIssue(
                    category="genre",
                    severity=CheckSeverity.WARNING,
                    message="模拟器文缺少模拟过程写法要求",
                    suggestion="添加'快速剪辑感的模拟过程写法'要求"
                ))
        
        return issues
    
    def _check_emotion_curve(self, chapter_num: int, prompt: str, 
                             blueprint: Dict) -> List[QualityIssue]:
        """检查情绪曲线设计"""
        issues = []
        
        # 检查是否有情绪要求
        if "情绪" not in prompt:
            issues.append(QualityIssue(
                category="emotion",
                severity=CheckSeverity.WARNING,
                message="提示词缺少情绪设计要求",
                suggestion="添加'严格按照指定情绪类型写作'的要求"
            ))
        
        # 检查是否有情绪转变要求
        if "转变" not in prompt and "曲线" not in prompt:
            issues.append(QualityIssue(
                category="emotion",
                severity=CheckSeverity.INFO,
                message="未明确要求情绪转变次数",
                suggestion="添加'一章内至少3次情绪转变'的要求"
            ))
        
        return issues
    
    def _check_micro_innovation(self, chapter_num: int, prompt: str) -> List[QualityIssue]:
        """检查微创新原则"""
        issues = []
        
        # 第1章特殊检查：避免老套路
        if chapter_num == 1:
            # 检查是否有微创新要求
            if "微创新" not in prompt and "创新" not in prompt:
                issues.append(QualityIssue(
                    category="micro_innov",
                    severity=CheckSeverity.WARNING,
                    message="第1章缺少微创新要求",
                    suggestion="添加微创新要求：'避开深夜暴雨套路，尝试凌晨下班'等"
                ))
            
            # 检查反派塑造
            if "反派" in prompt and "智商" not in prompt and "目的" not in prompt:
                issues.append(QualityIssue(
                    category="micro_innov",
                    severity=CheckSeverity.INFO,
                    message="反派塑造可能过于脸谱化",
                    suggestion="添加'反派要有智商，不只是嚣张，要有自己的目的'"
                ))
            
            # 检查系统激活方式
            if "系统" in prompt and "激活" in prompt:
                if "金光" in prompt or "天降" in prompt:
                    issues.append(QualityIssue(
                        category="micro_innov",
                        severity=CheckSeverity.WARNING,
                        message="系统激活方式过于老套（天降金光）",
                        suggestion="尝试现代激活方式：手机APP、短信邀请、延迟确认等"
                    ))
            
            # 检查配角要求
            if "配角" not in prompt and "围观" not in prompt:
                issues.append(QualityIssue(
                    category="micro_innov",
                    severity=CheckSeverity.INFO,
                    message="未要求配角在线",
                    suggestion="添加'至少2-3个配角各有反应和立场'的要求"
                ))
        
        return issues
    
    def _check_completeness(self, chapter_num: int, prompt: str) -> List[QualityIssue]:
        """检查提示词完整性"""
        issues = []
        
        # 检查字数要求
        if "字数" not in prompt and "2000" not in prompt:
            issues.append(QualityIssue(
                category="completeness",
                severity=CheckSeverity.ERROR,
                message="缺少字数要求",
                suggestion="添加'2000-2500字'的字数要求"
            ))
        
        # 检查视角要求
        if "第三人称" not in prompt and "上帝视角" not in prompt:
            issues.append(QualityIssue(
                category="completeness",
                severity=CheckSeverity.WARNING,
                message="未明确视角要求",
                suggestion="添加'第三人称上帝视角'的要求"
            ))
        
        # 检查输出格式
        if "输出格式" not in prompt and "格式" not in prompt:
            issues.append(QualityIssue(
                category="completeness",
                severity=CheckSeverity.INFO,
                message="缺少输出格式说明",
                suggestion="添加明确的输出格式要求"
            ))
        
        return issues
    
    def _optimize_prompt(self, original_prompt: str, issues: List[QualityIssue]) -> str:
        """
        根据问题优化提示词
        
        Args:
            original_prompt: 原始提示词
            issues: 问题列表
            
        Returns:
            优化后的提示词
        """
        optimized = original_prompt
        
        # 修复番茄算法问题
        algo_errors = [i for i in issues if i.category == "tomato_algo" and i.severity in [CheckSeverity.ERROR, CheckSeverity.CRITICAL]]
        if algo_errors:
            # 在提示词开头添加番茄算法要求
            tomato_section = """\n\n## 【番茄算法强制指标】\n- 前300字必须出现冲突/羞辱\n- 对话占比≥50%\n- 每段1-3行，多用换行\n- 章尾最后50字必须是钩子\n"""
            if "## 【番茄算法" not in optimized:
                optimized = tomato_section + "\n\n" + optimized
        
        # 修复微创新问题
        innov_warnings = [i for i in issues if i.category == "micro_innov"]
        if innov_warnings and "【微创新原则" not in optimized:
            innov_section = """\n\n## 【微创新原则】\n1. 时间选择：避开"深夜23:47暴雨"，尝试"凌晨5:30刚下班"\n2. 系统激活：尝试"手机APP式"、"延迟确认式"\n3. 反派塑造：要有智商，不只是嚣张，要有自己的目的\n4. 配角在线：至少2-3个配角各有反应和立场\n"""
            optimized = optimized + innov_section
        
        # 修复结构问题（黄金三章）
        structure_errors = [i for i in issues if i.category == "structure"]
        if structure_errors and any("字数分配" in i.message for i in structure_errors):
            if "【结构要求" not in optimized:
                structure_section = """\n\n## 【结构要求】（严格按字数分配）\n### 第一部分（0-500字）：极端困境\n### 第二部分（500-2000字）：系统觉醒/金手指使用\n### 第三部分（2000-2500字）：悬念钩子\n"""
                optimized = optimized + structure_section
        
        return optimized
    
    def quick_check(self, chapter_num: int, prompt: str) -> Tuple[bool, float]:
        """
        快速检查，返回是否可以通过和分数
        
        Args:
            chapter_num: 章节号
            prompt: 提示词
            
        Returns:
            (是否可以通过, 分数)
        """
        report = self.check_chapter(chapter_num, prompt)
        return report.can_generate, report.score


# 便捷函数
def check_chapter_quality(novel_data: Dict, chapter_num: int, 
                         prompt: str, blueprint: Dict = None,
                         optimizer_v3=None) -> QualityReport:
    """
    检查章节质量的便捷函数
    
    Args:
        novel_data: 小说数据
        chapter_num: 章节号
        prompt: 提示词
        blueprint: 章节规划
        optimizer_v3: v3.0优化器
        
    Returns:
        质检报告
    """
    checker = ChapterQualityChecker(novel_data, optimizer_v3)
    return checker.check_chapter(chapter_num, prompt, blueprint)


def format_quality_report(report: QualityReport) -> str:
    """
    格式化质检报告为字符串
    
    Args:
        report: 质检报告
        
    Returns:
        格式化后的报告文本
    """
    lines = [
        f"=" * 60,
        f"📋 第{report.chapter_num}章质量检查报告",
        f"=" * 60,
        f"总分: {report.score}/100 | 检查项: {report.passed_checks}/{report.total_checks}",
        f"状态: {'✅ 可通过' if report.can_generate else '❌ 需修复'}",
        f"-" * 60,
    ]
    
    if report.issues:
        lines.append("问题列表:")
        for issue in report.issues:
            severity_icon = {
                CheckSeverity.CRITICAL: "🔴",
                CheckSeverity.ERROR: "🟠",
                CheckSeverity.WARNING: "🟡",
                CheckSeverity.INFO: "🔵"
            }.get(issue.severity, "⚪")
            
            lines.append(f"  {severity_icon} [{issue.category}] {issue.message}")
            lines.append(f"     建议: {issue.suggestion}")
    else:
        lines.append("✅ 未发现明显问题")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)
