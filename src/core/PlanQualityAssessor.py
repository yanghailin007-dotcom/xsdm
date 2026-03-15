"""写作计划质量评估器

通过分层摘要和增量评估的方式，高效评估大型写作计划的质量，
避免一次性处理大量token。

核心策略：
1. 结构化摘要提取 - 压缩关键信息到5k tokens以内
2. 分层评估 - 先整体后局部
3. 增量验证 - 只对有问题区域深入分析
4. 可视化报告 - 生成人类可读的质量报告
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from src.utils.logger import get_logger


class IssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "critical"  # 必须修复，否则影响生成
    HIGH = "high"         # 强烈建议修复
    MEDIUM = "medium"     # 建议修复
    LOW = "low"           # 可选优化
    INFO = "info"         # 仅信息提示


@dataclass
class QualityIssue:
    """质量问题记录"""
    category: str           # 类别：character/plot/pacing/logic/commercial
    severity: IssueSeverity
    location: str           # 位置：如 "major_event[1].medium_event[2]"
    description: str        # 问题描述
    suggestion: str         # 修改建议
    auto_fixable: bool = False  # 是否可自动修复


@dataclass
class AssessmentResult:
    """评估结果"""
    overall_score: float    # 总体评分 0-100
    readiness: str          # 准备度：ready/needs_review/needs_revision
    issues: List[QualityIssue] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    summary: str = ""
    token_saved: int = 0    # 节省的token数量


class PlanQualityAssessor:
    """写作计划质量评估器"""

    # 评估提示词模板
    SUMMARY_EVAL_PROMPT = """你是一位资深网文编辑，擅长评估小说写作计划的质量。

请对以下写作计划摘要进行评估，重点关注：
1. 商业吸引力 - 是否有清晰的爽点和卖点
2. 结构完整性 - 三幕式结构是否完整
3. 角色一致性 - 角色动机和行为是否自洽
4. 节奏合理性 - 章节分配是否合理
5. 逻辑连贯性 - 剧情发展是否有逻辑漏洞

评分标准（0-100分）：
- 90-100分：优秀，可直接使用
- 70-89分：良好，有小问题但不影响使用
- 50-69分：一般，需要修改
- 0-49分：较差，需要大幅修改

写作计划摘要：
{plan_summary}

请以JSON格式返回评估结果（确保使用UTF-8编码）：
{{
    "overall_score": 85,
    "readiness": "ready",
    "strengths": ["卖点清晰", "节奏紧凑"],
    "issues": [
        {{
            "category": "character",
            "severity": "medium",
            "location": "major_event[2].medium_event[1]",
            "description": "角色动机不够充分",
            "suggestion": "增加心理描写，铺垫其对宗门的不满"
        }}
    ],
    "summary": "整体质量良好，建议..."
}}
"""

    DEEP_ANALYSIS_PROMPT = """对以下写作计划部分进行深入分析：

{detail_content}

关注点：{focus_areas}

