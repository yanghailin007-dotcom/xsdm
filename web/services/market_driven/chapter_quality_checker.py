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

版本：2.0.0 (JSON配置化)
日期：2026-03-31
"""

import json
import logging
import os
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
    
    # 默认配置路径
    DEFAULT_CONFIG_DIR = os.path.join("prompt_packages", "default", "market_driven", "components")
    RULES_FILE = "quality_check_rules.json"
    OPTIMIZATION_FILE = "optimization_hints.json"
    
    def __init__(self, novel_data: Dict, optimizer_v3=None, config_dir: str = None):
        """
        初始化质检器
        
        Args:
            novel_data: 小说数据
            optimizer_v3: v3.0优化器实例（可选）
            config_dir: 配置文件目录（可选，默认使用DEFAULT_CONFIG_DIR）
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
        
        # 加载配置
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.rules_config = self._load_rules_config()
        self.optimization_config = self._load_optimization_config()
        
        logger.info(f"[QualityChecker] 初始化 | 书名: {novel_data.get('title', '未命名')} | 题材: {self.genre_type}")
    
    def _load_rules_config(self) -> Dict:
        """加载检查规则配置"""
        config_path = os.path.join(self.config_dir, self.RULES_FILE)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.debug(f"[QualityChecker] 成功加载规则配置: {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"[QualityChecker] 规则配置文件未找到: {config_path}，使用默认规则")
            return self._get_default_rules_config()
        except json.JSONDecodeError as e:
            logger.error(f"[QualityChecker] 规则配置文件解析错误: {e}，使用默认规则")
            return self._get_default_rules_config()
    
    def _load_optimization_config(self) -> Dict:
        """加载优化提示词配置"""
        config_path = os.path.join(self.config_dir, self.OPTIMIZATION_FILE)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.debug(f"[QualityChecker] 成功加载优化配置: {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"[QualityChecker] 优化配置文件未找到: {config_path}，使用默认优化")
            return self._get_default_optimization_config()
        except json.JSONDecodeError as e:
            logger.error(f"[QualityChecker] 优化配置文件解析错误: {e}，使用默认优化")
            return self._get_default_optimization_config()
    
    def _get_default_rules_config(self) -> Dict:
        """配置缺失时的警告提示"""
        logger.error("""
❌ 错误：质量检查规则配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/components/quality_check_rules.json

或使用API创建配置：
POST /api/v2/prompt-config/component/quality_check_rules

详细信息请查看文档：docs/prompt_configuration.md
""")
        return {
            "version": "1.0.0",
            "check_categories": [],
            "rules": {},
            "_warning": "配置缺失，请检查quality_check_rules.json"
        }
    
    def _get_default_optimization_config(self) -> Dict:
        """配置缺失时的警告提示"""
        logger.error("""
❌ 错误：优化提示词配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/components/optimization_hints.json

或使用API创建配置：
POST /api/v2/prompt-config/component/optimization_hints

详细信息请查看文档：docs/prompt_configuration.md
""")
        return {
            "sections": {},
            "_warning": "配置缺失，请检查optimization_hints.json"
        }
    
    def reload_config(self):
        """重新加载配置文件"""
        self.rules_config = self._load_rules_config()
        self.optimization_config = self._load_optimization_config()
        logger.info("[QualityChecker] 配置已重新加载")
    
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
        rules = self.rules_config.get("rules", {})
        
        # 1. 结构检查（黄金三章）
        if "structure" in rules:
            structure_issues = self._check_structure(chapter_num, prompt, blueprint, rules["structure"])
            issues.extend(structure_issues)
        
        # 2. 番茄算法检查
        if "tomato_algo" in rules:
            algo_issues = self._check_tomato_algorithm(chapter_num, prompt, rules["tomato_algo"])
            issues.extend(algo_issues)
        
        # 3. 题材专项检查
        if "genre" in rules:
            genre_issues = self._check_genre_specific(chapter_num, prompt, rules["genre"])
            issues.extend(genre_issues)
        
        # 4. 情绪曲线检查
        if "emotion" in rules:
            emotion_issues = self._check_emotion_curve(chapter_num, prompt, blueprint, rules["emotion"])
            issues.extend(emotion_issues)
        
        # 5. 微创新检查
        if "micro_innov" in rules:
            innov_issues = self._check_micro_innovation(chapter_num, prompt, rules["micro_innov"])
            issues.extend(innov_issues)
        
        # 6. 完整性检查
        if "completeness" in rules:
            completeness_issues = self._check_completeness(chapter_num, prompt, rules["completeness"])
            issues.extend(completeness_issues)
        
        # 计算分数
        categories = self.rules_config.get("check_categories", self.CHECK_CATEGORIES)
        total_checks = len(categories) * 3  # 每个类别约3个检查点
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
                        blueprint: Dict, config: Dict) -> List[QualityIssue]:
        """检查章节结构（黄金三章合规性）"""
        issues = []
        
        # 黄金三章特殊检查
        golden_config = config.get("golden_chapters", {})
        if golden_config.get("enabled", False) and chapter_num in golden_config.get("chapters", [1, 2, 3]):
            # 检查是否有结构分配
            word_count_check = None
            for check in config.get("checks", []):
                if check.get("id") == "word_count_allocation":
                    word_count_check = check
                    break
            
            if word_count_check:
                condition = word_count_check.get("condition", {})
                missing_patterns = condition.get("missing_patterns", [])
                if all(pattern not in prompt for pattern in missing_patterns):
                    message_template = word_count_check.get("message", "第{chapter_num}章缺少字数分配结构")
                    try:
                        message = message_template.format(chapter_num=chapter_num)
                    except KeyError:
                        message = message_template.replace("{chapter_num}", str(chapter_num))
                    issues.append(QualityIssue(
                        category="structure",
                        severity=CheckSeverity(word_count_check.get("severity", "warning")),
                        message=message,
                        suggestion=word_count_check.get("suggestion", "")
                    ))
            
            # 检查是否包含必要的节拍
            required_beats = self._get_required_beats_for_golden_chapter(chapter_num, config)
            for beat in required_beats:
                if beat not in prompt.lower():
                    beat_check = None
                    for check in config.get("checks", []):
                        if check.get("id") == "required_beats":
                            beat_check = check
                            break
                    if beat_check:
                        message_template = beat_check.get("message", "可能缺少必要节拍: {beat}")
                        suggestion_template = beat_check.get("suggestion", "在提示词中明确包含'{beat}'的要求")
                        try:
                            message = message_template.format(beat=beat)
                            suggestion = suggestion_template.format(beat=beat)
                        except KeyError:
                            message = message_template.replace("{beat}", beat)
                            suggestion = suggestion_template.replace("{beat}", beat)
                        issues.append(QualityIssue(
                            category="structure",
                            severity=CheckSeverity(beat_check.get("severity", "warning")),
                            message=message,
                            suggestion=suggestion
                        ))
        
        # 通用结构检查
        for check in config.get("checks", []):
            if check.get("id") == "section_markers":
                condition = check.get("condition", {})
                missing_patterns = condition.get("missing_patterns", [])
                if all(pattern not in prompt for pattern in missing_patterns):
                    issues.append(QualityIssue(
                        category="structure",
                        severity=CheckSeverity(check.get("severity", "warning")),
                        message=check.get("message", ""),
                        suggestion=check.get("suggestion", "")
                    ))
                break
        
        return issues
    
    def _get_required_beats_for_golden_chapter(self, chapter_num: int, config: Dict = None) -> List[str]:
        """获取黄金三章的必要节拍"""
        if config:
            golden_config = config.get("golden_chapters", {})
            required_beats = golden_config.get("required_beats", {})
            return required_beats.get(str(chapter_num), [])
        # 默认回退
        if chapter_num == 1:
            return ["困境", "系统", "钩子"]
        elif chapter_num == 2:
            return ["验证", "爽点", "冲突"]
        else:  # chapter_num == 3
            return ["打脸", "收获", "震惊"]
    
    def _check_tomato_algorithm(self, chapter_num: int, prompt: str, config: Dict) -> List[QualityIssue]:
        """检查番茄算法指标"""
        issues = []
        
        for check in config.get("checks", []):
            check_id = check.get("id", "")
            condition = check.get("condition", {})
            missing_patterns = condition.get("missing_patterns", [])
            missing_keywords = condition.get("missing_keywords", [])
            
            should_add = False
            
            # 检查pattern条件
            if missing_patterns and all(pattern not in prompt for pattern in missing_patterns):
                should_add = True
            
            # 检查keywords条件
            if missing_keywords and all(keyword not in prompt for keyword in missing_keywords):
                should_add = True
            
            if should_add:
                issues.append(QualityIssue(
                    category="tomato_algo",
                    severity=CheckSeverity(check.get("severity", "warning")),
                    message=check.get("message", ""),
                    suggestion=check.get("suggestion", "")
                ))
        
        return issues
    
    def _check_genre_specific(self, chapter_num: int, prompt: str, config: Dict) -> List[QualityIssue]:
        """检查题材专项要求"""
        issues = []
        
        genre_types = config.get("genre_types", {})
        genre_config = genre_types.get(self.genre_type)
        
        if genre_config:
            for check in genre_config.get("checks", []):
                condition = check.get("condition", {})
                missing_keywords = condition.get("missing_keywords", [])
                
                if missing_keywords and all(keyword not in prompt for keyword in missing_keywords):
                    issues.append(QualityIssue(
                        category="genre",
                        severity=CheckSeverity(check.get("severity", "warning")),
                        message=check.get("message", ""),
                        suggestion=check.get("suggestion", "")
                    ))
        
        return issues
    
    def _check_emotion_curve(self, chapter_num: int, prompt: str, 
                             blueprint: Dict, config: Dict) -> List[QualityIssue]:
        """检查情绪曲线设计"""
        issues = []
        
        for check in config.get("checks", []):
            condition = check.get("condition", {})
            missing_keywords = condition.get("missing_keywords", [])
            
            if missing_keywords and all(keyword not in prompt for keyword in missing_keywords):
                issues.append(QualityIssue(
                    category="emotion",
                    severity=CheckSeverity(check.get("severity", "warning")),
                    message=check.get("message", ""),
                    suggestion=check.get("suggestion", "")
                ))
        
        return issues
    
    def _check_micro_innovation(self, chapter_num: int, prompt: str, config: Dict) -> List[QualityIssue]:
        """检查微创新原则"""
        issues = []
        
        # 第1章特殊检查：避免老套路
        chapter_1_config = config.get("chapter_1_special", {})
        if chapter_1_config.get("enabled", False) and chapter_num == 1:
            for check in chapter_1_config.get("checks", []):
                condition = check.get("condition", {})
                missing_keywords = condition.get("missing_keywords", [])
                has_keywords = condition.get("has_keywords", [])
                has_keywords_negative = condition.get("has_keywords_negative", [])
                
                should_add = False
                
                # 简单关键词缺失检查
                if missing_keywords and all(keyword not in prompt for keyword in missing_keywords):
                    should_add = True
                
                # 包含某些关键词但缺少其他关键词
                if has_keywords and missing_keywords:
                    has_all_required = all(keyword in prompt for keyword in has_keywords)
                    missing_all = all(keyword not in prompt for keyword in missing_keywords)
                    if has_all_required and missing_all:
                        should_add = True
                
                # 检查负面关键词（如"金光"、"天降"）
                if has_keywords_negative:
                    has_negative = any(keyword in prompt for keyword in has_keywords_negative)
                    has_all_required = all(keyword in prompt for keyword in has_keywords) if has_keywords else True
                    if has_all_required and has_negative:
                        should_add = True
                
                if should_add:
                    issues.append(QualityIssue(
                        category="micro_innov",
                        severity=CheckSeverity(check.get("severity", "warning")),
                        message=check.get("message", ""),
                        suggestion=check.get("suggestion", "")
                    ))
        
        return issues
    
    def _check_completeness(self, chapter_num: int, prompt: str, config: Dict) -> List[QualityIssue]:
        """检查提示词完整性"""
        issues = []
        
        for check in config.get("checks", []):
            condition = check.get("condition", {})
            missing_keywords = condition.get("missing_keywords", [])
            
            if missing_keywords and all(keyword not in prompt for keyword in missing_keywords):
                issues.append(QualityIssue(
                    category="completeness",
                    severity=CheckSeverity(check.get("severity", "warning")),
                    message=check.get("message", ""),
                    suggestion=check.get("suggestion", "")
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
        sections = self.optimization_config.get("sections", {})
        
        # 按类别分组问题
        issues_by_category = {}
        for issue in issues:
            cat = issue.category
            if cat not in issues_by_category:
                issues_by_category[cat] = []
            issues_by_category[cat].append(issue)
        
        # 应用番茄算法优化
        if "tomato_algo" in issues_by_category and "tomato_algorithm" in sections:
            section_config = sections["tomato_algorithm"]
            marker = section_config.get("marker", "")
            if marker not in optimized:
                content = section_config.get("content", "")
                position = section_config.get("position", "append")
                if position == "prepend":
                    optimized = content + "\n\n" + optimized
                else:
                    optimized = optimized + content
        
        # 应用微创新优化
        if "micro_innov" in issues_by_category and "micro_innovation" in sections:
            section_config = sections["micro_innovation"]
            marker = section_config.get("marker", "")
            if marker not in optimized:
                content = section_config.get("content", "")
                position = section_config.get("position", "append")
                if position == "prepend":
                    optimized = content + "\n\n" + optimized
                else:
                    optimized = optimized + content
        
        # 应用结构优化（黄金三章）
        if "structure" in issues_by_category and "structure_golden" in sections:
            structure_issues = issues_by_category["structure"]
            section_config = sections["structure_golden"]
            marker = section_config.get("marker", "")
            if marker not in optimized and any("字数分配" in i.message for i in structure_issues):
                content = section_config.get("content", "")
                position = section_config.get("position", "append")
                if position == "prepend":
                    optimized = content + "\n\n" + optimized
                else:
                    optimized = optimized + content
        
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
    
    # 检查类别（保留兼容性）
    CHECK_CATEGORIES = [
        "structure",      # 结构检查
        "tomato_algo",    # 番茄算法
        "genre",          # 题材专项
        "emotion",        # 情绪曲线
        "micro_innov",    # 微创新
        "completeness",   # 完整性
    ]


# 便捷函数
def check_chapter_quality(novel_data: Dict, chapter_num: int, 
                         prompt: str, blueprint: Dict = None,
                         optimizer_v3=None, config_dir: str = None) -> QualityReport:
    """
    检查章节质量的便捷函数
    
    Args:
        novel_data: 小说数据
        chapter_num: 章节号
        prompt: 提示词
        blueprint: 章节规划
        optimizer_v3: v3.0优化器
        config_dir: 配置目录（可选）
        
    Returns:
        质检报告
    """
    checker = ChapterQualityChecker(novel_data, optimizer_v3, config_dir)
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
