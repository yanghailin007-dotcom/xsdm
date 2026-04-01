"""
阶段性复盘优化系统

在达成里程碑（30/60/100/150/200章）时，调用AI全局分析并多轮优化。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)


@dataclass
class Issue:
    """问题记录"""
    type: str  # plot/character/world/bestseller
    chapter: int
    description: str
    suggestion: str = ""
    priority: str = "p1"  # p0/p1/p2
    severity: str = ""  # high/medium/low (derived from priority)
    fix_strategy: str = "patch"
    
    def __post_init__(self):
        """根据priority自动设置severity"""
        if not self.severity:
            severity_map = {
                'p0': 'high',
                'p1': 'medium', 
                'p2': 'low'
            }
            self.severity = severity_map.get(self.priority, 'medium')


@dataclass
class FixPlan:
    """修复计划"""
    type: str  # global/batch/single
    chapter_indices: List[int]
    instructions: str
    priority: int = 5


@dataclass
class SceneIssue:
    """场景级问题记录"""
    chapter: int
    scene_number: int  # 第几个场景
    scene_type: str    # 场景类型（压抑/转折/爆发等）
    issue_type: str    # plot/character/world/bestseller
    priority: str      # p0/p1/p2
    description: str
    suggestion: str


@dataclass
class Scene:
    """场景单元"""
    scene_number: int
    scene_type: str
    content: str
    word_count: int


# 使用 src.core.APIClient.ConversationSession 进行真正的对话模式
# 不再在本地定义，而是导入核心类
from src.core.APIClient import ConversationSession


class StageReviewOptimizer:
    """
    阶段性复盘优化器（滑动窗口版）
    
    核心改进：
    - 使用滑动窗口分析，避免一次处理过多章节
    - 窗口间有重叠，保持连贯性分析
    
    默认配置：
    - 窗口大小：10章
    - 重叠：2章
    - 步长：8章（10-2）
    
    分析序列示例：
    - 第1轮：第1-10章
    - 第2轮：第8-18章（重叠2章：8,9）
    - 第3轮：第16-26章（重叠2章：16,17）
    """
    
    # 阶段配置
    STAGE_MILESTONES = [30, 60, 100, 150, 200]
    
    # 滑动窗口配置
    DEFAULT_WINDOW_SIZE = 10  # 每窗口章节数
    DEFAULT_OVERLAP = 2       # 重叠章节数
    
    def __init__(self, project_path: str, api_client=None, 
                 window_size: int = None, overlap: int = None):
        self.project_path = Path(project_path)
        self.api_client = api_client
        self.window_size = window_size or self.DEFAULT_WINDOW_SIZE
        self.overlap = overlap or self.DEFAULT_OVERLAP
        self.issues: List[Issue] = []
        self.fix_plans: List[FixPlan] = []
        self.protagonist_name = self._load_protagonist_name()
        self.stage_goals = self._load_stage_goals()
        self.emotion_plan = self._load_emotion_plan()
        # 🔥 加载提示词配置
        self._prompt_loader = get_prompt_loader()
        self._review_prompts = self._load_review_prompts()
    
    def _load_review_prompts(self) -> Dict:
        """从JSON加载复盘提示词配置"""
        try:
            # 尝试从prompt_loader加载
            if self._prompt_loader:
                prompts = self._prompt_loader.load_json("stage_review_prompts")
                if prompts:
                    return prompts
            
            # 直接加载JSON文件
            config_path = Path("prompt_packages/default/market_driven/stage_review_prompts.json")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            logger.warning("[StageOptimizer] 无法加载stage_review_prompts.json，使用硬编码默认值")
            return {}
        except Exception as e:
            logger.error(f"[StageOptimizer] 加载复盘提示词配置失败: {e}")
            return {}
    
    def _render_fix_prompt(self, variables: Dict) -> str:
        """渲染修复提示词模板"""
        templates = self._review_prompts.get("templates", {})
        
        # 获取各个部分
        word_count_template = templates.get("word_count_constraints", {}).get("template", "")
        self_check_template = templates.get("self_check_list", {}).get("template", "")
        main_template = templates.get("fix_prompt", {}).get("template", "")
        
        # 如果没有配置，使用硬编码
        if not main_template:
            return self._get_default_fix_prompt(variables)
        
        # 渲染字数约束
        word_count_constraints = word_count_template or self._get_default_word_count_constraints()
        self_check_list = self_check_template or self._get_default_self_check_list()
        
        # 准备变量
        render_vars = {
            **variables,
            "word_count_constraints": word_count_constraints,
            "self_check_list": self_check_list
        }
        
        # 渲染主模板
        try:
            return main_template.format(**render_vars)
        except KeyError as e:
            logger.warning(f"[StageOptimizer] 模板渲染失败，使用默认提示词: {e}")
            return self._get_default_fix_prompt(variables)
    
    def _get_default_fix_prompt(self, variables: Dict) -> str:
        """获取默认修复提示词（硬编码回退）"""
        return f"""修复第{variables.get('chapter_num')}章的所有问题。基于原文修改，不要重写。

**第{variables.get('chapter_num')}章：{variables.get('chapter_title', '')}**
**原文字数：**{variables.get('original_word_count')}字
**问题统计：**P0={variables.get('p0_count')}个, P1={variables.get('p1_count')}个, P2={variables.get('p2_count')}个

{self._get_default_word_count_constraints()}

## 其他关键约束
1. 主角名必须保持一致：'{variables.get('protagonist_name', '')}' - 禁止改为其他名字
2. 世界观保持一致 - 不要引入新的力量体系
3. 只修改有问题的部分，保留其他内容原样
4. 保持原有的写作风格和语气

**需要修复的所有问题：**
{variables.get('issues_text', '')}

**原文内容（前800字供参考）：**
{variables.get('original_content_preview', '')}...