返回JSON格式的分析结果。
"""

    def __init__(self, api_key: str = None, api_client=None):
        """初始化评估器

        Args:
            api_key: Anthropic API密钥（可选，向后兼容）
            api_client: APIClient实例（推荐使用，统一使用系统配置的API）
        """
        self.logger = get_logger("PlanQualityAssessor")
        
        # 优先使用 api_client（统一API调用）
        self.api_client = api_client
        
        # 向后兼容：如果提供了 api_key 且没有 api_client，使用 Anthropic
        if api_client:
            self.use_ai = True
            self.client = None
            self.logger.info("✅ 使用APIClient进行AI质量评估")
        elif ANTHROPIC_AVAILABLE and api_key:
            self.client = Anthropic(api_key=api_key)
            self.use_ai = True
            self.api_client = None
            self.logger.info("✅ 使用Anthropic进行AI质量评估")
        else:
            self.client = None
            self.api_client = None
            self.use_ai = False
            self.logger.warning("⚠️ AI评估未启用，将使用规则式评估")

    def assess(self, plan_path: Path, use_deep_analysis: bool = False, skip_compression: bool = True, report_save_path: Path = None) -> AssessmentResult:
        """评估写作计划（从文件路径加载）

        Args:
            plan_path: 写作计划JSON文件路径
            use_deep_analysis: 是否进行深度分析（消耗更多token）
            skip_compression: 是否跳过压缩，直接传递完整计划（默认True）
            report_save_path: 报告保存路径（可选，默认保存到plan_path同级目录）

        Returns:
            评估结果
        """
        self.logger.info(f"开始评估写作计划: {plan_path}")

        # 加载计划
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan = json.load(f)

        # 调用数据评估方法
        return self.assess_data(
            plan, 
            use_deep_analysis=use_deep_analysis, 
            skip_compression=skip_compression,
            report_save_path=report_save_path,
            source_path=plan_path
        )

    def assess_data(self, plan: Dict, use_deep_analysis: bool = False, skip_compression: bool = True, report_save_path: Path = None, source_path: Path = None) -> AssessmentResult:
        """评估写作计划（直接传入数据对象，不创建临时文件）

        Args:
            plan: 写作计划数据字典
            use_deep_analysis: 是否进行深度分析（消耗更多token）
            skip_compression: 是否跳过压缩，直接传递完整计划（默认True）
            report_save_path: 报告保存路径（可选）
            source_path: 源文件路径（仅用于报告中的引用，不影响评估逻辑）

        Returns:
            评估结果
        """
        self.logger.info(f"开始评估写作计划数据 (skip_compression={skip_compression})")

        # 计算原始大小
        original_tokens = self._estimate_tokens(json.dumps(plan, ensure_ascii=False))

        # 🔥 新增：支持跳过压缩
        if skip_compression:
            self.logger.info(f"跳过压缩，使用完整计划进行评估 (Token数: {original_tokens})")
            if self.use_ai:
                result = self._ai_assess(plan, plan, use_deep_analysis)
            else:
                result = self._rule_based_assess(plan, plan)
            result.token_saved = 0
            # 保存评估报告（如果指定了保存路径）
            if report_save_path:
                self._save_report_data(result, report_save_path, source_path=source_path)
            return result

        # 提取摘要
        summary = self._extract_summary(plan)
        summary_tokens = self._estimate_tokens(json.dumps(summary, ensure_ascii=False))

        self.logger.info(f"摘要压缩率: {summary_tokens}/{original_tokens} = {summary_tokens/original_tokens:.1%}")

        if self.use_ai:
            result = self._ai_assess(summary, plan, use_deep_analysis)
            result.token_saved = original_tokens - summary_tokens
        else:
            result = self._rule_based_assess(summary, plan)
            result.token_saved = original_tokens - summary_tokens

        # 保存评估报告（如果指定了保存路径）
        if report_save_path:
            self._save_report_data(result, report_save_path, source_path=source_path)

        return result

    def _extract_summary(self, plan: Dict) -> Dict:
        """提取写作计划摘要

        压缩策略：
        - 保留元数据
        - medium_event只保留标题、章节范围、情感标签
        - 删除详细的outline内容

        支持的结构：
        1. 直接包含 major_events 的结构
        2. stage_writing_plan 嵌套结构
        3. 多阶段合并结构（包含 stages 数组）
        """
        # 🔥 处理多阶段合并结构
        if "stages" in plan:
            return self._extract_summary_from_merged_plan(plan)
        
        # 处理嵌套结构
        if "stage_writing_plan" in plan:
            inner_plan = plan["stage_writing_plan"]
            # 从 chapter_range 提取章节数量
            chapter_range = inner_plan.get("chapter_range", "1-1")
            total_chapters = self._parse_chapter_count(chapter_range)
            event_system = inner_plan.get("event_system", {})
            major_events = event_system.get("major_events", [])
            goal_hierarchy = inner_plan.get("goal_hierarchy_assessment", {})
            continuity_score = inner_plan.get("continuity_assessment", {}).get("overall_score", 0)
            novel_title = inner_plan.get("novel_metadata", {}).get("novel_title", "")
            stage = inner_plan.get("stage_name", "unknown")
        else:
            # 直接结构
            chapter_range = plan.get("chapter_range", "1-1")
            total_chapters = self._parse_chapter_count(chapter_range)
            major_events = plan.get("major_events", [])
            goal_hierarchy = plan.get("goal_hierarchy", {})
            continuity_score = plan.get("continuity_assessment", {}).get("overall_score", 0)
            novel_title = plan.get("novel_title", "")
            stage = plan.get("stage", "unknown")

        summary = {
            "meta": {
                "novel_title": novel_title,
                "stage": stage,
                "chapter_range": chapter_range,
                "total_chapters": total_chapters,
                "creation_date": plan.get("creation_date", ""),
            },
            "major_events": []
        }

        for me in major_events:
            me_summary = {
                "id": me.get("id", ""),
                "name": me.get("name", ""),
                "chapter_range": me.get("chapter_range", ""),
                "core_conflict": me.get("core_conflict", ""),
                "emotional_arc": me.get("emotional_arc_summary", ""),
                "expectation_tags": me.get("expectation_tags", []),
                "medium_events": []
            }

            for idx, med in enumerate(me.get("medium_events", [])):
                # 只保留关键信息
                med_summary = {
                    "index": idx,
                    "name": med.get("name", ""),
                    "chapter_range": med.get("chapter_range", ""),
                    "role": med.get("role", ""),  # 起/承/转/结
                    "emotional_tone": med.get("emotional_tone", ""),
                    "key_twists": med.get("key_twists", []),
                    # 注意：不包含详细的 outline 内容
                }
                me_summary["medium_events"].append(med_summary)

            summary["major_events"].append(me_summary)

        # 提取目标层级（如果有）
        if goal_hierarchy:
            if isinstance(goal_hierarchy, dict):
                main_goal = goal_hierarchy.get("main_goal", "")
                sub_goals = goal_hierarchy.get("sub_goals", [])[:3]  # 只取前3个
            else:
                main_goal = str(goal_hierarchy)
                sub_goals = []

            summary["goal_hierarchy"] = {
                "main_goal": main_goal,
                "sub_goals": sub_goals
            }

        # 提取连贯性评估（如果有）
        if continuity_score:
            summary["continuity_score"] = continuity_score

        return summary

    def _extract_summary_from_merged_plan(self, plan: Dict) -> Dict:
        """从合并后的多阶段计划中提取摘要"""
        stages = plan.get("stages", [])
        novel_title = plan.get("novel_title", "")
        
        # 合并所有阶段的重大事件
        all_major_events = []
        total_chapters = 0
        
        for stage in stages:
            stage_name = stage.get("stage_name", "unknown")
            chapter_range = stage.get("chapter_range", "")
            
            # 统计章节数
            if chapter_range:
                try:
                    parts = chapter_range.replace("章", "").split("-")
                    if len(parts) == 2:
                        stage_chapters = int(parts[1]) - int(parts[0]) + 1
                        total_chapters += stage_chapters
                except:
                    pass
            
            # 处理重大事件
            for me in stage.get("major_events", []):
                me_summary = {
                    "id": f"{stage_name}_{me.get('name', '')}",
                    "name": f"[{stage_name}] {me.get('name', '')}",
                    "chapter_range": me.get("chapter_range", ""),
                    "core_conflict": me.get("core_conflict", ""),
                    "emotional_arc": "",
                    "expectation_tags": [],
                    "medium_events": []
                }
                
                # 处理中级事件
                for idx, med in enumerate(me.get("medium_events", [])):
                    med_summary = {
                        "index": idx,
                        "name": med.get("name", ""),
                        "chapter_range": med.get("chapter_range", ""),
                        "role": med.get("role", ""),
                        "emotional_tone": "",
                        "key_twists": []
                    }
                    me_summary["medium_events"].append(med_summary)
                
                all_major_events.append(me_summary)
        
        summary = {
            "meta": {
                "novel_title": novel_title,
                "stage": f"全阶段({len(stages)}个)",
                "chapter_range": f"1-{total_chapters}",
                "total_chapters": total_chapters,
                "creation_date": "",
                "total_stages": len(stages)
            },
            "major_events": all_major_events
        }
        
        return summary

    def _parse_chapter_count(self, chapter_range: str) -> int:
        """从章节范围字符串解析章节数量

        Args:
            chapter_range: 如 "1-20", "1-5章", "第1-20章"

        Returns:
            章节总数
        """
        import re
        # 提取所有数字
        numbers = re.findall(r'\d+', str(chapter_range))
        if len(numbers) >= 2:
            return int(numbers[1])
        elif len(numbers) == 1:
            return int(numbers[0])
        return 0

    # 🔥 系统提示词 - 用于APIClient调用
    SYSTEM_PROMPT = """你是一位资深网文编辑，擅长评估小说写作计划的质量。

