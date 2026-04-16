"""
Hierarchical Planner
分层规划管理器

新架构：
- WorldBuilder: 构建世界观+阶段目标（不绑定章数）
- TacticalPlanner: 每30章滚动规划（基于前序总结+阶段目标）
- BatchSummarizer: 每轮生成后总结（用于下一轮规划）
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# 先定义logger
logger = logging.getLogger(__name__)

from .world_builder import WorldBuilder
from .tactical_planner import TacticalPlanner
from .batch_summarizer import BatchSummarizer
from .sliding_window_monitor import SlidingWindowMonitor
from .config import get_config

# 🔥 导入番茄爆款细纲会话（三轮对话）
try:
    from .tomato_tactical_session import (
        TomatoBestsellerTacticalSession,
        create_tactical_session
    )
    HAS_TOMATO_TACTICAL = True
    logger.info("[HierarchicalPlanner] 已加载番茄爆款细纲会话")
except ImportError as e:
    HAS_TOMATO_TACTICAL = False
    logger.warning(f"[HierarchicalPlanner] 番茄爆款细纲会话未加载: {e}")


class HierarchicalPlanner:
    """
    分层规划管理器（新架构）
    
    架构：
    - WorldBuilder: 构建世界观+阶段目标
    - TacticalPlanner: 每30章滚动规划（基于前序总结）
    - BatchSummarizer: 每轮生成后总结
    
    特点：
    1. 阶段目标不绑定具体章数
    2. 每轮基于前序总结动态调整
    3. 自动追踪阶段目标完成度
    """
    
    def __init__(
        self,
        genre: str,
        novel_title: str,
        protagonist_name: str,
        api_client=None,
        project_path: Path = None,
        total_chapters: int = None,
        target_words: int = None,
        emotion_curve: List[Dict] = None,       # ← 新增：一阶段情绪曲线
        bestseller_analysis: Dict = None,        # ← 新增：爆款分析数据
        use_tomato_tactical: bool = True        # 🔥 新增：是否使用番茄爆款细纲会话
    ):
        """
        初始化分层规划器
        
        Args:
            genre: 题材
            novel_title: 书名
            protagonist_name: 主角名
            api_client: API客户端
            project_path: 项目路径
            total_chapters: 总章节数
            target_words: 目标字数
            emotion_curve: 一阶段生成的200章情绪曲线（用于确保战术规划符合爆款设计）
            bestseller_analysis: 爆款分析数据（钩子公式、爽点模式等）
            use_tomato_tactical: 是否使用番茄爆款细纲会话（三轮对话：设定+情绪+角色）
        """
        self.genre = genre
        self.novel_title = novel_title
        self.protagonist_name = protagonist_name
        self.api_client = api_client
        self.project_path = project_path
        self.emotion_curve = emotion_curve       # 存储一阶段情绪曲线
        self.bestseller_analysis = bestseller_analysis  # 存储爆款分析
        self.use_tomato_tactical = use_tomato_tactical and HAS_TOMATO_TACTICAL  # 是否使用番茄细纲会话
        
        # 加载配置
        config = get_config(genre)
        self.total_chapters = total_chapters or config["chapters"]
        self.target_words = target_words or config["target_words"]
        self.tactical_window = config["planning"]["tactical_window"]
        
        # 初始化组件
        self.world_builder = WorldBuilder(api_client)
        self.tactical_planner = TacticalPlanner(api_client, project_path)
        
        # 🔥 初始化滑动窗口监控器（用于实时监控质量趋势）
        self.window_monitor = SlidingWindowMonitor(window_size=6)
        
        # 🔥 analytics_service将在需要时延迟初始化
        self._analytics_service = None
        
        # 状态
        self.world_setting = None        # 世界观设定
        self.stage_goals = []            # 阶段目标列表
        self.current_stage_index = 0     # 当前阶段索引
        self.current_batch_summary = None  # 当前批次总结
        self.generated_chapters_count = 0
        
        logger.info(f"[HierarchicalPlanner] 初始化: {novel_title}")
        if emotion_curve:
            logger.info(f"[HierarchicalPlanner] 已加载一阶段情绪曲线: {len(emotion_curve)}章")
        if bestseller_analysis:
            logger.info(f"[HierarchicalPlanner] 已加载爆款分析数据")
        
        # 🔥 尝试加载上次的批次总结
        self._load_last_batch_summary()
    
    def _load_last_batch_summary(self):
        """从文件加载上次的批次总结"""
        if not self.project_path:
            return
        
        try:
            # 尝试加载最新总结
            latest_path = self.project_path / "batch_summary_latest.json"
            if latest_path.exists():
                with open(latest_path, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                
                self.current_batch_summary = summary_data.get('summary', {})
                stats = summary_data.get('statistics', {})
                self.generated_chapters_count = stats.get('total_generated', 0)
                
                logger.info(f"[HierarchicalPlanner] 已加载上次总结: "
                           f"第{self.current_batch_summary.get('batch_range', '未知')}章, "
                           f"已生成{self.generated_chapters_count}章")
                return
            
            # 如果没有 latest，尝试找到最新的 batch_summary_xxx.json
            summary_dir = self.project_path / "batch_summaries"
            if summary_dir.exists():
                summary_files = sorted(summary_dir.glob("batch_summary_*.json"))
                if summary_files:
                    latest_file = summary_files[-1]  # 最新的文件
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                    
                    self.current_batch_summary = summary_data.get('summary', {})
                    stats = summary_data.get('statistics', {})
                    self.generated_chapters_count = stats.get('total_generated', 0)
                    
                    logger.info(f"[HierarchicalPlanner] 已加载历史总结: {latest_file.name}")
                    return
            
            logger.info("[HierarchicalPlanner] 没有找到历史总结，将从头开始")
            
        except Exception as e:
            logger.error(f"[HierarchicalPlanner] 加载历史总结失败: {e}")
    
    def _get_sub_theme(self) -> Optional[str]:
        """获取子主题配置：优先从 project_info.json 读取，否则根据 genre 推断"""
        try:
            if self.project_path:
                project_info_path = self.project_path / "project_info.json"
                if project_info_path.exists():
                    with open(project_info_path, "r", encoding="utf-8") as f:
                        info = json.load(f)
                    sub_theme = info.get("sub_theme")
                    if sub_theme:
                        logger.info(f"[HierarchicalPlanner] 使用子主题: {sub_theme}")
                        return sub_theme
        except Exception as e:
            logger.warning(f"[HierarchicalPlanner] 读取子主题失败: {e}")
        
        # 根据 genre 推断默认值
        genre_sub_theme_map = {
            "god-tier": "spending_rebate",
            "god-tier-investment": "investment_guru",
            "god-tier-livestream": "livestream_tycoon",
            "god-tier-checkin": "daily_checkin",
            "sign-in-daily": "daily_checkin",
        }
        sub_theme = genre_sub_theme_map.get(self.genre)
        if sub_theme:
            logger.info(f"[HierarchicalPlanner] 根据题材推断子主题: {sub_theme}")
            return sub_theme
        
        return None
    
    def initialize(self, existing_world_setting: Dict = None):
        """
        初始化世界观和阶段目标（只执行一次）
        
        Args:
            existing_world_setting: 传入已有的一阶段产物（如对话模式生成的），避免重复生成
        """
        logger.info("[HierarchicalPlanner] 初始化世界观...")
        
        # 🔥 修复：如果传入已有的一阶段产物，直接使用，不再调用 WorldBuilder
        if existing_world_setting:
            logger.info("[HierarchicalPlanner] 使用已有的一阶段产物（对话模式生成），跳过 WorldBuilder 调用")
            self.world_setting = existing_world_setting
            self.stage_goals = existing_world_setting.get('stage_goals', [])
            # 同时更新 total_chapters（如果一阶段产物中有）
            if 'total_chapters' in existing_world_setting:
                self.total_chapters = existing_world_setting['total_chapters']
        else:
            # 没有传入一阶段产物，调用 WorldBuilder 生成
            logger.info("[HierarchicalPlanner] 未传入一阶段产物，调用 WorldBuilder 生成")
            self.world_setting = self.world_builder.build_world_setting(
                genre=self.genre,
                novel_title=self.novel_title,
                protagonist_name=self.protagonist_name,
                total_chapters=self.total_chapters,
                target_words=self.target_words
            )
            self.stage_goals = self.world_setting.get('stage_goals', [])
        
        logger.info(f"[HierarchicalPlanner] 世界观初始化完成 | 阶段目标: {len(self.stage_goals)}个")
        for i, goal in enumerate(self.stage_goals):
            logger.info(f"  阶段{i+1}: {goal.get('description', '无')[:50]}...")
        
        return self.world_setting
    
    def get_next_batch_plan(self, batch_size: int = 6) -> Tuple[Dict, Dict]:
        """
        获取下一批次的规划
        
        Args:
            batch_size: 批次大小（默认6章）
            
            Returns:
            (batch_plan, strategic_context)
            batch_plan: 本批次详细规划
            strategic_context: 战略上下文（包含世界观、阶段目标等）
        """
        # 确保已初始化
        if not self.world_setting:
            self.initialize()
        
        start_ch = self.generated_chapters_count + 1
        end_ch = min(start_ch + batch_size - 1, self.total_chapters)
        
        # 检查是否需要新的战术规划（每30章或首次）
        need_new_tactical = (
            self.current_batch_summary is None or  # 首次
            (start_ch - 1) % self.tactical_window == 0  # 每30章
        )
        
        if need_new_tactical:
            logger.info(f"[HierarchicalPlanner] 规划第{start_ch}-{start_ch + self.tactical_window - 1}章战术...")
            
            # 🔥 判断是否使用番茄爆款细纲会话（三轮对话）
            if self.use_tomato_tactical:
                logger.info("[HierarchicalPlanner] 使用番茄爆款细纲会话（三轮：设定+情绪+角色）")
                tactical_plan = self._generate_tomato_tactical_plan(start_ch)
            else:
                logger.info("[HierarchicalPlanner] 使用传统战术规划")
                # 获取当前阶段目标
                current_goal = self._get_current_stage_goal()
                
                # 生成战术规划（基于前序总结+阶段目标+一阶段爆款设计）
                tactical_plan = self.tactical_planner.plan_next_batch(
                    start_chapter=start_ch,
                    end_chapter=min(start_ch + self.tactical_window - 1, self.total_chapters),
                    novel_title=self.novel_title,
                    protagonist_name=self.protagonist_name,
                    stage_goal=current_goal,
                    previous_summary=self.current_batch_summary,
                    emotion_curve=self.emotion_curve,              # 传入一阶段情绪曲线
                    bestseller_analysis=self.bestseller_analysis   # 传入爆款分析数据
                )
            
            # 保存战术规划到文件
            self._save_tactical_plan(tactical_plan, start_ch)
        else:
            # 复用现有战术规划
            tactical_plan = self._load_tactical_plan(start_ch)
            # 🔥 修复：如果加载的规划为空或缺少 chapters，强制重新生成（兼容 continue-chapters 等场景）
            if not tactical_plan.get("chapters"):
                logger.warning(f"[HierarchicalPlanner] 已保存的战术规划为空（第{start_ch}章起），强制重新生成")
                if self.use_tomato_tactical:
                    logger.info("[HierarchicalPlanner] 使用番茄爆款细纲会话重新生成")
                    tactical_plan = self._generate_tomato_tactical_plan(start_ch)
                else:
                    logger.info("[HierarchicalPlanner] 使用传统战术规划重新生成")
                    current_goal = self._get_current_stage_goal()
                    tactical_plan = self.tactical_planner.plan_next_batch(
                        start_chapter=start_ch,
                        end_chapter=min(start_ch + self.tactical_window - 1, self.total_chapters),
                        novel_title=self.novel_title,
                        protagonist_name=self.protagonist_name,
                        stage_goal=current_goal,
                        previous_summary=self.current_batch_summary,
                        emotion_curve=self.emotion_curve,
                        bestseller_analysis=self.bestseller_analysis
                    )
                self._save_tactical_plan(tactical_plan, start_ch)
        
        # 提取当前批次
        batch_plan = self._extract_batch_plan(tactical_plan, start_ch, end_ch)
        
        # 🔥 构建战略上下文（包含一阶段爆款设计）
        strategic_context = {
            "world_setting": self.world_setting.get('world_setting', {}),
            "characters": self.world_setting.get('characters', {}),
            "current_stage_goal": self._get_current_stage_goal(),
            "stage_progress": self._get_stage_progress(),
            "emotion_curve": self.emotion_curve,              # 传递一阶段情绪曲线
            "bestseller_analysis": self.bestseller_analysis   # 传递爆款分析数据
        }
        
        return batch_plan, strategic_context
    
    def _get_current_stage_goal(self) -> Dict:
        """获取当前阶段目标"""
        if not self.stage_goals:
            return {}
        
        if self.current_stage_index >= len(self.stage_goals):
            return self.stage_goals[-1]  # 返回最后一个
        
        return self.stage_goals[self.current_stage_index]
    
    def _get_stage_progress(self) -> Dict:
        """获取各阶段进度"""
        if not self.current_batch_summary:
            return {}
        
        return self.current_batch_summary.get('goal_progress', {})
    
    def _generate_tomato_tactical_plan(self, start_ch: int) -> Dict:
        """
        🔥 使用番茄爆款细纲会话生成战术规划（三轮对话）
        
        三轮：
        1. 核心设定对齐（世界观+金手指+主角人设）
        2. 情绪爽点规划（情绪曲线+钩子+爽点）
        3. 角色出场规划（已有角色+新增角色）
        
        Args:
            start_ch: 开始章节
            
        Returns:
            Dict: 完整战术蓝图
        """
        if not HAS_TOMATO_TACTICAL:
            logger.error("[HierarchicalPlanner] 番茄细纲会话不可用，回退到传统规划")
            raise RuntimeError("TomatoBestsellerTacticalSession not available")
        
        try:
            # 创建细纲会话
            # 🔥 读取子主题配置
            sub_theme = self._get_sub_theme()
            
            session = create_tactical_session(
                project_path=self.project_path,
                api_client=self.api_client,
                start_chapter=start_ch,
                end_chapter=min(start_ch + self.tactical_window - 1, self.total_chapters),
                novel_title=self.novel_title,
                emotion_curve=self.emotion_curve,
                sub_theme=sub_theme
            )
            
            # 执行三轮对话，生成完整蓝图
            blueprint = session.generate_blueprint()
            
            logger.info(f"[HierarchicalPlanner] 番茄细纲会话完成: {session.session_id}")
            logger.info(f"  - 规划章节: {blueprint.get('summary', {}).get('total_chapters', 0)}章")
            logger.info(f"  - 爽点数量: {blueprint.get('summary', {}).get('total_satisfaction_points', 0)}个")
            logger.info(f"  - 新角色: {blueprint.get('summary', {}).get('new_characters_introduced', 0)}个")
            
            return blueprint
            
        except Exception as e:
            logger.error(f"[HierarchicalPlanner] 番茄细纲会话失败: {e}")
            raise
    
    def _extract_batch_plan(self, tactical_plan: Dict, start: int, end: int) -> Dict:
        """从战术规划中提取指定批次"""
        all_chapters = tactical_plan.get("chapters", [])
        batch_chapters = []
        
        for ch in all_chapters:
            if not isinstance(ch, dict):
                continue
            ch_num = ch.get("chapter_number", 0)
            try:
                ch_num_int = int(ch_num) if ch_num else 0
            except (ValueError, TypeError):
                continue
            
            if start <= ch_num_int <= end:
                batch_chapters.append(ch)
        
        return {
            "batch_info": {
                "start_chapter": start,
                "end_chapter": end,
                "stage_goal_id": self._get_current_stage_goal().get('goal_id', 'G1')
            },
            "chapters": batch_chapters,
            "stage_goal": self._get_current_stage_goal()  # 包含阶段目标
        }
    
    def _save_tactical_plan(self, tactical_plan: Dict, start_chapter: int):
        """保存战术规划到文件"""
        if not self.project_path:
            logger.warning("[HierarchicalPlanner] project_path 为空，无法保存战术规划")
            return
        
        try:
            import json
            # 确保目录存在
            self.project_path.mkdir(parents=True, exist_ok=True)
            
            # 使用非隐藏文件名（Windows兼容性）
            # 🔥 按 tactical_window 对齐窗口起始，确保 BatchGenerator 能正确读取
            aligned_start = ((start_chapter - 1) // self.tactical_window) * self.tactical_window + 1
            tactical_plan_path = self.project_path / f"tactical_plan_{aligned_start}.json"
            with open(tactical_plan_path, 'w', encoding='utf-8') as f:
                json.dump(tactical_plan, f, ensure_ascii=False, indent=2)
            logger.info(f"[HierarchicalPlanner] 战术规划已保存: {tactical_plan_path}")
        except Exception as e:
            logger.error(f"[HierarchicalPlanner] 保存战术规划失败: {e}", exc_info=True)
    
    def _load_tactical_plan(self, start_chapter: int) -> Dict:
        """从文件加载战术规划
        
        Args:
            start_chapter: 当前批次的起始章节号
            
        Returns:
            战术规划字典
        """
        if not self.project_path:
            return self._get_default_tactical_plan()
        
        try:
            import json
            
            # 计算该章节所属的战术规划窗口起始章节
            # 例如：第199章属于第181-200窗口，应加载 tactical_plan_181.json
            window_start = ((start_chapter - 1) // self.tactical_window) * self.tactical_window + 1
            
            # 优先尝试新文件名格式（非隐藏文件）
            tactical_plan_path = self.project_path / f"tactical_plan_{window_start}.json"
            
            # 兼容旧格式（隐藏文件）
            if not tactical_plan_path.exists():
                tactical_plan_path = self.project_path / f".tactical_plan_{window_start}.json"
            
            if tactical_plan_path.exists():
                with open(tactical_plan_path, 'r', encoding='utf-8') as f:
                    tactical_plan = json.load(f)
                logger.info(f"[HierarchicalPlanner] 战术规划已加载: {tactical_plan_path} (窗口起始: {window_start})")
                return tactical_plan
            else:
                logger.warning(f"[HierarchicalPlanner] 战术规划文件不存在: {tactical_plan_path} (窗口起始: {window_start}, 当前章节: {start_chapter})")
        except Exception as e:
            logger.error(f"[HierarchicalPlanner] 加载战术规划失败: {e}", exc_info=True)
        
        return self._get_default_tactical_plan()
    
    def _get_default_tactical_plan(self) -> Dict:
        """获取默认战术规划（当没有保存的规划时）"""
        current_goal = self._get_current_stage_goal()
        return {
            "chapters": [],
            "batch_info": {
                "stage_goal_id": current_goal.get('goal_id', 'G1')
            }
        }
    
    def update_progress(self, generated_chapters: List[Dict]):
        """
        更新生成进度
        
        Args:
            generated_chapters: 已生成的章节列表
        """
        if not generated_chapters:
            return
        
        count = len(generated_chapters)
        self.generated_chapters_count += count
        
        # 🔥 初始化BatchSummarizer（延迟初始化，确保analytics_service可用）
        if not hasattr(self, 'batch_summarizer') or self.batch_summarizer is None:
            self.batch_summarizer = BatchSummarizer(
                api_client=self.api_client,
                analytics_service=self._get_analytics_service()
            )
        
        # 🔥 滑动窗口质量监控
        for ch in generated_chapters:
            ch_num = ch.get('chapter_number') or ch.get('chapter') or 0
            
            # 获取章节质量指标（如果analytics_service可用）
            if self._analytics_service:
                metrics = self._analytics_service.analyze_chapter(ch_num)
                if metrics:
                    chapter_plan = ch.get('chapter_plan', {})
                    planned_emotion = chapter_plan.get('emotion', '未知')
                    
                    # 添加到滑动窗口
                    window_result = self.window_monitor.add_chapter(
                        ch_num,
                        {
                            'tomato_score': metrics.get('tomato_score', 0),
                            'dialogue_ratio': metrics.get('dialogue_ratio', 0),
                            'shuang_density': metrics.get('shuang_density', 0),
                            'emotion_density': metrics.get('emotion_density', 0)
                        },
                        planned_emotion
                    )
                    
                    # 如果触发告警，记录日志（仅分析，不自动修复）
                    if window_result.get('alert'):
                        logger.warning(
                            f"[HierarchicalPlanner] 质量告警: {window_result.get('alert_type')} - "
                            f"{window_result.get('message')}"
                        )
                        # 注意：此处仅记录告警，不触发自动修复
                        # 修复决策由用户在UI中手动确认后执行
        
        # 生成批次总结
        current_goal = self._get_current_stage_goal()
        new_summary = self.batch_summarizer.summarize_batch(
            chapters=generated_chapters,
            stage_goal=current_goal,
            previous_summary=self.current_batch_summary
        )
        
        # 合并总结（累积多批次信息）
        if self.current_batch_summary:
            self.current_batch_summary = self.batch_summarizer.merge_summaries(
                self.current_batch_summary,
                new_summary
            )
        else:
            self.current_batch_summary = new_summary
        
        # 检查阶段目标是否完成
        self._check_stage_completion()
        
        # 更新战术规划器的记录
        self.tactical_planner.update_generated_chapters(generated_chapters)
        
        # 🔥 保存批次总结报告到文件
        self._save_batch_summary(generated_chapters)
        
        logger.info(f"[HierarchicalPlanner] 进度更新: {self.generated_chapters_count}/{self.total_chapters}章")
    
    def _save_batch_summary(self, generated_chapters: List[Dict]):
        """
        保存批次总结报告到文件（JSON + Markdown双格式）
        
        Args:
            generated_chapters: 本次生成的章节列表
        """
        if not self.project_path or not generated_chapters:
            return
        
        try:
            import json
            from datetime import datetime
            
            # 计算批次信息（兼容两种字段名）
            batch_chapters = []
            for c in generated_chapters:
                ch_num = c.get('chapter_number') or c.get('chapter') or 0
                if ch_num:
                    batch_chapters.append(ch_num)
            
            start_ch = min(batch_chapters) if batch_chapters else 0
            end_ch = max(batch_chapters) if batch_chapters else 0
            
            # 构建总结报告
            summary_report = {
                "batch_info": {
                    "start_chapter": start_ch,
                    "end_chapter": end_ch,
                    "chapter_count": len(generated_chapters),
                    "generated_at": datetime.now().isoformat()
                },
                "summary": self.current_batch_summary,
                "chapters": [
                    {
                        "chapter_number": c.get('chapter_number') or c.get('chapter'),
                        "title": c.get('title', ''),
                        "word_count": c.get('word_count', 0),
                        "quality_score": c.get('quality_score', 0)
                    }
                    for c in generated_chapters
                ],
                "statistics": {
                    "total_generated": self.generated_chapters_count,
                    "total_target": self.total_chapters,
                    "progress_percent": round(self.generated_chapters_count / self.total_chapters * 100, 1)
                }
            }
            
            # 保存到文件
            summary_dir = self.project_path / "batch_summaries"
            summary_dir.mkdir(exist_ok=True)
            
            # 保存JSON格式（供程序读取）
            filename = f"batch_summary_{start_ch:03d}_{end_ch:03d}.json"
            filepath = summary_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, ensure_ascii=False, indent=2)
            
            # 同时保存最新总结（方便读取）
            latest_path = self.project_path / "batch_summary_latest.json"
            with open(latest_path, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, ensure_ascii=False, indent=2)
            
            # 🔥 保存Markdown格式（供人工阅读）
            try:
                md_content = self._generate_batch_summary_md(start_ch, end_ch, generated_chapters)
                md_filename = f"batch_summary_{start_ch:03d}_{end_ch:03d}.md"
                md_filepath = summary_dir / md_filename
                with open(md_filepath, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                    logger.info(f"[HierarchicalPlanner] Markdown批次总结已保存: {md_filepath}")
            except Exception as md_e:
                logger.error(f"[HierarchicalPlanner] Markdown生成失败: {md_e}")
                import traceback
                logger.error(traceback.format_exc())
            
            logger.info(f"[HierarchicalPlanner] 批次总结已保存: {filepath}")
            
        except Exception as e:
            logger.error(f"[HierarchicalPlanner] 保存批次总结失败: {e}")
    
    def _generate_batch_summary_md(self, start_ch: int, end_ch: int, chapters: List[Dict]) -> str:
        """生成批次总结的Markdown格式（人工可读）"""
        lines = []
        
        # 标题
        lines.append(f"# 📦 批次总结报告：第{start_ch}-{end_ch}章")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 基本信息
        lines.append("## 📊 基本信息")
        lines.append("")
        total_words = sum(c.get('word_count', 0) for c in chapters)
        avg_quality = sum(c.get('quality_score', 0) for c in chapters) / len(chapters) if chapters else 0
        lines.append(f"- **章节范围**: 第{start_ch}章 ~ 第{end_ch}章")
        lines.append(f"- **章节数量**: {len(chapters)} 章")
        lines.append(f"- **总字数**: {total_words:,} 字")
        lines.append(f"- **平均质量**: {avg_quality:.1f}/10")
        lines.append(f"- **整体进度**: {self.generated_chapters_count}/{self.total_chapters} 章 ({round(self.generated_chapters_count / self.total_chapters * 100, 1)}%)")
        lines.append("")
        
        # 阶段目标进度
        if self.current_batch_summary:
            current_goal = self.current_batch_summary.get('current_goal', {})
            if current_goal:
                lines.append("## 🎯 当前阶段目标")
                lines.append("")
                lines.append(f"- **目标ID**: {current_goal.get('goal_id', 'N/A')}")
                lines.append(f"- **目标名称**: {current_goal.get('goal_name', '未知')}")
                lines.append(f"- **完成进度**: {current_goal.get('progress_percent', 0)}%")
                lines.append("")
            
            # AI分析摘要
            ai_analysis = self.current_batch_summary.get('ai_analysis', {})
            if ai_analysis and ai_analysis.get('summary_text'):
                lines.append("## 🤖 AI分析摘要")
                lines.append("")
                lines.append(f"> {ai_analysis.get('summary_text', '')}")
                lines.append("")
            
            # 关键事件
            completed_events = self.current_batch_summary.get('completed_events', [])
            if completed_events:
                lines.append("## ⚡ 关键事件")
                lines.append("")
                for event in completed_events[:5]:  # 最多显示5个
                    ch = event.get('chapter', 'N/A')
                    desc = event.get('event', event.get('description', '未知事件'))
                    significance = event.get('significance', 'medium')
                    emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(significance, "⚪")
                    lines.append(f"{emoji} **第{ch}章**: {desc}")
                lines.append("")
            
            # 待解决钩子
            pending_hooks = self.current_batch_summary.get('pending_hooks', [])
            if pending_hooks:
                lines.append("## 🪝 待解决钩子")
                lines.append("")
                for hook in pending_hooks[:5]:
                    ch = hook.get('chapter', 'N/A')
                    content = hook.get('content', hook.get('hook', '未知钩子'))
                    priority = hook.get('priority', 'medium')
                    emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                    lines.append(f"{emoji} **第{ch}章**: {content[:100]}{'...' if len(content) > 100 else ''}")
                lines.append("")
            
            # 角色状态
            char_state = self.current_batch_summary.get('character_state', {})
            if char_state:
                lines.append("## 👤 角色状态")
                lines.append("")
                for role, state in char_state.items():
                    if isinstance(state, dict):
                        name = state.get('name', role)
                        status = state.get('status', state.get('state', '未知'))
                        lines.append(f"- **{name}** ({role}): {status}")
                lines.append("")
            
            # 剧情方向
            plot_direction = self.current_batch_summary.get('plot_direction', '')
            if plot_direction:
                lines.append("## 🧭 后续剧情方向")
                lines.append("")
                lines.append(f"> {plot_direction}")
                lines.append("")
        
        # 章节详情表
        lines.append("## 📖 章节详情")
        lines.append("")
        lines.append("| 章节 | 标题 | 字数 | 质量分 |")
        lines.append("|------|------|------|--------|")
        for ch in chapters:
            ch_num = ch.get('chapter_number') or ch.get('chapter') or '?'
            title = ch.get('title', '未命名')[:20]  # 限制长度
            words = ch.get('word_count', 0)
            quality = ch.get('quality_score', 0)
            lines.append(f"| 第{ch_num}章 | {title} | {words:,} | {quality:.1f} |")
        lines.append("")
        
        # 备注
        if self.current_batch_summary:
            notes = self.current_batch_summary.get('notes', '')
            if notes:
                lines.append("## 📝 备注")
                lines.append("")
                lines.append(notes)
                lines.append("")
        
        # 🔥 添加生成提示
        if not self.current_batch_summary:
            lines.append("## ⚠️ 提示")
            lines.append("")
            lines.append("> 批次总结数据暂未生成，此报告仅包含基础统计信息。")
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_analytics_service(self):
        """
        🔥 延迟初始化并返回ChapterAnalyticsService
        """
        if self._analytics_service is None and self.project_path:
            try:
                from .chapter_analytics_service import ChapterAnalyticsService
                novel_path = self.project_path.parent / self.project_path.name
                if novel_path.exists():
                    self._analytics_service = ChapterAnalyticsService(str(novel_path))
                    logger.info(f"[HierarchicalPlanner] 初始化ChapterAnalyticsService: {novel_path}")
            except Exception as e:
                logger.error(f"[HierarchicalPlanner] 初始化ChapterAnalyticsService失败: {e}")
        
        return self._analytics_service
    
    def _check_stage_completion(self):
        """检查当前阶段目标是否完成"""
        if not self.current_batch_summary:
            return
        
        current_goal = self._get_current_stage_goal()
        goal_id = current_goal.get('goal_id', 'G1')
        
        progress_str = self.current_batch_summary.get('goal_progress', {}).get(goal_id, '0%')
        try:
            progress = int(progress_str.replace('%', ''))
        except:
            progress = 0
        
        if progress >= 90 and self.current_stage_index < len(self.stage_goals) - 1:
            logger.info(f"[HierarchicalPlanner] 阶段目标{goal_id}完成({progress}%)，进入下一阶段")
            self.current_stage_index += 1
    
    def get_progress(self) -> Dict:
        """获取当前进度信息"""
        current_goal = self._get_current_stage_goal()
        
        return {
            "total_chapters": self.total_chapters,
            "generated_chapters": self.generated_chapters_count,
            "remaining_chapters": self.total_chapters - self.generated_chapters_count,
            "progress_percent": round((self.generated_chapters_count / self.total_chapters) * 100, 1),
            "current_stage": current_goal.get('description', '无')[:50],
            "stage_goal_id": current_goal.get('goal_id', 'G1')
        }
    
    def get_world_setting(self) -> Dict:
        """获取世界观设定"""
        if not self.world_setting:
            self.initialize()
        return self.world_setting