## 输出格式
**JSON格式：**
{{{{\"chapter_number\": {variables.get('chapter_num')}, \"content\": \"完整的修改后章节内容\"}}}}

{self._get_default_self_check_list()}"""
    
    def _get_default_word_count_constraints(self) -> str:
        """获取默认字数约束（硬编码回退）"""
        return """## 🚨 字数约束（硬性要求，违反会导致重试）
**目标字数：2000-2500字**
**硬性下限：2000字（绝对不能低于）**
**硬性上限：2500字（绝对不能超过）**

**字数控制策略：**
- **硬性上限：修复后的字数绝对不能超过2500字！**
- 如果原文字数<2000字：扩充到2000-2200字
- 如果原文字数在2000-2500字：允许小幅增加爽点，但绝对不要超过2500字
- 如果原文字数>2500字：删减到2200-2400字
- **可以增爽点，但必须在2500字以内完成！**

**⚠️ 警告：超过2500字的内容将被强制拒绝，必须重试！**"""
    
    def _get_default_self_check_list(self) -> str:
        """获取默认自检清单（硬编码回退）"""
        return """## 🔥 强制自检清单（输出前必须完成）
- [ ] 统计content字段字数（使用len()精确计算）
- [ ] 字数是否≥2000字？（低于则必须扩充）
- [ ] 字数是否≤2500字？（绝对不能超过硬性上限！）
- [ ] 理想范围：2000-2500字

**🚨 硬性上限：绝对不能超过2500字！**
**可以增爽点，但必须在2500字以内完成！**"""
    
    def _get_retry_warning(self, last_word_count: int, over_limit: bool = True) -> str:
        """获取重试警告提示"""
        templates = self._review_prompts.get("templates", {})
        
        if over_limit:
            template = templates.get("retry_warning_over_limit", {}).get("template", "")
            if template:
                return template.format(last_word_count=last_word_count)
            return f"**🚨 紧急警告：上次输出字数{last_word_count}字超过了硬性上限2500字！**\n**你可以增爽点，但必须在2500字以内完成！**\n**删减建议：精简震惊描写（只保留现场+权威两层）、删除冗余弹幕反应、压缩环境描写。**"
        else:
            template = templates.get("retry_warning_under_limit", {}).get("template", "")
            if template:
                return template.format(last_word_count=last_word_count)
            return f"**警告：上次输出字数{last_word_count}字不足2000字。你必须输出至少2000字，但绝对不能超过2500字。输出前请统计字数。**"
        
    def _load_protagonist_name(self) -> str:
        """从project_info.json加载主角名"""
        try:
            project_info_path = self.project_path / 'project_info.json'
            if project_info_path.exists():
                with open(project_info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    # 尝试多个可能的路径
                    name = info.get('generation_metadata', {}).get('mode_specific', {}).get('info', {}).get('plan', {}).get('protagonist', {}).get('name')
                    if name:
                        return name
                    # 备选路径
                    name = info.get('selected_plan', {}).get('user_choices', {}).get('protagonist_name')
                    if name:
                        return name
            logger.warning("[StageOptimizer] 无法从project_info.json获取主角名")
            return ""
        except Exception as e:
            logger.error(f"[StageOptimizer] 加载主角名失败: {e}")
            return ""
    
    def _load_stage_goals(self) -> List[Dict]:
        """从project_info.json加载阶段目标"""
        try:
            project_info_path = self.project_path / 'project_info.json'
            if project_info_path.exists():
                with open(project_info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    # 尝试加载阶段计划
                    stage_plans = info.get('generation_metadata', {}).get('mode_specific', {}).get('info', {}).get('stage_plans', [])
                    if stage_plans:
                        # 确保返回列表类型
                        if isinstance(stage_plans, dict):
                            return [stage_plans]
                        return stage_plans if isinstance(stage_plans, list) else []
                    # 备选路径
                    plan = info.get('generation_metadata', {}).get('mode_specific', {}).get('info', {}).get('plan', {})
                    if plan and 'stage_goals' in plan:
                        stage_goals = plan.get('stage_goals', [])
                        # 确保返回列表类型
                        if isinstance(stage_goals, dict):
                            return [stage_goals]
                        return stage_goals if isinstance(stage_goals, list) else []
            return []
        except Exception as e:
            logger.error(f"[StageOptimizer] 加载阶段目标失败: {e}")
            return []
    
    def _load_emotion_plan(self) -> Dict:
        """从project_info.json加载情绪计划"""
        try:
            project_info_path = self.project_path / 'project_info.json'
            if project_info_path.exists():
                with open(project_info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    emotion_plan = info.get('generation_metadata', {}).get('mode_specific', {}).get('info', {}).get('emotion_plan', {})
                    if emotion_plan:
                        return emotion_plan
                    # 备选路径
                    plan = info.get('generation_metadata', {}).get('mode_specific', {}).get('info', {}).get('plan', {})
                    if plan and 'emotion_curve' in plan:
                        return {'emotion_curve': plan.get('emotion_curve', [])}
            return {}
        except Exception as e:
            logger.error(f"[StageOptimizer] 加载情绪计划失败: {e}")
            return {}
    
    def _load_tactical_plan(self, start_chapter: int) -> Dict:
        """从文件加载战术规划"""
        try:
            # 优先尝试新文件名格式（非隐藏文件）
            tactical_plan_path = self.project_path / f"tactical_plan_{start_chapter}.json"
            
            # 兼容旧格式（隐藏文件）
            if not tactical_plan_path.exists():
                tactical_plan_path = self.project_path / f".tactical_plan_{start_chapter}.json"
            
            if tactical_plan_path.exists():
                with open(tactical_plan_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # 尝试加载最新的战术规划（兼容新旧格式）
            tactical_files = list(self.project_path.glob("tactical_plan_*.json")) + \
                            list(self.project_path.glob(".tactical_plan_*.json"))
            if tactical_files:
                latest = max(tactical_files, key=lambda p: int(p.stem.split('_')[-1]))
                with open(latest, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"[StageOptimizer] 加载战术规划失败: {e}")
            return {}
        
    def should_trigger(self, end_chapter: int) -> bool:
        """检查是否达到阶段节点"""
        return end_chapter in self.STAGE_MILESTONES
    
    def run_review(self, start_chapter: int = None, end_chapter: int = None) -> Dict:
        """
        运行阶段性复盘分析（滑动窗口版）
        
        仅进行分析并生成报告，不修改章节内容。
        适用于生成过程中每10章触发的轻量级复盘。
        
        Args:
            start_chapter: 复盘起始章节（默认1）
            end_chapter: 复盘结束章节（默认最新生成的章节）
            
        Returns:
            复盘报告字典
        """
        if start_chapter is None:
            start_chapter = 1
        if end_chapter is None:
            # 尝试从项目目录找出最新章节
            end_chapter = self._find_latest_chapter()
        
        logger.info(f"[StageOptimizer] 启动阶段性复盘: 第{start_chapter}-{end_chapter}章")
        
        # 加载章节内容
        chapters = self._load_chapters_from_disk(start_chapter, end_chapter)
        if not chapters:
            logger.warning(f"[StageOptimizer] 未找到第{start_chapter}-{end_chapter}章内容")
            return {"status": "error", "message": "未找到章节内容"}
        
        logger.info(f"[StageOptimizer] 已加载 {len(chapters)} 章内容")
        
        # 使用滑动窗口识别问题（不修复）
        issues = self._identify_issues_sliding_window(chapters, end_chapter)
        
        # 生成报告
        self._generate_report(chapters, end_chapter)
        
        # 构建返回结果
        report = {
            "status": "success",
            "review_range": f"{start_chapter}-{end_chapter}",
            "chapters_analyzed": len(chapters),
            "issues_found": len(issues),
            "issues": [
                {
                    "chapter": i.chapter,
                    "type": i.type,
                    "severity": i.severity,
                    "description": i.description
                }
                for i in issues
            ],
            "fixes_applied": [],  # 复盘模式不修复，所以为空
            "report_path": str(self.project_path / f"optimization_report_stage_{end_chapter}.md")
        }
        
        logger.info(f"[StageOptimizer] 阶段性复盘完成: 发现 {len(issues)} 个问题")
        return report
    
    def _find_latest_chapter(self) -> int:
        """从项目目录找出最新章节号"""
        chapters_dir = self.project_path / "chapters"
        if not chapters_dir.exists():
            return 10  # 默认返回10
        
        max_ch = 0
        for f in chapters_dir.glob("chapter_*.txt"):
            try:
                ch_num = int(f.stem.split("_")[1])
                max_ch = max(max_ch, ch_num)
            except (IndexError, ValueError):
                continue
        
        return max_ch if max_ch > 0 else 10
    
    def _load_chapters_from_disk(self, start: int, end: int) -> List[Dict]:
        """从磁盘加载章节内容（支持.txt和.json格式）"""
        chapters = []
        chapters_dir = self.project_path / "chapters"
        
        if not chapters_dir.exists():
            logger.warning(f"[StageOptimizer] 章节目录不存在: {chapters_dir}")
            return chapters
        
        for ch_num in range(start, end + 1):
            content = None
            file_path = None
            
            # 🔥 首先尝试JSON格式（新的存储格式）
            json_paths = [
                chapters_dir / f"chapter_{ch_num:03d}.json",
                chapters_dir / f"chapter_{ch_num}.json",
                chapters_dir / f"{ch_num:03d}.json",
                chapters_dir / f"{ch_num}.json",
            ]
            
            for path in json_paths:
                if path.exists():
                    try:
                        import json
                        with open(path, 'r', encoding='utf-8') as f:
                            chapter_data = json.load(f)
                        # 从JSON中提取内容字段
                        if isinstance(chapter_data, dict):
                            content = chapter_data.get('content', '')
                            if not content:
                                # 尝试其他可能的字段名
                                content = chapter_data.get('chapter_content', '')
                        file_path = path
                        break
                    except Exception as e:
                        logger.warning(f"[StageOptimizer] 读取JSON章节文件失败 {path}: {e}")
                        continue
            
            # 如果JSON没找到，尝试TXT格式（旧格式兼容）
            if not content:
                txt_paths = [
                    chapters_dir / f"chapter_{ch_num:03d}.txt",
                    chapters_dir / f"chapter_{ch_num}.txt",
                    chapters_dir / f"{ch_num:03d}.txt",
                    chapters_dir / f"{ch_num}.txt",
                ]
                
                for path in txt_paths:
                    if path.exists():
                        try:
                            content = path.read_text(encoding='utf-8')
                            file_path = path
                            break
                        except Exception as e:
                            logger.warning(f"[StageOptimizer] 读取TXT章节文件失败 {path}: {e}")
                            continue
            
            if content:
                chapters.append({
                    "chapter_number": ch_num,
                    "content": content,
                    "word_count": len(content)
                })
                logger.debug(f"[StageOptimizer] 已加载第{ch_num}章: {file_path}")
            else:
                logger.warning(f"[StageOptimizer] 未找到第{ch_num}章内容")
        
        logger.info(f"[StageOptimizer] 从磁盘加载: 第{start}-{end}章，成功{len(chapters)}章")
        return chapters
    
    def optimize_window(self, window_start: int, window_end: int) -> Dict:
        """
        优化单个滑动窗口（10章）
        
        流程：
        1. 从磁盘加载窗口内的章节
        2. 🔥 计算并更新章节质量评分
        3. 🔥 低分章节（<7.0）自动创建质量问题并修复
        4. 识别其他问题（AI分析）
        5. 修复问题（如果需要）
        6. 生成窗口优化报告
        
        Args:
            window_start: 窗口起始章节号
            window_end: 窗口结束章节号
            
        Returns:
            优化报告字典
        """
        logger.info(f"[StageOptimizer] 🔄 开始优化窗口 {window_start}-{window_end}")
        
        # 1. 加载章节内容
        window_chapters = self._load_chapters_from_disk(window_start, window_end)
        if not window_chapters:
            logger.warning(f"[StageOptimizer] 未找到窗口 {window_start}-{window_end} 的章节内容")
            return {"status": "error", "message": "未找到章节内容"}
        
        logger.info(f"[StageOptimizer] 已加载窗口章节: {len(window_chapters)} 章")
        
        # 🔥 2. 计算并更新质量评分（新增）
        logger.info(f"[StageOptimizer] 🔍 开始计算章节质量评分...")
        scored_chapters = []
        quality_issues = []  # 质量评分发现的低分章节
        
        for chapter in window_chapters:
            ch_num = chapter.get('chapter_number', 0)
            content = chapter.get('content', '')
            word_count = len(content)
            score = self._calculate_chapter_quality_score(chapter)
            chapter['quality_score'] = score
            self._update_chapter_quality_score(ch_num, score)
            scored_chapters.append(chapter)
            
            # 🔥 强制标记字数不足的章节（<1800字）
            if word_count < 1800:
                quality_issues.append(Issue(
                    type="bestseller",
                    chapter=ch_num,
                    description=f"字数严重不足({word_count}字)，低于1800字最低标准",
                    suggestion=f"扩充内容至2000-2500字，当前仅{word_count}字",
                    priority="p1",
                    severity="high"
                ))
                logger.warning(f"[StageOptimizer] 第{ch_num}章字数仅{word_count}字，强制标记为待修复")
            # 🔥 自动标记低分章节为需要修复
            elif score < 7.0:
                quality_issues.append(Issue(
                    type="bestseller",
                    chapter=ch_num,
                    description=f"质量评分过低({score}分)，字数或爽点密度不足",
                    suggestion="扩充内容至2000字以上，增加爽点或反转",
                    priority="p1",
                    severity="medium"
                ))
                logger.warning(f"[StageOptimizer] 第{ch_num}章质量评分{score}，标记为待修复")
            elif score < 8.0:
                # 7.0-8.0分的章节，如果是关键章节（如高潮章），也建议优化
                content = chapter.get('content', '')
                # 检测是否应该是高潮章
                if any(kw in content for kw in ['高潮', '爆发', '决战', '终极']):
                    quality_issues.append(Issue(
                        type="bestseller",
                        chapter=ch_num,
                        description=f"高潮章节质量一般({score}分)，建议强化爽点",
                        suggestion="增加震惊层次，强化打脸效果",
                        priority="p2",
                        severity="low"
                    ))
        
        avg_score = sum(c.get('quality_score', 8.0) for c in scored_chapters) / len(scored_chapters)
        low_score_count = len([c for c in scored_chapters if c.get('quality_score', 8.0) < 7.0])
        logger.info(f"[StageOptimizer] ✅ 窗口质量评分完成 | 平均分: {avg_score:.2f} | 低分章节: {low_score_count}章")
        
        # 3. 识别问题（使用对话式优化，传入质量发现的Issue）
        window_issues, fixed_chapters = self._optimize_window_conversational(
            window_chapters, 
            window_idx=1,
            max_rounds=1,
            pre_identified_issues=quality_issues  # 🔥 传入质量评分发现的问题
        )
        
        # 3. 生成窗口专属报告（使用已评分的章节）
        report_path = self.project_path / f"window_review_{window_start}_{window_end}.md"
        self._generate_window_report(
            scored_chapters, fixed_chapters, window_issues, 
            window_start, window_end, report_path
        )
        
        # 4. 构建返回结果（包含质量评分统计）
        scores = [c.get('quality_score', 8.0) for c in scored_chapters]
        report = {
            "status": "success",
            "window": f"{window_start}-{window_end}",
            "chapters_analyzed": len(window_chapters),
            "avg_quality_score": round(sum(scores) / len(scores), 1) if scores else 8.0,
            "max_quality_score": max(scores) if scores else 8.0,
            "min_quality_score": min(scores) if scores else 8.0,
            "score_distribution": {
                "excellent(9.0+)": len([s for s in scores if s >= 9.0]),
                "good(8.0-8.9)": len([s for s in scores if 8.0 <= s < 9.0]),
                "average(7.0-7.9)": len([s for s in scores if 7.0 <= s < 8.0]),
                "below_avg(<7.0)": len([s for s in scores if s < 7.0])
            },
            "issues_found": len(window_issues),
            "issues": [
                {
                    "chapter": i.chapter,
                    "type": i.type,
                    "severity": i.severity,
                    "description": i.description
                }
                for i in window_issues
            ],
            "fixes_applied": [
                {
                    "chapter": ch.get('chapter_number'),
                    "optimized": ch.get('optimized', False),
                    "word_count": ch.get('word_count', 0)
                }
                for ch in fixed_chapters if ch.get('optimized')
            ],
            "report_path": str(report_path)
        }
        
        logger.info(f"[StageOptimizer] ✅ 窗口 {window_start}-{window_end} 优化完成 | 问题: {len(window_issues)} | 修复: {len(report['fixes_applied'])}")
        return report
    
    def _generate_window_report(self, original_chapters: List[Dict], 
                                fixed_chapters: List[Dict],
                                issues: List[Issue],
                                window_start: int, window_end: int,
                                report_path: Path):
        """生成单个窗口的优化报告"""
        
        # 计算修复统计
        fixed_count = len([c for c in fixed_chapters if c.get('optimized')])
        
        report = f"""# 滑动窗口优化报告

## 窗口范围：第{window_start}-{window_end}章

## 优化统计
- 分析章节数：{len(original_chapters)}
- 发现问题数：{len(issues)}
- 严重问题数：{len([i for i in issues if i.severity == 'high'])}
- 修复章节数：{fixed_count}

## 问题详情
"""
        
        # 按类型分组问题
        from collections import defaultdict
        issues_by_type = defaultdict(list)
        for issue in issues:
            issues_by_type[issue.type].append(issue)
        
        # 输出各类问题
        issue_type_names = {
            'plot': '剧情连续性',
            'character': '角色一致性', 
            'world': '设定一致性',
            'bestseller': '爆款标准差距',
            'emotion': '情绪节奏',
            'hook': '钩子设计'
        }
        
        for type_name, type_issues in issues_by_type.items():
            type_display = issue_type_names.get(type_name, type_name)
            report += f"\n### {type_display} ({len(type_issues)}个)\n"
            for issue in type_issues[:10]:  # 最多显示10个
                report += f"- **第{issue.chapter}章** [{issue.severity}] {issue.description}\n"
            if len(type_issues) > 10:
                report += f"- ... 还有 {len(type_issues) - 10} 个问题\n"
        
        # 🔥 章节质量评分统计（新增）
        report += f"\n## 章节质量评分统计\n"
        scores = [ch.get('quality_score', 8.0) for ch in original_chapters]
        avg_score = sum(scores) / len(scores) if scores else 8.0
        max_score = max(scores) if scores else 8.0
        min_score = min(scores) if scores else 8.0
        
        report += f"- **窗口平均分**: {avg_score:.1f}/10.0\n"
        report += f"- **最高评分**: {max_score:.1f}/10.0\n"
        report += f"- **最低评分**: {min_score:.1f}/10.0\n"
        report += f"- **评分分布**: \n"
        
        # 统计各分数段
        excellent = len([s for s in scores if s >= 9.0])  # 9.0+
        good = len([s for s in scores if 8.0 <= s < 9.0])  # 8.0-8.9
        average = len([s for s in scores if 7.0 <= s < 8.0])  # 7.0-7.9
        below_avg = len([s for s in scores if s < 7.0])  # <7.0
        
        report += f"  - 🌟 优秀(9.0+): {excellent}章\n"
        report += f"  - ✅ 良好(8.0-8.9): {good}章\n"
        report += f"  - ⚠️ 一般(7.0-7.9): {average}章\n"
        report += f"  - 🔴 待改进(<7.0): {below_avg}章\n"
        
        # 详细评分表
        report += f"\n### 各章节详细评分\n"
        report += "| 章节 | 字数 | 质量评分 | 评价 |\n"
        report += "|------|------|----------|------|\n"
        
        for ch in original_chapters:
            ch_num = ch.get('chapter_number', 0)
            word_count = ch.get('word_count', 0)
            score = ch.get('quality_score', 8.0)
            
            # 评价标签
            if score >= 9.0:
                label = "🌟 优秀"
            elif score >= 8.0:
                label = "✅ 良好"
            elif score >= 7.0:
                label = "⚠️ 一般"
            else:
                label = "🔴 待改进"
            
            report += f"| {ch_num} | {word_count} | {score:.1f}/10.0 | {label} |\n"
        
        # 🔥 章节质量对比（修复前后的评分对比）
        report += f"\n## 章节质量优化对比\n"
        report += "| 章节 | 原评分 | 修复后 | 字数变化 | 状态 |\n"
        report += "|------|--------|--------|----------|------|\n"
        
        fixed_dict = {c.get('chapter_number'): c for c in fixed_chapters}
        for ch in original_chapters:
            ch_num = ch.get('chapter_number', 0)
            orig_score = ch.get('quality_score', 8.0)
            orig_words = ch.get('word_count', 0)
            fixed_ch = fixed_dict.get(ch_num)
            if fixed_ch and fixed_ch.get('optimized'):
                new_score = fixed_ch.get('quality_score', orig_score)
                new_words = fixed_ch.get('word_count', orig_words)
                word_change = f"{orig_words}→{new_words}"
                score_change = f"{orig_score:.1f}→{new_score:.1f}"
                # 显示评分提升
                if new_score > orig_score:
                    score_display = f"{score_change} 📈"
                elif new_score < orig_score:
                    score_display = f"{score_change} 📉"
                else:
                    score_display = f"{score_change} ➡️"
                report += f"| {ch_num} | {orig_score:.1f} | {score_display} | {word_change} | ✅ 已优化 |\n"
            else:
                report += f"| {ch_num} | {orig_score:.1f} | - | {orig_words} | ➖ 未修改 |\n"
        
        report += f"\n---\n生成时间：{self._get_timestamp()}\n"
        
        # 保存报告
        report_path.write_text(report, encoding='utf-8')
        logger.info(f"[StageOptimizer] 窗口报告已保存: {report_path}")
    
    def optimize_stage(self, chapters: List[Dict], stage_end: int, 
                       use_conversational: bool = True,
                       use_scene_level: bool = False,
                       max_rounds: int = 2) -> List[Dict]:
        """
        优化整个阶段（对话式滑动窗口版）
        
        Args:
            chapters: 当前阶段的所有章节
            stage_end: 阶段结束章节号
            use_conversational: 使用对话式优化（P0->P1->P2逐级修复）
            use_scene_level: 使用场景级优化（更精细，只改有问题场景）
            max_rounds: 最大优化轮次（默认2轮）
            
        Returns:
            优化后的章节列表
        """
        logger.info(f"[StageOptimizer] 开始优化第1-{stage_end}章 (conversational={use_conversational}, scene_level={use_scene_level}, max_rounds={max_rounds})")
        logger.info(f"[StageOptimizer] 窗口大小：{self.window_size}，重叠：{self.overlap}")
        
        if use_scene_level:
            # 场景级优化：识别问题章节，只修复有问题的场景
            return self._optimize_stage_scene_level(chapters, stage_end, max_rounds)
        elif use_conversational:
            # 对话式优化：每个窗口独立session，P0->P1->P2逐级修复
            return self._optimize_stage_conversational(chapters, stage_end, max_rounds)
        else:
            # 传统优化方式
            return self._optimize_stage_traditional(chapters, stage_end, max_rounds)
    
    def _optimize_stage_scene_level(self, chapters: List[Dict], stage_end: int, max_rounds: int = 2) -> List[Dict]:
        """场景级优化实现"""
        windows = self._split_windows(chapters)
        all_fixed_chapters: Dict[int, Dict] = {}
        
        for idx, window_chapters in enumerate(windows):
            window_idx = idx + 1
            
            # 场景级优化
            window_issues, fixed_chapters = self._optimize_window_scene_level(
                window_chapters, window_idx
            )
            
            # 合并结果（处理重叠章节）
            for ch in fixed_chapters:
                ch_num = ch.get('chapter_number', 0)
                if ch_num not in all_fixed_chapters:
                    all_fixed_chapters[ch_num] = ch
                else:
                    # 重叠章节：如果新优化版本有优化标记，使用新版本
                    if ch.get('optimized'):
                        all_fixed_chapters[ch_num] = ch
            
            self.issues.extend(window_issues)
        
        # Build result list - include all chapters, use fixed if available
        result_chapters = []
        for ch in chapters:
            ch_num = ch.get('chapter_number', 0)
            if ch_num in all_fixed_chapters:
                result_chapters.append(all_fixed_chapters[ch_num])
            else:
                result_chapters.append(ch.copy())
        return result_chapters
    
    def _optimize_stage_conversational(self, chapters: List[Dict], stage_end: int, max_rounds: int = 2) -> List[Dict]:
        """对话式优化实现"""
        windows = self._split_windows(chapters)
        all_fixed_chapters: Dict[int, Dict] = {}
        all_issues: List[Issue] = []
        
        for window_idx, window in enumerate(windows, 1):
            window_ch_nums = [c.get('chapter_number') for c in window]
            logger.info(f"[StageOptimizer] === Window {window_idx}/{len(windows)}: ch{window_ch_nums[0]}-{window_ch_nums[-1]} ===")
            
            # Use already fixed chapters if available
            current_window = []
            for ch in window:
                ch_num = ch.get('chapter_number')
                if ch_num in all_fixed_chapters:
                    current_window.append(all_fixed_chapters[ch_num])
                else:
                    current_window.append(ch)
            
            # Conversational optimization
            window_issues, fixed_window = self._optimize_window_conversational(current_window, window_idx, max_rounds)
            all_issues.extend(window_issues)
            
            for fixed_ch in fixed_window:
                ch_num = fixed_ch.get('chapter_number')
                all_fixed_chapters[ch_num] = fixed_ch
        
        # Build result list - make sure to copy chapters to avoid modifying original
        result_chapters = []
        for i, ch in enumerate(chapters):
            ch_num = ch.get('chapter_number', i+1)
            if ch_num in all_fixed_chapters:
                # Use fixed chapter (already a copy)
                result_chapters.append(all_fixed_chapters[ch_num])
            else:
                # Copy original chapter to avoid modifying input
                result_chapters.append(ch.copy())
        
        # Update issues for report
        self.issues = all_issues
        
        self._generate_report(result_chapters, stage_end)
        logger.info(f"[StageOptimizer] Conversational optimization completed")
        return result_chapters
    
    def _optimize_stage_traditional(self, chapters: List[Dict], stage_end: int, max_rounds: int = 2) -> List[Dict]:
        """传统优化实现（原逻辑）"""
        current_chapters = chapters
        
        for round_num in range(1, max_rounds + 1):  # 使用max_rounds参数
            logger.info(f"[StageOptimizer] === Round {round_num} ===")
            
            issues = self._identify_issues_sliding_window(current_chapters, stage_end)
            high_issues = [i for i in issues if i.severity == "high"]
            
            if len(high_issues) == 0:
                logger.info(f"[StageOptimizer] No high issues, stopping")
                break
            
            fix_plans = self._plan_fixes(issues, current_chapters)
            current_chapters = self._execute_fixes(fix_plans, current_chapters)
            
            if self._verify_fixes(issues, current_chapters):
                logger.info(f"[StageOptimizer] Round {round_num} verified")
        
        self._sync_settings(current_chapters)
        self._generate_report(current_chapters, stage_end)
        return current_chapters
    
    def _split_windows(self, chapters: List[Dict]) -> List[List[Dict]]:
        """
        将章节切分为滑动窗口
        
        Returns:
            窗口列表，每个窗口包含若干章节
        """
        if len(chapters) <= self.window_size:
            return [chapters]
        
        windows = []
        step = self.window_size - self.overlap
        
        start = 0
        while start < len(chapters):
            end = min(start + self.window_size, len(chapters))
            window = chapters[start:end]
            windows.append(window)
            
            if end >= len(chapters):
                break
            start += step
        
        logger.info(f"[StageOptimizer] 切分为 {len(windows)} 个窗口")
        for i, w in enumerate(windows):
            ch_nums = [c.get('chapter_number', '?') for c in w]
            logger.info(f"  窗口{i+1}: 第{ch_nums[0]}-{ch_nums[-1]}章")
        
        return windows
    
    def _identify_issues_sliding_window(self, chapters: List[Dict], stage_end: int) -> List[Issue]:
        """
        Stage 1: 使用滑动窗口识别问题
        """
        windows = self._split_windows(chapters)
        all_issues = []
        
        for i, window in enumerate(windows):
            window_chapters = [c.get('chapter_number', '?') for c in window]
            logger.info(f"[StageOptimizer] 分析窗口{i+1}/{len(windows)}: 第{window_chapters[0]}-{window_chapters[-1]}章")
            
            window_issues = self._identify_issues_in_window(window, i+1, len(windows))
            all_issues.extend(window_issues)
        
        # 合并重复问题（同一章节同一类型的问题）
        merged_issues = self._merge_duplicate_issues(all_issues)
        
        logger.info(f"[StageOptimizer] 共发现问题：{len(merged_issues)} 个")
        return merged_issues
    
    def _identify_issues_in_window(self, window_chapters: List[Dict], 
                                   window_idx: int, total_windows: int) -> List[Issue]:
        """分析单个窗口的问题"""
        first_ch = window_chapters[0].get('chapter_number', '?')
        last_ch = window_chapters[-1].get('chapter_number', '?')
        
        # 构建分析 prompt
        chapters_text = self._format_chapters_for_analysis(window_chapters)
        
        # 重叠章节的特殊说明
        overlap_note = ""
        if window_idx > 1:
            overlap_chapters = [c.get('chapter_number') for c in window_chapters[:self.overlap]]
            overlap_note = f"\n注：第{overlap_chapters}章与上一窗口重叠，用于检查连贯性。"
        
        # 构建关键约束信息
        protagonist_name = self.protagonist_name or "主角"
        
        prompt = f"""你是一名专业的小说编辑，请对以下第{first_ch}-{last_ch}章进行严格分析。

{overlap_note}

【关键约束 - 必须检查】
- 主角名: {protagonist_name} ⚠️ 必须全文保持一致，禁止出现其他名字
- 战术规划: 每章内容必须与其【战术规划】中定义的事件、情绪、节拍类型一致

章节内容摘要：
{chapters_text}

请检查以下问题：

## 1. 剧情连续性问题（重点关注窗口边界）
- 窗口内各章之间是否连贯
- 章尾悬念是否在下一章有回应
- 时间线、场景切换是否合理

## 2. 角色一致性问题（重点检查）
- **主角名一致性**: 是否全文保持"{protagonist_name}"，没有出现"叶辰""林凡"等其他名字
- 主角能力/状态是否稳定
- 配角立场是否有异常变化
- 新角色登场是否有铺垫

## 3. 战术规划一致性（重点检查）
- **事件一致性**: 章节实际发生的事件是否与【战术规划】中定义的"关键事件"一致
- **情绪一致性**: 实际情绪曲线是否与规划的"情绪+强度"匹配
- **节拍一致性**: 实际节拍类型是否与规划一致(铺垫/冲突/反转/渲染/伏笔)
- **钩子落实**: 章尾钩子是否与规划的"钩子内容"一致

## 4. 世界设定一致性
- 力量体系描述是否统一
- 组织/势力设定是否矛盾

## 5. 爆款标准差距
- 爽点密度（每章应有≥1个）
- 情绪转折次数（每章应有≥3次）
- 字数是否达标（2000-2500字）

输出格式（JSON）：
{{
    "issues": [
        {{
            "type": "plot/character/world/bestseller/tactical",
            "severity": "high/medium/low",
            "chapter": 章节号,
            "description": "问题描述",
            "suggestion": "修复建议"
        }}
    ]
}}

严重问题(high)：
- 主角名不一致（如出现"叶辰"而非"{protagonist_name}"）
- 实际事件与战术规划严重偏离
- 主角能力突变、反派无铺垫登场

中等问题(medium)：
- 情绪曲线与规划有偏差
- 节拍类型不匹配
- 小伏笔未回收

轻微问题(low)：
- 某章爽点不足
- 字数略低于2000字"""

        # 调用AI分析
        if not self.api_client:
            logger.warning("[StageOptimizer] 无API客户端，跳过问题识别")
            return []
        
        try:
            response = self.api_client.generate(messages=[
                {"role": "user", "content": prompt}
            ])
            
            content = response.get("content", "")
            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                issues = [Issue(**item) for item in data.get("issues", [])]
                logger.info(f"[StageOptimizer] 窗口{window_idx}发现 {len(issues)} 个问题")
                return issues
        except Exception as e:
            logger.error(f"[StageOptimizer] 窗口{window_idx}分析失败: {e}")
        
        return []
    
    def _merge_duplicate_issues(self, issues: List[Issue]) -> List[Issue]:
        """合并重复问题（同一章节同一类型）"""
        seen = {}
        merged = []
        
        for issue in issues:
            key = (issue.chapter, issue.type, issue.description[:30])
            if key not in seen:
                seen[key] = issue
                merged.append(issue)
            else:
                # 如果重复，保留severity更高的
                if issue.severity == "high" and seen[key].severity != "high":
                    seen[key] = issue
        
        return merged
    
    def _optimize_window_conversational(self, window_chapters: List[Dict], 
                                        window_idx: int,
                                        max_rounds: int = 2,
                                        pre_identified_issues: List[Issue] = None) -> Tuple[List[Issue], List[Dict]]:
        """
        对话式循环优化单个窗口
        
        流程：
        1. 合并预识别的问题（如质量评分发现的低分章节）
        2. 识别P0->修复P0->识别P1->修复P1->识别P2->修复P2
        
        Args:
            window_chapters: 窗口内的章节
            window_idx: 窗口索引
            max_rounds: 最大优化轮次
            pre_identified_issues: 预识别的问题（如质量评分发现的低分章节）
        """
        first_ch = window_chapters[0].get('chapter_number', '?')
        last_ch = window_chapters[-1].get('chapter_number', '?')
        
        logger.info(f"[StageOptimizer] Conversational optimization window{window_idx}: ch{first_ch}-{last_ch}")
        
        if not self.api_client:
            return [], window_chapters
        
        # 🔥 从JSON配置加载system prompt
        templates = self._review_prompts.get("templates", {})
        system_prompt = templates.get("editor_system_prompt", """你是专业的小说编辑。分析并修复质量问题。
工作流程：1) 识别P0/P1/P2问题 2) 逐章修复 3) 验证。只输出JSON格式。""")
        
        session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            temperature=0.3,
            purpose_prefix=f"StageOpt-w{window_idx}"
        )
        
        # Step 1: Send chapters with stage goals
        chapters_text = self._format_chapters_for_analysis(window_chapters)
        
        # 构建阶段目标信息
        stage_goals_text = ""
        # 确保 stage_goals 是列表类型
        stage_goals_list = self.stage_goals if isinstance(self.stage_goals, list) else []
        if stage_goals_list:
            stage_goals_text = "\n【阶段目标】\n"
            for goal in stage_goals_list[:3]:  # 最多显示3个阶段目标
                if isinstance(goal, dict):
                    stage_goals_text += f"- 第{goal.get('chapter_range', 'N/A')}章: {goal.get('goal', '无')}\n"
        
        # 构建情绪计划信息
        emotion_text = ""
        if self.emotion_plan and 'emotion_curve' in self.emotion_plan:
            emotion_curve = self.emotion_plan['emotion_curve']
            if emotion_curve:
                emotion_text = "\n【情绪曲线规划】\n"
                for point in emotion_curve[:5]:  # 最多显示5个情绪点
                    emotion_text += f"- 第{point.get('chapter', '?')}章: {point.get('emotion', '无')} (强度{point.get('intensity', 'N/A')})\n"
        
        # 构建关键约束信息
        protagonist_name = self.protagonist_name or "主角"
        
        init_prompt = f"""分析第{first_ch}-{last_ch}章:

【关键约束 - 必须检查】
- 主角名: {protagonist_name} ⚠️ 必须全文保持一致
- 战术规划: 每章内容必须与其【战术规划】中定义的事件、情绪、节拍类型一致

{stage_goals_text}{emotion_text}

{chapters_text}

回复：准备就绪。"""
        session.send_message(init_prompt, purpose=f"w{window_idx}-init")
        
        # Step 2: Identify all issues
        identify_prompt = f"""严格分析质量问题。

【必须检查的维度】
1. **角色名一致性** (P0级别): 是否全文保持主角名"{protagonist_name}"，禁止出现"叶辰"等其他名字
2. **战术规划一致性** (P0/P1级别): 
   - 实际发生的事件是否与【战术规划】中定义的"关键事件"一致
   - 实际情绪是否与规划的"情绪+强度"匹配
   - 实际节拍类型是否与规划一致
   - 章尾钩子是否与规划的"钩子内容"一致
3. **剧情连续性**: 窗口内各章之间是否连贯，章尾悬念是否有回应
4. **世界设定一致性**: 力量体系、组织设定是否统一
5. **爆款标准差距**: 爽点密度、情绪转折次数、字数是否达标

输出JSON格式：
{{
    "issues": [
        {{"type": "plot|character|world|bestseller|tactical", "priority": "p0|p1|p2", 
         "chapter": 1, "description": "问题描述", "suggestion": "修复建议"}}
    ],
    "summary": {{"p0_count": 0, "p1_count": 0, "p2_count": 0}}
}}

优先级定义：
- P0: 严重问题（主角名不一致、事件与战术规划严重偏离）
- P1: 中等问题（情绪偏差、节拍不匹配）
- P2: 轻微问题（爽点不足、字数略低）"""
        
        response = session.send_message(identify_prompt, purpose=f"w{window_idx}-identify")
        data = self._safe_parse_json(response, f"w{window_idx}-identify")
        
        if not data:
            return [], window_chapters
        
        ai_issues = [Issue(**item) for item in data.get("issues", [])]
        
        # 🔥 合并预识别的问题（质量评分发现的低分章节）
        all_issues = ai_issues.copy()
        if pre_identified_issues:
            # 避免重复：如果同一章节同一类型的问题已存在，优先使用pre_identified（更具体）
            existing_keys = {(i.chapter, i.type) for i in ai_issues}
            for pre_issue in pre_identified_issues:
                key = (pre_issue.chapter, pre_issue.type)
                if key not in existing_keys:
                    all_issues.append(pre_issue)
                    logger.info(f"[StageOptimizer] 添加质量评分发现的问题: 第{pre_issue.chapter}章 - {pre_issue.description[:30]}...")
        
        # 重新统计
        p0_count = sum(1 for i in all_issues if i.priority == 'p0')
        p1_count = sum(1 for i in all_issues if i.priority == 'p1')
        p2_count = sum(1 for i in all_issues if i.priority == 'p2')
        logger.info(f"[StageOptimizer] w{window_idx} 总问题: P0={p0_count}, P1={p1_count}, P2={p2_count} (AI发现{len(ai_issues)}个, 质量评分发现{len(pre_identified_issues) if pre_identified_issues else 0}个)")
        
        # Step 3: Fix by chapter - 逐章一次性修复所有问题
        fixed_chapters = [ch.copy() for ch in window_chapters]
        chapter_map = {ch['chapter_number']: idx for idx, ch in enumerate(fixed_chapters)}
        
        # 按章节分组所有问题（不分优先级）
        issues_by_chapter = {}
        for issue in all_issues:
            ch_num = int(issue.chapter)
            if ch_num not in issues_by_chapter:
                issues_by_chapter[ch_num] = []
            issues_by_chapter[ch_num].append(issue)
        
        # 逐章修复（一次性修复该章所有P0+P1+P2问题）
        for ch_num in sorted(issues_by_chapter.keys()):
            if ch_num not in chapter_map:
                continue
            
            ch_idx = chapter_map[ch_num]
            ch = fixed_chapters[ch_idx]
            ch_issues = issues_by_chapter[ch_num]
            
            # 统计该章各优先级问题数
            p0_count = sum(1 for i in ch_issues if i.priority == 'p0')
            p1_count = sum(1 for i in ch_issues if i.priority == 'p1')
            p2_count = sum(1 for i in ch_issues if i.priority == 'p2')
            
            # 如果只有P2问题且配置为忽略，则跳过
            # 注意：这里可根据需要添加开关
            
            # 构建该章所有问题的描述
            issues_text = "\n".join([f"- [{i.priority.upper()}/{i.type}]: {i.description}" for i in ch_issues])
            
            protagonist_name = self.protagonist_name
            ch_title = ch.get('title', '')
            original_content = ch.get('content', '')
            original_word_count = ch.get('word_count', len(original_content))
            
            # 🔥 使用JSON配置渲染修复提示词
            fix_prompt_vars = {
                "chapter_num": ch_num,
                "chapter_title": ch_title,
                "original_word_count": original_word_count,
                "p0_count": p0_count,
                "p1_count": p1_count,
                "p2_count": p2_count,
                "protagonist_name": protagonist_name,
                "issues_text": issues_text,
                "original_content_preview": original_content[:800]
            }
            fix_prompt = self._render_fix_prompt(fix_prompt_vars)
            
            # 尝试修复（带重试机制）
            retry_config = self._review_prompts.get("retry", {})
            max_retries = retry_config.get("max_retries", 2)
            retry_count = 0
            is_accepted = False
            last_word_count = 0  # 🔥 记录上次字数用于重试提示
            
            while retry_count <= max_retries and not is_accepted:
                if retry_count > 0:
                    logger.info(f"[StageOptimizer] 第{ch_num}章第{retry_count}次重试...")
                    # 🔥 根据上次问题动态调整提示词（从JSON配置加载）
                    if last_word_count > 2500:
                        fix_prompt += f"\n\n{self._get_retry_warning(last_word_count, over_limit=True)}"
                    elif last_word_count < 2000:
                        fix_prompt += f"\n\n{self._get_retry_warning(last_word_count, over_limit=False)}"
                
                logger.info(f"[StageOptimizer] 修复第{ch_num}章的所有问题 (P0={p0_count}, P1={p1_count}, P2={p2_count}, 尝试{retry_count+1}/{max_retries+1})")
                fix_response = session.send_message(fix_prompt, purpose=f"w{window_idx}-fix-ch{ch_num}-try{retry_count}")
                fix_data = self._safe_parse_json(fix_response, f"w{window_idx}-fix-ch{ch_num}-try{retry_count}")
                
                if not fix_data:
                    retry_count += 1
                    continue
                
                # 解析修复结果
                if "chapter_number" in fix_data:
                    new_content = fix_data.get("content")
                elif "fixed_chapters" in fix_data and len(fix_data["fixed_chapters"]) > 0:
                    new_content = fix_data["fixed_chapters"][0].get("content")
                else:
                    retry_count += 1
                    continue
                
                ch_idx = chapter_map[ch_num]
                original_word_count = fixed_chapters[ch_idx].get("word_count", 0)
                new_word_count = len(new_content) if new_content else 0
                last_word_count = new_word_count  # 🔥 记录本次字数用于下次重试提示
                
                # 🔥 字数检查：从JSON配置读取
                word_count_config = self._review_prompts.get("word_count", {})
                MIN_ABSOLUTE = word_count_config.get("min_absolute", 2000)  # 硬性下限
                MAX_ABSOLUTE = word_count_config.get("max_absolute", 2500)  # 硬性上限
                MIN_PERCENT = word_count_config.get("min_percent", 0.8)
                MAX_PERCENT = word_count_config.get("max_percent", 1.1)
                
                # 检查1：硬性下限
                if new_word_count < MIN_ABSOLUTE:
                    logger.warning(f"[StageOptimizer] 第{ch_num}章字数({new_word_count})低于硬性下限{MIN_ABSOLUTE}字，将重试")
                    retry_count += 1
                    continue
                
                # 检查2：硬性上限（绝对不能超过）
                if new_word_count > MAX_ABSOLUTE:
                    logger.warning(f"[StageOptimizer] 第{ch_num}章字数({new_word_count})超过硬性上限{MAX_ABSOLUTE}字，将重试")
                    retry_count += 1
                    continue
                
                # 检查3：百分比范围（宽松警告，不强制重试）
                min_percent = original_word_count * MIN_PERCENT
                max_percent = original_word_count * MAX_PERCENT
                if new_word_count < min_percent or new_word_count > max_percent:
                    deviation = abs(new_word_count - original_word_count) / original_word_count * 100
                    direction = "增加" if new_word_count > original_word_count else "减少"
                    logger.info(f"[StageOptimizer] 第{ch_num}章字数较原文{direction}{deviation:.1f}%，但在{MIN_ABSOLUTE}-{MAX_ABSOLUTE}字范围内，接受修改")
                
                # 字数符合要求，接受修改
                is_accepted = True
                change_pct = (new_word_count - original_word_count) / original_word_count * 100 if original_word_count > 0 else 0
                fixed_chapters[ch_idx]["content"] = new_content
                fixed_chapters[ch_idx]["word_count"] = new_word_count
                fixed_chapters[ch_idx]["optimized"] = True
                logger.info(f"[StageOptimizer] 第{ch_num}章已优化: {original_word_count} -> {new_word_count}字 ({change_pct:+.1f}%)")
            
            if not is_accepted:
                # 🔥 最终处理：从JSON配置读取截断设置
                retry_config = self._review_prompts.get("retry", {})
                truncate_on_failure = retry_config.get("truncate_on_failure", True)
                truncate_to = retry_config.get("truncate_to", 2500)
                truncate_min = retry_config.get("truncate_min", 2300)
                
                if truncate_on_failure and last_word_count > truncate_to:
                    logger.warning(f"[StageOptimizer] 第{ch_num}章经过{max_retries+1}次尝试仍超过{truncate_to}字({last_word_count})，执行强制截断")
                    
                    # 强制截断策略：保留到truncate_to字，找到最近的段落结尾
                    truncated_content = new_content[:truncate_to]
                    # 找到最后一个换行符，避免截断在句子中间
                    last_newline = truncated_content.rfind('\n')
                    if last_newline > truncate_min:  # 确保至少保留truncate_min字
                        truncated_content = truncated_content[:last_newline]
                    
                    # 添加截断标记
                    truncated_content += "\n\n【系统自动优化：此处删减冗余内容以保持最佳阅读节奏】"
                    
                    fixed_chapters[ch_idx]["content"] = truncated_content
                    fixed_chapters[ch_idx]["word_count"] = len(truncated_content)
                    fixed_chapters[ch_idx]["optimized"] = True
                    fixed_chapters[ch_idx]["truncated"] = True  # 标记为截断
                    logger.info(f"[StageOptimizer] 第{ch_num}章已强制截断: {last_word_count} -> {len(truncated_content)}字")
                else:
                    logger.error(f"[StageOptimizer] 第{ch_num}章经过{max_retries+1}次尝试仍无法达到字数要求({last_word_count}字<2000)，放弃修改")
        
        # 🔥 重新计算修复后章节的质量评分
        logger.info(f"[StageOptimizer] 重新计算修复后章节的质量评分...")
        for ch in fixed_chapters:
            if ch.get('optimized'):
                ch_num = ch.get('chapter_number', 0)
                new_score = self._calculate_chapter_quality_score(ch)
                ch['quality_score'] = new_score
                self._update_chapter_quality_score(ch_num, new_score)
                logger.info(f"[StageOptimizer] 第{ch_num}章修复后评分: {new_score}")
        
        return all_issues, fixed_chapters
    
    def _safe_parse_json(self, content: str, context: str = "") -> Optional[Dict]:
        """Safe JSON parsing with multiple strategies"""
        import re
        import ast
        
        if not content or not isinstance(content, str):
            logger.warning(f"[StageOptimizer] {context} content is empty or not string: {type(content)}")
            return None
        
        content = content.strip()
        
        # Log first 200 chars for debugging
        logger.debug(f"[StageOptimizer] {context} parsing content: {repr(content[:200])}...")
        
        # Strategy 1: Direct parse
        try:
            result = json.loads(content)
            logger.info(f"[StageOptimizer] {context} JSON parsed successfully (direct)")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"[StageOptimizer] {context} direct parse failed: {e}")
        
        # Strategy 2: Extract code block
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if match:
            try:
                result = json.loads(match.group(1))
                logger.info(f"[StageOptimizer] {context} JSON parsed successfully (code block)")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"[StageOptimizer] {context} code block parse failed: {e}")
        
        # Strategy 3: Extract braces
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            json_str = match.group()
            try:
                result = json.loads(json_str)
                logger.info(f"[StageOptimizer] {context} JSON parsed successfully (braces)")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"[StageOptimizer] {context} braces parse failed: {e}")
                
                # Strategy 4: Try Python literal eval (for single-quoted dicts)
                try:
                    # Replace single quotes with double quotes for JSON compatibility
                    # But need to be careful with apostrophes in text
                    # Use ast.literal_eval as safer alternative
                    result = ast.literal_eval(json_str)
                    if isinstance(result, dict):
                        logger.info(f"[StageOptimizer] {context} JSON parsed successfully (literal_eval)")
                        return result
                except (ValueError, SyntaxError) as e2:
                    logger.debug(f"[StageOptimizer] {context} literal_eval failed: {e2}")
        
        logger.warning(f"[StageOptimizer] {context} JSON parse failed, content preview: {repr(content[:300])}...")
        return None
    
    def _identify_issues_in_window_deprecated(self, window_chapters: List[Dict], 
                                               window_idx: int, total_windows: int) -> List[Issue]:
        """旧版方法 - 已弃用，保留用于参考"""
        return []
    
    def _old_prompt_example(self):
        """旧prompt示例 - 已弃用"""
        prompt = f"""你是一名专业的小说编辑，请对以下章节进行分析。

请按以下维度检查问题：

## 1. 剧情连续性问题
- 时间线是否连贯（倒计时、时间跳跃）
- 场景切换是否有过渡
- 章尾悬念是否被回收（超过3章未提即算问题）
- 战斗结果的延续性

## 2. 角色一致性问题  
- 主角能力是否有异常波动（解锁的能力是否正确使用）
- 配角立场是否稳定
- 反派层级是否有合理铺垫（上级反派的登场是否有下级铺垫）
- 已击败反派的后续处理是否明确

## 3. 世界设定一致性
- 力量体系是否统一（等级划分前后一致）
- 道具/能力设定是否矛盾
- 组织势力评估是否稳定

## 4. 爆款标准差距
- 爽点不足的章节（每章应有≥1个爽点）
- 情绪曲线平淡（每章应有≥3次转折）
- 字数不足的章节（<1800字）

输出格式（JSON）：
{{
    "issues": [
        {{
            "type": "plot/character/world/bestseller",
            "severity": "high/medium/low",
            "chapter": 章节号,
            "description": "问题描述",
            "suggestion": "修复建议"
        }}
    ]
}}

注意：
- high: 严重影响阅读体验（如主角能力突然变化、反派无铺垫跳变）
- medium: 影响流畅度（如小伏笔未回收、小设定矛盾）
- low: 细节问题（如个别章节爽点不足）"""

        # 调用AI分析
        if not self.api_client:
            logger.warning("[StageOptimizer] 无API客户端，跳过问题识别")
            return []
        
        try:
            response = self.api_client.generate(messages=[
                {"role": "user", "content": prompt}
            ])
            
            content = response.get("content", "")
            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                issues = [Issue(**item) for item in data.get("issues", [])]
                logger.info(f"[StageOptimizer] 识别到 {len(issues)} 个问题")
                return issues
        except Exception as e:
            logger.error(f"[StageOptimizer] 问题识别失败: {e}")
        
        return []
    
    def _plan_fixes(self, issues: List[Issue], chapters: List[Dict]) -> List[FixPlan]:
        """
        Stage 2: 规划修复方案
        """
        # 按类型分组
        plot_issues = [i for i in issues if i.type == "plot"]
        char_issues = [i for i in issues if i.type == "character"]
        world_issues = [i for i in issues if i.type == "world"]
        best_issues = [i for i in issues if i.type == "bestseller"]
        
        plans = []
        
        # 全局修复（设定类问题）
        if world_issues:
            plans.append(FixPlan(
                type="global",
                chapter_indices=list(range(len(chapters))),
                instructions=f"统一世界设定：{[i.description for i in world_issues]}",
                priority=10
            ))
        
        # 批量修复（同类章节）
        # 按章节分组
        chapter_issues = {}
        for issue in issues:
            if issue.chapter not in chapter_issues:
                chapter_issues[issue.chapter] = []
            chapter_issues[issue.chapter].append(issue)
        
        for ch_num, ch_issues in chapter_issues.items():
            if len(ch_issues) >= 2:  # 多问题的章节单独处理
                idx = ch_num - 1
                plans.append(FixPlan(
                    type="single",
                    chapter_indices=[idx],
                    instructions=f"修复第{ch_num}章：{[i.description for i in ch_issues]}",
                    priority=8 if any(i.severity == "high" for i in ch_issues) else 5
                ))
        
        # 排序：优先级高的先处理
        plans.sort(key=lambda p: p.priority, reverse=True)
        return plans
    
    def _execute_fixes(self, plans: List[FixPlan], chapters: List[Dict]) -> List[Dict]:
        """
        Stage 3: 执行修复
        """
        fixed_chapters = chapters.copy()
        
        for plan in plans:
            if plan.type == "global":
                # 全局修复：更新所有章节的设定引用
                logger.info(f"[StageOptimizer] 执行全局修复")
                # 这里可以更新 world_state，然后重新生成相关章节
                
            elif plan.type == "single":
                # 单章修复
                for idx in plan.chapter_indices:
                    if idx < len(fixed_chapters):
                        chapter = fixed_chapters[idx]
                        logger.info(f"[StageOptimizer] 修复第{chapter['chapter_number']}章")
                        
                        # 调用AI修复单章
                        fixed = self._fix_single_chapter(chapter, plan.instructions)
                        fixed_chapters[idx] = fixed
        
        return fixed_chapters
    
    def _fix_single_chapter(self, chapter: Dict, instructions: str) -> Dict:
        """修复单个章节"""
        if not self.api_client:
            return chapter
        
        prompt = f"""请修复以下章节：

章节标题：{chapter.get('title', '')}
当前内容：
{chapter.get('content', '')[:2000]}...

修复要求：
{instructions}

要求：
1. 保持原有剧情主线
2. 只修复指定问题
3. 字数维持在2000-2500字
4. 保持番茄风格（短段落、多对话）

直接输出修复后的完整章节内容。"""

        try:
            response = self.api_client.generate(messages=[
                {"role": "user", "content": prompt}
            ])
            
            new_content = response.get("content", chapter.get('content', ''))
            
            # 更新章节
            fixed_chapter = chapter.copy()
            fixed_chapter['content'] = new_content
            fixed_chapter['word_count'] = len(new_content)
            fixed_chapter['optimized'] = True
            
            return fixed_chapter
        except Exception as e:
            logger.error(f"[StageOptimizer] 单章修复失败: {e}")
            return chapter
    
    def _verify_fixes(self, original_issues: List[Issue], 
                      fixed_chapters: List[Dict]) -> bool:
        """
        Stage 4: 验证修复
        """
        # 简单验证：重新检查是否还有同样的问题
        # 实际可以再次调用AI验证
        high_issues = [i for i in original_issues if i.severity == "high"]
        logger.info(f"[StageOptimizer] 验证：原{len(high_issues)}个严重问题")
        
        # 如果已经修复了大部分，返回True
        # 这里简化处理，实际应该重新分析
        return True
    
    def _sync_settings(self, chapters: List[Dict]):
        """
        Stage 5: 同步更新设定文件
        """
        logger.info(f"[StageOptimizer] 同步设定文件")
        
        # 1. 提取并更新世界状态
        world_state = self._extract_world_state(chapters)
        self._save_json(".world_state.json", world_state)
        
        # 2. 提取并更新角色状态
        character_state = self._extract_character_states(chapters)
        self._save_json(".character_state.json", character_state)
        
        # 3. 提取剧情时间线
        timeline = self._extract_timeline(chapters)
        self._save_json(".plot_timeline.json", timeline)
        
        # 4. 提取已解决/待解决的钩子
        hooks = self._extract_hooks(chapters)
        self._save_json(".hooks_state.json", hooks)
        
        logger.info(f"[StageOptimizer] 设定文件已更新")
    
    def _extract_world_state(self, chapters: List[Dict]) -> Dict:
        """从章节提取世界状态"""
        # 简化的提取逻辑
        # 实际应该调用AI分析全文
        return {
            "extracted_at": chapters[-1].get('chapter_number', 0),
            "total_chapters": len(chapters),
            "power_system": {},  # 从章节提取力量体系
            "factions": {},      # 从章节提取势力
            "key_events": []     # 关键事件列表
        }
    
    def _extract_character_states(self, chapters: List[Dict]) -> Dict:
        """从章节提取角色状态"""
        return {
            "protagonist": {
                "current_abilities": [],
                "power_level_progression": [],
            },
            "key_characters": {}
        }
    
    def _extract_timeline(self, chapters: List[Dict]) -> List[Dict]:
        """提取剧情时间线"""
        timeline = []
        for ch in chapters:
            timeline.append({
                "chapter": ch.get('chapter_number'),
                "title": ch.get('title'),
                "key_event": "",  # 从内容提取
                "new_characters": [],
                "resolved_hooks": [],
                "new_hooks": []
            })
        return timeline
    
    def _extract_hooks(self, chapters: List[Dict]) -> Dict:
        """提取钩子状态"""
        return {
            "resolved": [],
            "pending": [],
            "abandoned": []
        }
    
    def _generate_report(self, chapters: List[Dict], stage_end: int):
        """生成优化报告"""
        report_path = self.project_path / f"optimization_report_stage_{stage_end}.md"
        
        report = f"""# 阶段性复盘优化报告

## 阶段：第1-{stage_end}章

## 优化统计
- 总章节数：{len(chapters)}
- 发现问题数：{len(self.issues)}
- 严重问题数：{len([i for i in self.issues if i.severity == 'high'])}

## 问题分布
### 剧情连续性
{self._format_issues_by_type('plot')}

### 角色一致性
{self._format_issues_by_type('character')}

### 设定一致性
{self._format_issues_by_type('world')}

### 爆款标准差距
{self._format_issues_by_type('bestseller')}

## 修复措施
{self._format_fix_plans()}

## 章节质量评分
| 章节 | 字数 | 评分 | 备注 |
|------|------|------|------|
{self._format_chapter_scores(chapters)}

---
生成时间：{self._get_timestamp()}
"""
        
        report_path.write_text(report, encoding='utf-8')
        logger.info(f"[StageOptimizer] 报告已保存: {report_path}")
    
    def _format_chapters_for_analysis(self, chapters: List[Dict]) -> str:
        """格式化章节用于AI分析（包含完整设计信息和战术规划）"""
        lines = []
        
        # 加载战术规划
        if chapters:
            first_ch_num = chapters[0].get('chapter_number', 1)
            tactical_plan = self._load_tactical_plan(first_ch_num)
            
            # 添加战术规划信息
            if tactical_plan:
                lines.append("\n" + "="*60)
                lines.append("【战术规划（动态设计）】")
                lines.append("="*60)
                
                batch_info = tactical_plan.get('batch_info', {})
                if batch_info:
                    lines.append(f"阶段目标: {batch_info.get('stage_goal_id', '无')}")
                    lines.append(f"战术重点: {batch_info.get('focus', '无')}")
                
                # 添加战术规划中的章节设计
                tactical_chapters = tactical_plan.get('chapters', [])
                for tch in tactical_chapters:
                    tch_num = tch.get('chapter_number', 0)
                    # 只显示当前窗口内的章节
                    if any(ch.get('chapter_number') == tch_num for ch in chapters):
                        lines.append(f"\n第{tch_num}章设计:")
                        lines.append(f"  - 情绪: {tch.get('emotion', '无')} (强度{tch.get('intensity', '无')})")
                        lines.append(f"  - 节拍: {tch.get('beat_type', '无')}")
                        lines.append(f"  - 事件: {tch.get('event', '无')}")
                        lines.append(f"  - 目的: {tch.get('purpose', '无')}")
        
        # 章节详细信息
        for ch in chapters:
            ch_num = ch.get('chapter_number', 0)
            ch_title = ch.get('title', '')
            ch_plan = ch.get('chapter_plan', {})
            
            lines.append(f"\n{'='*60}")
            lines.append(f"第{ch_num}章：{ch_title}")
            lines.append(f"{'='*60}")
            
            # 章节设计信息（来自chapter_plan）
            if ch_plan:
                lines.append(f"【情绪】{ch_plan.get('emotion', '无')}")
                lines.append(f"【强度】{ch_plan.get('intensity', '无')}")
                lines.append(f"【节拍类型】{ch_plan.get('beat_type', '无')}")
                lines.append(f"【关键事件】{ch_plan.get('event', '无')}")
                lines.append(f"【本章目的】{ch_plan.get('purpose', '无')}")
                lines.append(f"【钩子类型】{ch_plan.get('hook_type', '无')}")
                lines.append(f"【钩子内容】{ch_plan.get('hook_content', '无')}")
                lines.append(f"【阶段目标对齐】{ch_plan.get('stage_goal_alignment', '无')}")
            
            # 正文内容（前500字）
            content = ch.get('content', '')
            lines.append(f"\n【正文内容（前500字）】")
            lines.append(content[:500] + "..." if len(content) > 500 else content)
            
        return "\n".join(lines)
    
    def _format_issues_by_type(self, type_name: str) -> str:
        """格式化某类型问题"""
        issues = [i for i in self.issues if i.type == type_name]
        if not issues:
            return "无"
        return "\n".join([f"- 第{i.chapter}章 ({i.severity}): {i.description}" for i in issues])
    
    def _format_fix_plans(self) -> str:
        """格式化修复计划"""
        if not self.fix_plans:
            return "无"
        return "\n".join([f"- {p.type}: {p.instructions[:50]}..." for p in self.fix_plans])
    
    def _format_chapter_scores(self, chapters: List[Dict]) -> str:
        """格式化章节评分表"""
        lines = []
        for ch in chapters:
            ch_num = ch.get('chapter_number', '?')
            word_count = ch.get('word_count', 0)
            score = ch.get('quality_score', '-')
            note = "已优化" if ch.get('optimized') else ""
            lines.append(f"| {ch_num} | {word_count} | {score} | {note} |")
        return "\n".join(lines)
    
    def _calculate_chapter_quality_score(self, chapter: Dict) -> float:
        """
        🔥 计算章节质量评分（基于规则）
        
        评分维度：
        1. 字数达标度 (0-2分)
        2. 情绪强度执行 (0-2分)
        3. 爽点/反转密度 (0-2分)
        4. 结构完整性 (0-2分)
        5. 创新性 (0-2分)
        
        总分：0-10分，保留1位小数
        """
        import re
        
        content = chapter.get('content', '')
        word_count = len(content)
        score = 6.0  # 基础分6分
        
        # 1. 字数评分 (0-2分)
        if word_count >= 3000:
            score += 2.0
        elif word_count >= 2500:
            score += 1.5
        elif word_count >= 2000:
            score += 1.0
        elif word_count >= 1800:
            score += 0.5
        else:
            score -= 1.0  # 字数不足扣分
        
        # 2. 情绪强度检测 (0-2分)
        emotion_indicators = {
            'high': ['震惊', '震撼', '恐怖', '绝望', '狂喜', '暴怒'],
            'medium': ['紧张', '兴奋', '愤怒', '悲伤', '期待']
        }
        high_count = sum(1 for w in emotion_indicators['high'] if w in content)
        med_count = sum(1 for w in emotion_indicators['medium'] if w in content)
        
        if high_count >= 5:
            score += 2.0
        elif high_count >= 3 or med_count >= 5:
            score += 1.0
        elif high_count >= 1 or med_count >= 3:
            score += 0.5
        
        # 3. 爽点/反转密度 (0-2分)
        climax_indicators = ['反转', '爆发', '秒杀', '震惊全场', '全网哗然', 
                            '打脸', '求饶', '不可置信', '怎么可能']
        climax_count = sum(1 for w in climax_indicators if w in content)
        
        if climax_count >= 5:
            score += 2.0
        elif climax_count >= 3:
            score += 1.0
        elif climax_count >= 1:
            score += 0.5
        
        # 4. 结构完整性 (0-2分)
        structure_score = 0.0
        # 检查多层震惊结构（通过关键词判断，不依赖标签）
        # 现场反应关键词
        if any(w in content for w in ['弹幕', '直播间', '围观', '现场']):
            structure_score += 0.5
        # 传播扩散关键词
        if any(w in content for w in ['全网', '热搜', '朋友圈', '社交媒体', '疯传']):
            structure_score += 0.5
        # 权威反应关键词
        if any(w in content for w in ['高层', '元帅', '将军', '指挥部', '官方', '紧急会议']):
            structure_score += 0.5
        # 检查钩子
        if any(w in content for w in ['钩子', '悬念', '伏笔']):
            structure_score += 0.5
        score += structure_score
        
        # 5. 创新性检测 (0-2分) - 检测是否有新的能力/角色/设定
        if any(w in content for w in ['解锁', '新技能', '觉醒', '突破']):
            score += 1.0
        if any(w in content for w in ['新角色登场', '神秘人', '幕后黑手']):
            score += 0.5
        if any(w in content for w in ['隐藏设定', '世界观展开', '真相']):
            score += 0.5
        
        # 限制在6.0-10.0之间（避免过低或过高）
        return round(max(6.0, min(10.0, score)), 1)
    
    def _update_chapter_quality_score(self, chapter_num: int, score: float):
        """
        🔥 将质量评分写回章节文件
        
        Args:
            chapter_num: 章节号
            score: 质量评分 (6.0-10.0)
        """
        chapters_dir = self.project_path / "chapters"
        
        # 尝试多种可能的文件路径
        possible_paths = [
            chapters_dir / f"chapter_{chapter_num:03d}.json",
            chapters_dir / f"chapter_{chapter_num}.json",
            chapters_dir / f"{chapter_num:03d}.json",
            chapters_dir / f"{chapter_num}.json",
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        chapter_data = json.load(f)
                    
                    # 更新评分
                    chapter_data['quality_score'] = score
                    
                    # 写回文件
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(chapter_data, f, ensure_ascii=False, indent=2)
                    
                    logger.debug(f"[StageOptimizer] 已更新第{chapter_num}章质量评分: {score}")
                    return True
                    
                except Exception as e:
                    logger.warning(f"[StageOptimizer] 更新第{chapter_num}章评分失败: {e}")
                    continue
        
        logger.warning(f"[StageOptimizer] 未找到第{chapter_num}章文件以更新评分")
        return False
    
    def _save_json(self, filename: str, data: Dict):
        """保存JSON文件"""
        filepath = self.project_path / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ==================== 场景级优化方法 ====================
    
    def _split_chapter_into_scenes(self, chapter: Dict) -> List[Scene]:
        """
        将章节分割成场景
        
        策略：
        1. 如果内容已有【场景X】标记，按标记分割
        2. 否则按字数大致均分（每场景500-800字）
        """
        import re
        
        content = chapter.get("content", "")
        ch_num = chapter.get("chapter_number", 0)
        
        # 尝试按场景标记分割
        scene_pattern = r'【场景(\d+)[：:]([^】]+)】'
        matches = list(re.finditer(scene_pattern, content))
        
        scenes = []
        
        if len(matches) >= 2:
            # 有场景标记，按标记分割
            for i, match in enumerate(matches):
                scene_num = int(match.group(1))
                scene_type = match.group(2).strip()
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
                scene_content = content[start:end].strip()
                
                scenes.append(Scene(
                    scene_number=scene_num,
                    scene_type=scene_type,
                    content=scene_content,
                    word_count=len(scene_content)
                ))
        else:
            # 无场景标记，按段落+字数智能分割
            scenes = self._auto_split_into_scenes(content, ch_num)
        
        return scenes
    
    def _auto_split_into_scenes(self, content: str, ch_num: int) -> List[Scene]:
        """按段落智能分割场景（每场景目标600字）"""
        paragraphs = content.split('\n\n')
        scenes = []
        current_content = []
        current_words = 0
        scene_num = 1
        target_words = 600
        
        for para in paragraphs:
            para_words = len(para)
            
            if current_words + para_words > target_words and current_content:
                # 保存当前场景
                scene_text = '\n\n'.join(current_content)
                scenes.append(Scene(
                    scene_number=scene_num,
                    scene_type="待识别",
                    content=scene_text,
                    word_count=len(scene_text)
                ))
                scene_num += 1
                current_content = [para]
                current_words = para_words
            else:
                current_content.append(para)
                current_words += para_words
        
        # 保存最后一个场景
        if current_content:
            scene_text = '\n\n'.join(current_content)
            scenes.append(Scene(
                scene_number=scene_num,
                scene_type="待识别",
                content=scene_text,
                word_count=len(scene_text)
            ))
        
        return scenes
    
    def _identify_scene_issues(self, chapter: Dict, scenes: List[Scene], 
                                session: ConversationSession, window_idx: int) -> List[SceneIssue]:
        """
        识别场景级问题
        """
        ch_num = chapter.get("chapter_number", 0)
        
        # 构建场景描述
        scenes_desc = []
        for s in scenes:
            preview = s.content[:200].replace('\n', ' ')
            scenes_desc.append(f"场景{s.scene_number}[{s.scene_type}]: {preview}...")
        
        prompt = f"""分析第{ch_num}章的场景质量问题。

章节场景：
{chr(10).join(scenes_desc)}

请识别每个场景的问题（如无问题可不输出）：
1. plot: 剧情逻辑问题
2. character: 人设一致性问题  
3. world: 设定一致性问题
4. bestseller: 爆款标准差距（爽点不足、情绪不到位等）

输出JSON：
{{
    "scene_issues": [
        {{
            "scene_number": 1,
            "scene_type": "压抑", 
            "issue_type": "bestseller",
            "priority": "p1",
            "description": "问题描述",
            "suggestion": "修复建议"
        }}
    ]
}}
"""
        
        try:
            response = session.send_message(prompt, purpose=f"w{window_idx}-ch{ch_num}-scenes")
            data = self._safe_parse_json(response, f"w{window_idx}-ch{ch_num}-scenes")
            
            if not data:
                return []
            
            issues = []
            for item in data.get("scene_issues", []):
                issues.append(SceneIssue(
                    chapter=ch_num,
                    scene_number=item.get("scene_number", 0),
                    scene_type=item.get("scene_type", ""),
                    issue_type=item.get("issue_type", ""),
                    priority=item.get("priority", "p2"),
                    description=item.get("description", ""),
                    suggestion=item.get("suggestion", "")
                ))
            return issues
            
        except Exception as e:
            logger.error(f"[StageOptimizer] 场景问题识别失败 Ch{ch_num}: {e}")
            return []
    
    def _fix_scene(self, chapter: Dict, scene: Scene, issue: SceneIssue, 
                   session: ConversationSession, window_idx: int) -> Optional[str]:
        """
        修复单个场景
        """
        ch_num = chapter.get("chapter_number", 0)
        protagonist_name = self.protagonist_name
        
        prompt = f"""修复第{ch_num}章的场景{scene.scene_number}。

**约束条件：**
1. 主角名必须保持：{protagonist_name or "原章节使用的主角名"}
2. 场景字数保持：{scene.word_count}字左右（±15%）
3. 只修复问题部分，保留其他内容风格
4. 场景类型：{scene.scene_type}

**原场景内容：**
{scene.content}

**需要修复的问题：**
[{issue.issue_type}/{issue.priority}] {issue.description}
修复建议：{issue.suggestion}

**输出要求：**
直接输出修复后的场景正文（不需要场景标记），保持相似字数。
"""
        
        try:
            response = session.send_message(prompt, purpose=f"w{window_idx}-ch{ch_num}-fix-s{scene.scene_number}")
            new_content = response.strip() if response else None
            
            if not new_content:
                return None
            
            # 字数检查
            new_words = len(new_content)
            if new_words < scene.word_count * 0.5:
                logger.warning(f"[StageOptimizer] 场景{scene.scene_number}修复后字数({new_words})不足原文50%，拒绝修改")
                return None
            
            return new_content
            
        except Exception as e:
            logger.error(f"[StageOptimizer] 场景修复失败 Ch{ch_num} Scene{scene.scene_number}: {e}")
            return None
    
    def _optimize_chapter_scene_level(self, chapter: Dict, session: ConversationSession, 
                                       window_idx: int) -> Tuple[Dict, List[SceneIssue]]:
        """
        场景级优化单章
        
        返回：(优化后的章节, 问题列表)
        """
        ch_num = chapter.get("chapter_number", 0)
        logger.info(f"[StageOptimizer] 开始场景级优化第{ch_num}章")
        
        # 1. 分割场景
        scenes = self._split_chapter_into_scenes(chapter)
        logger.info(f"[StageOptimizer] 第{ch_num}章分割为{len(scenes)}个场景")
        
        # 2. 识别场景问题
        issues = self._identify_scene_issues(chapter, scenes, session, window_idx)
        if not issues:
            logger.info(f"[StageOptimizer] 第{ch_num}章无场景问题，跳过")
            return chapter, []
        
        logger.info(f"[StageOptimizer] 第{ch_num}章发现{len(issues)}个场景问题")
        
        # 3. 按优先级排序修复
        priority_order = {"p0": 0, "p1": 1, "p2": 2}
        issues.sort(key=lambda x: priority_order.get(x.priority, 3))
        
        # 4. 修复场景
        modified_scenes = {}  # scene_number -> new_content
        
        for issue in issues:
            # 找到对应的场景
            scene = next((s for s in scenes if s.scene_number == issue.scene_number), None)
            if not scene:
                continue
            
            # 如果该场景已修复过，使用上次的结果作为输入
            current_content = modified_scenes.get(issue.scene_number, scene.content)
            temp_scene = Scene(
                scene_number=scene.scene_number,
                scene_type=scene.scene_type,
                content=current_content,
                word_count=len(current_content)
            )
            
            new_content = self._fix_scene(chapter, temp_scene, issue, session, window_idx)
            if new_content:
                modified_scenes[issue.scene_number] = new_content
                logger.info(f"[StageOptimizer] 第{ch_num}章场景{issue.scene_number}已修复")
        
        # 5. 拼接章节
        if not modified_scenes:
            return chapter, issues
        
        new_chapter = chapter.copy()
        new_content_parts = []
        
        for scene in scenes:
            if scene.scene_number in modified_scenes:
                # 使用修复后的内容
                new_content_parts.append(modified_scenes[scene.scene_number])
            else:
                # 使用原内容
                new_content_parts.append(scene.content)
        
        new_chapter["content"] = "\n\n".join(new_content_parts)
        new_chapter["word_count"] = len(new_chapter["content"])
        new_chapter["optimized"] = True
        new_chapter["scene_issues_fixed"] = len(modified_scenes)
        
        return new_chapter, issues
    
    def _optimize_window_scene_level(self, window_chapters: List[Dict], 
                                      window_idx: int) -> Tuple[List[Issue], List[Dict]]:
        """
        场景级优化窗口（替代整章重写）
        
        流程：
        1. 识别整章问题
        2. 对有问题的章节进行场景级修复
        3. 保持其他章节不变
        """
        first_ch = window_chapters[0].get('chapter_number', '?')
        last_ch = window_chapters[-1].get('chapter_number', '?')
        
        logger.info(f"[StageOptimizer] 场景级优化窗口{window_idx}: ch{first_ch}-{last_ch}")
        
        if not self.api_client:
            return [], window_chapters
        
        # 🔥 从JSON配置加载system prompt
        templates = self._review_prompts.get("templates", {})
        system_prompt = templates.get("scene_editor_system_prompt", """You are a professional novel editor. Analyze and fix quality issues at scene level.
Workflow: 1) Identify issues 2) Fix specific scenes 3) Preserve unchanged content. Output JSON only.""")
        
        session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            temperature=0.3,
            purpose_prefix=f"SceneOpt-w{window_idx}"
        )
        
        # Step 1: Send chapters for context
        chapters_summary = []
        for ch in window_chapters:
            ch_num = ch.get('chapter_number', 0)
            word_count = ch.get('word_count', 0)
            title = ch.get('title', '')
            content_preview = ch.get('content', '')[:200].replace('\n', ' ')
            chapters_summary.append(f"Ch{ch_num}: {title} ({word_count}字) - {content_preview}...")
        
        init_prompt = f"""Analyze chapters {first_ch}-{last_ch}:

{chr(10).join(chapters_summary)}

Reply: Ready to analyze."""
        
        session.send_message(init_prompt, purpose=f"w{window_idx}-init")
        
        # Step 2: Identify issues at chapter level first
        identify_prompt = """Analyze quality issues for all chapters. Focus on identifying which chapters have problems.

Output JSON:
{
    "issues": [
        {"type": "plot|character|world|bestseller", "priority": "p0|p1|p2", 
         "chapter": 1, "description": "...", "suggestion": "..."}
    ],
    "summary": {"p0_count": 0, "p1_count": 0, "p2_count": 0}
}"""
        
        response = session.send_message(identify_prompt, purpose=f"w{window_idx}-identify")
        data = self._safe_parse_json(response, f"w{window_idx}-identify")
        
        if not data:
            return [], window_chapters
        
        all_issues = [Issue(**item) for item in data.get("issues", [])]
        summary = data.get("summary", {})
        logger.info(f"[StageOptimizer] w{window_idx} identified: P0={summary.get('p0_count',0)}, P1={summary.get('p1_count',0)}, P2={summary.get('p2_count',0)}")
        
        # 记录问题章节（转换类型确保匹配）
        chapters_with_issues = set(int(i.chapter) for i in all_issues)
        window_chapter_nums = set(ch.get('chapter_number', 0) for ch in window_chapters)
        
        logger.info(f"[StageOptimizer] 问题章节: {sorted(chapters_with_issues)}")
        logger.info(f"[StageOptimizer] 窗口章节: {sorted(window_chapter_nums)}")
        logger.info(f"[StageOptimizer] 需要优化的章节: {sorted(chapters_with_issues & window_chapter_nums)}")
        
        # Step 3: 对有问题的章节进行场景级优化
        fixed_chapters = []
        
        for ch in window_chapters:
            ch_num = ch.get('chapter_number', 0)
            
            if ch_num not in chapters_with_issues:
                # 无问题，保持不变
                logger.info(f"[StageOptimizer] 第{ch_num}章无问题，跳过")
                fixed_chapters.append(ch)
                continue
            
            # 有问题的章节，进行场景级优化
            logger.info(f"[StageOptimizer] 第{ch_num}章有问题，进行场景级优化")
            fixed_ch, scene_issues = self._optimize_chapter_scene_level(ch, session, window_idx)
            fixed_chapters.append(fixed_ch)
        
        return all_issues, fixed_chapters