请对提供的写作计划进行专业评估，重点关注：
1. 商业吸引力 - 是否有清晰的爽点和卖点
2. 结构完整性 - 三幕式结构是否完整
3. 角色一致性 - 角色动机和行为是否自洽
4. 节奏合理性 - 章节分配是否合理
5. 逻辑连贯性 - 剧情发展是否有逻辑漏洞

你必须以JSON格式返回评估结果。"""

    def _ai_assess(self, summary: Dict, full_plan: Dict, use_deep_analysis: bool) -> AssessmentResult:
        """使用AI进行评估"""
        import json

        summary_str = json.dumps(summary, ensure_ascii=False, indent=2)
        user_prompt = self.SUMMARY_EVAL_PROMPT.format(plan_summary=summary_str)

        try:
            # 优先使用APIClient（统一API调用）
            if self.api_client:
                # 使用 generate_content_with_retry 获取完整日志和JSON解析
                ai_result = self.api_client.generate_content_with_retry(
                    content_type="writing_plan_quality_assessment",
                    user_prompt=user_prompt,
                    purpose="写作计划质量评估"
                )
                
                if not ai_result:
                    self.logger.error("❌ API调用返回空结果")
                    return self._rule_based_assess(summary, full_plan)
                
                # generate_content_with_retry 已经返回解析后的JSON对象
                if isinstance(ai_result, dict):
                    self.logger.info(f"✅ AI评估完成，返回字段: {list(ai_result.keys())}")
                    # 🔥 调试：记录AI返回的分数
                    score = ai_result.get("overall_score", "N/A")
                    readiness = ai_result.get("readiness", "N/A")
                    issue_count = len(ai_result.get("issues", []))
                    self.logger.info(f"📊 AI评分: {score}/100, 状态: {readiness}, 问题数: {issue_count}")
                else:
                    self.logger.warning(f"⚠️ AI返回不是字典类型: {type(ai_result)}")
                    return self._rule_based_assess(summary, full_plan)
            else:
                # 向后兼容：使用Anthropic
                self.logger.info("🤖 使用Anthropic进行AI评估...")
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=[{
                        "role": "user",
                        "content": user_prompt
                    }]
                )
                response_text = message.content[0].text
                
                # 提取JSON部分
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.rfind("```")
                    response_text = response_text[json_start:json_end].strip()
                
                ai_result = json.loads(response_text)

            # 解析结果
            result = AssessmentResult(
                overall_score=ai_result.get("overall_score", 70),
                readiness=ai_result.get("readiness", "needs_review"),
                strengths=ai_result.get("strengths", []),
                summary=ai_result.get("summary", ""),
            )

            # 转换issues
            for issue in ai_result.get("issues", []):
                result.issues.append(QualityIssue(
                    category=issue.get("category", "general"),
                    severity=IssueSeverity(issue.get("severity", "medium")),
                    location=issue.get("location", "unknown"),
                    description=issue.get("description", ""),
                    suggestion=issue.get("suggestion", ""),
                    auto_fixable=False
                ))

            # 如果需要深度分析且有问题
            if use_deep_analysis and result.issues:
                self.logger.info("执行深度分析...")
                deep_issues = self._deep_analyze_issues(full_plan, result.issues)
                result.issues.extend(deep_issues)

        except Exception as e:
            self.logger.error(f"AI评估失败: {e}")
            # 降级到规则式评估
            self.logger.info("降级到规则式评估...")
            result = self._rule_based_assess(summary, full_plan)

        return result

    def _deep_analyze_issues(self, full_plan: Dict, issues: List[QualityIssue]) -> List[QualityIssue]:
        """对特定问题进行深度分析"""
        deep_issues = []

        # 按location分组，减少API调用
        locations = set(issue.location for issue in issues if issue.severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL])

        for location in locations:
            detail_content = self._extract_location_content(full_plan, location)
            focus_areas = [issue.category for issue in issues if issue.location == location]

            # 调用深度分析
            # 这里可以进一步优化，只提取必要的内容
            pass

        return deep_issues

    def _extract_location_content(self, plan: Dict, location: str) -> Dict:
        """提取指定位置的内容"""
        # 解析location如 "major_event[1].medium_event[2]"
        import re

        pattern = r'major_event\[(\d+)\](?:\.medium_event\[(\d+)\])?'
        match = re.search(pattern, location)

        if not match:
            return {}

        major_idx = int(match.group(1))
        medium_idx = int(match.group(2)) if match.group(2) else None

        if major_idx >= len(plan.get("major_events", [])):
            return {}

        major_event = plan["major_events"][major_idx]

        if medium_idx is not None:
            if medium_idx >= len(major_event.get("medium_events", [])):
                return {}
            return major_event["medium_events"][medium_idx]

        return major_event

    def _rule_based_assess(self, summary: Dict, full_plan: Dict) -> AssessmentResult:
        """基于规则的评估（无AI时使用）"""
        issues = []
        strengths = []

        # 检查1：章节数量
        total_chapters = summary["meta"].get("total_chapters", 0)
        if total_chapters < 10:
            issues.append(QualityIssue(
                category="pacing", severity=IssueSeverity.HIGH,
                location="meta", description="章节数量过少",
                suggestion="建议至少20章的开局阶段"
            ))
        else:
            strengths.append("章节数量适中")

        # 检查2：大型事件数量
        major_count = len(summary.get("major_events", []))
        if major_count < 2:
            issues.append(QualityIssue(
                category="structure", severity=IssueSeverity.MEDIUM,
                location="major_events", description="大型事件数量不足",
                suggestion="建议至少2-3个大型事件构建三幕结构"
            ))
        else:
            strengths.append(f"包含{major_count}个大型事件，结构完整")

        # 检查3：情感标签
        has_tags = any(
            me.get("expectation_tags")
            for me in summary.get("major_events", [])
        )
        if has_tags:
            strengths.append("情感标签完整")
        else:
            issues.append(QualityIssue(
                category="commercial", severity=IssueSeverity.LOW,
                location="major_events", description="缺少情感标签",
                suggestion="添加expectation_tags有助于控制生成方向"
            ))

        # 检查4：章节覆盖连续性
        chapters_covered = set()
        for me in summary.get("major_events", []):
            for med in me.get("medium_events", []):
                range_str = med.get("chapter_range", "")
                if range_str:
                    # 解析 "1-3" 格式
                    parts = range_str.replace("第", "").replace("章", "").split("-")
                    if parts:
                        start = int(parts[0])
                        end = int(parts[1]) if len(parts) > 1 else start
                        chapters_covered.update(range(start, end + 1))

        if chapters_covered:
            expected = set(range(1, total_chapters + 1))
            missing = expected - chapters_covered
            if missing:
                issues.append(QualityIssue(
                    category="pacing", severity=IssueSeverity.HIGH,
                    location="chapter_coverage",
                    description=f"章节未覆盖: {sorted(missing)}",
                    suggestion="补充缺失章节的内容规划"
                ))

        # 计算分数
        score = 100 - len(issues) * 10
        score = max(0, min(100, score))

        # 确定准备度
        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)

        if critical_count > 0:
            readiness = "needs_revision"
        elif high_count > 2:
            readiness = "needs_review"
        else:
            readiness = "ready"

        return AssessmentResult(
            overall_score=score,
            readiness=readiness,
            issues=issues,
            strengths=strengths,
            summary=f"基于规则的评估：发现{len(issues)}个问题，{len(strengths)}个优点"
        )

    def _estimate_tokens(self, text: str) -> int:
        """估算token数量（粗略：中文约1.5字符/token）"""
        return len(text) // 2

    def _save_report(self, plan_path: Path, result: AssessmentResult, report_save_path: Path = None):
        """保存评估报告（从文件路径）
        
        Args:
            plan_path: 写作计划文件路径
            result: 评估结果
            report_save_path: 报告保存路径（可选，默认保存到plan_path同级目录）
        """
        # 🔥 修复：使用自定义保存路径，或默认保存到plan_path同级目录
        if report_save_path:
            report_path = report_save_path
        else:
            report_path = plan_path.parent / f"{plan_path.stem}_quality_report.json"

        self._save_report_data(result, report_path, source_path=plan_path)

    def _save_report_data(self, result: AssessmentResult, report_path: Path, source_path: Path = None):
        """保存评估报告（直接保存，不依赖源文件）
        
        Args:
            result: 评估结果
            report_path: 报告保存路径
            source_path: 源文件路径（仅用于记录，可选）
        """
        report = {
            "plan_file": str(source_path) if source_path else None,
            "assessment_time": datetime.now().isoformat(),
            "overall_score": result.overall_score,
            "readiness": result.readiness,
            "token_saved": result.token_saved,
            "strengths": result.strengths,
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity.value,
                    "location": i.location,
                    "description": i.description,
                    "suggestion": i.suggestion,
                    "auto_fixable": i.auto_fixable
                }
                for i in result.issues
            ],
            "summary": result.summary
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self.logger.info(f"评估报告已保存: {report_path}")

        # 同时生成可读文本报告
        text_report = self._generate_text_report(result)
        text_report_path = report_path.with_suffix(".txt")
        with open(text_report_path, 'w', encoding='utf-8') as f:
            f.write(text_report)

        self.logger.info(f"文本报告已保存: {text_report_path}")

    def _generate_text_report(self, result: AssessmentResult) -> str:
        """生成人类可读的文本报告"""
        lines = [
            "=" * 60,
            "Writing Plan Quality Assessment Report",
            "=" * 60,
            "",
            f"Overall Score: {result.overall_score}/100",
            f"Readiness Status: {result.readiness}",
            f"Tokens Saved: {result.token_saved:,}",
            "",
            "=" * 60,
            "[+] Strengths",
            "=" * 60,
        ]

        for strength in result.strengths:
            lines.append(f"  * {strength}")

        lines.extend([
            "",
            "=" * 60,
            "[!] Issues Found",
            "=" * 60,
        ])

        if not result.issues:
            lines.append("  No issues found [PASS]")
        else:
            # 按严重程度分组
            by_severity = {}
            for issue in result.issues:
                sev = issue.severity.value
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(issue)

            for sev_name in ["critical", "high", "medium", "low", "info"]:
                if sev_name not in by_severity:
                    continue
                lines.append(f"\n[{sev_name.upper()}]")
                for issue in by_severity[sev_name]:
                    lines.append(f"  [{issue.category}] {issue.location}")
                    lines.append(f"    Issue: {issue.description}")
                    lines.append(f"    Suggestion: {issue.suggestion}")
                    if issue.auto_fixable:
                        lines.append(f"    [AUTO-FIXABLE]")
                    lines.append("")

        lines.extend([
            "=" * 60,
            "[SUMMARY]",
            "=" * 60,
            result.summary,
            "",
            "=" * 60,
        ])

        return "\n".join(lines)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="写作计划质量评估")
    parser.add_argument("plan", type=str, help="写作计划JSON文件路径")
    parser.add_argument("--deep", action="store_true", help="启用深度分析")
    parser.add_argument("--api-key", type=str, help="Anthropic API密钥")

    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"错误: 文件不存在 {plan_path}")
        return

    assessor = PlanQualityAssessor(api_key=args.api_key)
    result = assessor.assess(plan_path, use_deep_analysis=args.deep)

    print(f"\n评估完成！")
    print(f"  总分: {result.overall_score}/100")
    print(f"  状态: {result.readiness}")
    print(f"  问题数: {len(result.issues)}")
    print(f"  优点数: {len(result.strengths)}")


if __name__ == "__main__":
    main()
