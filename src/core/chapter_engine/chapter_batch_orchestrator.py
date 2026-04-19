"""
ChapterBatchOrchestrator - 章节批次调度编排器

职责：
1. 从 overall_stage_plans 解析大阶段上下文
2. 按批次大小切分 specs
3. 循环创建 ChapterBatchSession 生成每批
4. 批次间传递 Context Brief
5. 触发滑动优化（每10章）
6. 管理回调和进度
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from pathlib import Path

from src.core.chapter_engine.types import (
    ChapterContext, ChapterSpec, GeneratedChapter, BatchResult, Callbacks
)
from src.core.chapter_engine.quality_gate import QualityGate
from src.core.session_mode.sessions.chapter_batch_session import ChapterBatchSession

logger = logging.getLogger("ChapterBatchOrchestrator")


class ChapterBatchOrchestrator:
    """
    章节批次调度编排器

    按爽点单元批次调度章节生成，使用对话模式保持上下文。
    """

    def __init__(
        self,
        api_client,
        novel_data: Dict[str, Any],
        project_path: Optional[str] = None,
        batch_size: int = 4,
        provider: str = "kimi",
        model_name: str = "kimi-k2.5",
        temperature: float = 0.9,
        use_quality_gate: bool = True,
        use_sliding_optimizer: bool = True,
    ):
        """
        初始化批次编排器

        Args:
            api_client: APIClient 实例
            novel_data: 小说数据（含 overall_stage_plans、character_design 等）
            project_path: 项目路径（用于滑动优化从磁盘读取章节）
            batch_size: 批次大小（默认4章）
            provider: 模型提供商
            model_name: 模型名称
            temperature: 温度参数
            use_quality_gate: 是否使用 QualityGate 进行批次质检
            use_sliding_optimizer: 是否使用滑动优化
        """
        self.api_client = api_client
        self.novel_data = novel_data
        self.project_path = Path(project_path) if project_path else None
        self.batch_size = batch_size
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.use_quality_gate = use_quality_gate
        self.use_sliding_optimizer = use_sliding_optimizer

        # 复用 QualityGate（作为回退质检）
        self.quality_gate = QualityGate(api_client) if use_quality_gate else None

        # 滑动优化器（延迟初始化）
        self.sliding_optimizer = None

        # 批次间状态
        self.previous_brief: Optional[str] = None
        self.all_chapters: List[GeneratedChapter] = []
        self.batch_count = 0

        # 进度回调
        self._progress_callback: Optional[Callable[[Dict], None]] = None

        logger.info(
            f"[Orchestrator] 初始化完成 | 批次大小: {batch_size} | "
            f"模型: {model_name} | 滑动优化: {use_sliding_optimizer}"
        )

    def set_progress_callback(self, callback: Callable[[Dict], None]):
        """设置进度回调"""
        self._progress_callback = callback

    def _notify_progress(self, data: Dict):
        """通知进度"""
        if self._progress_callback:
            self._progress_callback(data)
        logger.info(f"[Orchestrator] 进度: {data}")

    # =====================================================================
    # 主入口
    # =====================================================================

    def generate_all(
        self,
        specs: List[ChapterSpec],
        callbacks: Callbacks = None
    ) -> BatchResult:
        """
        生成所有章节

        Args:
            specs: 所有章节的规格列表
            callbacks: 回调对象

        Returns:
            BatchResult
        """
        if callbacks is None:
            callbacks = Callbacks()

        result = BatchResult()
        total = len(specs)

        logger.info(f"[Orchestrator] 开始生成 {total} 章，批次大小: {self.batch_size}")

        # 按批次大小切分
        for i in range(0, total, self.batch_size):
            batch_specs = specs[i:i + self.batch_size]
            batch_start = batch_specs[0].chapter_number
            batch_end = batch_specs[-1].chapter_number

            self.batch_count += 1
            logger.info(f"[Orchestrator] 批次 {self.batch_count}: 第{batch_start}-{batch_end}章")

            # 进度通知
            self._notify_progress({
                "current": i + 1,
                "total": total,
                "batch_start": batch_start,
                "batch_end": batch_end,
                "batch_count": self.batch_count,
                "status": "generating"
            })
            if callbacks.on_progress:
                callbacks.on_progress({
                    "current": i + 1,
                    "total": total,
                    "batch_start": batch_start,
                    "batch_end": batch_end,
                    "status": "generating"
                })

            # 生成批次
            try:
                batch_chapters, brief = self._generate_batch(
                    batch_specs=batch_specs,
                    previous_brief=self.previous_brief,
                )
            except Exception as e:
                logger.error(f"[Orchestrator] 批次 {batch_start}-{batch_end} 生成失败: {e}")
                result.issues.append(f"批次 {batch_start}-{batch_end} 失败: {e}")
                continue

            if not batch_chapters:
                logger.error(f"[Orchestrator] 批次 {batch_start}-{batch_end} 无输出")
                result.issues.append(f"批次 {batch_start}-{batch_end} 无输出")
                continue

            # 保存章节 + 回调
            for ch in batch_chapters:
                self.all_chapters.append(ch)
                result.chapters.append(ch)
                if callbacks.on_chapter_done:
                    callbacks.on_chapter_done(ch)

            # 更新 Context Brief
            self.previous_brief = brief

            # 触发滑动优化（每10章）
            if self.use_sliding_optimizer and len(self.all_chapters) >= 10:
                self._trigger_sliding_window_review()

        # 最终质检
        if result.chapters and self.quality_gate:
            try:
                # 构建 ChapterContext
                ctx = self._build_chapter_context()
                qa = self.quality_gate.assess(ctx, result.chapters)
                result.overall_score = qa.get("score", 0.0)
                result.can_proceed = qa.get("can_proceed", True)
                logger.info(f"[Orchestrator] 最终质检: {result.overall_score}分")
            except Exception as e:
                logger.warning(f"[Orchestrator] 最终质检失败: {e}")

        logger.info(
            f"[Orchestrator] 全部完成 | 成功: {len(result.chapters)}/{total}章 | "
            f"问题: {len(result.issues)}个"
        )
        return result

    # =====================================================================
    # 批次生成
    # =====================================================================

    def _generate_batch(
        self,
        batch_specs: List[ChapterSpec],
        previous_brief: Optional[str] = None,
    ) -> Tuple[List[GeneratedChapter], str]:
        """
        生成单个批次

        Returns:
            (章节列表, Context Brief)
        """
        batch_start = batch_specs[0].chapter_number

        # 1. 解析爽点单元上下文
        stage_context = self._get_stage_context_for_chapter(batch_start)
        logger.info(
            f"[Orchestrator] 批次上下文: {stage_context.get('stage_name', '未知')} | "
            f"范围: {stage_context.get('stage_chapter_range', '未知')}"
        )

        # 2. 创建 ChapterBatchSession
        session = ChapterBatchSession(
            api_client=self.api_client,
            novel_data=self.novel_data,
            context_briefs=[previous_brief] if previous_brief else None,
            batch_start_chapter=batch_start,
            batch_size=len(batch_specs),
            stage_context=stage_context,
            provider=self.provider,
            model_name=self.model_name,
            temperature=self.temperature,
        )

        # 注入核心设定圣经（如果有）
        core_setting = self._build_core_setting_text()
        if core_setting:
            session.set_core_setting(core_setting)

        # 3. 生成章节
        logger.info(f"[Orchestrator] 开始对话生成批次 {batch_start}-{batch_specs[-1].chapter_number}")
        chapters = session.generate_batch(batch_specs)

        if not chapters:
            return [], ""

        # 4. 批次质检（同session）
        logger.info(f"[Orchestrator] 批次内质检（{len(chapters)}章）")
        qa = session.assess_batch_quality(chapters)
        score = qa.get("score", 6.0)
        can_proceed = qa.get("can_proceed", True)
        feedback = qa.get("feedback", "")
        per_chapter = qa.get("per_chapter", [])

        logger.info(f"[Orchestrator] 质检结果: {score}分 | 通过: {can_proceed}")

        # 5. 不达标 → 重新生成
        if score < 7.0 or not can_proceed:
            logger.warning(f"[Orchestrator] 质检不达标，尝试重新生成")
            for i, ch in enumerate(chapters):
                # 找出有问题的章节
                ch_feedback = ""
                for pc in per_chapter:
                    if pc.get("chapter") == ch.chapter_number:
                        ch_feedback = pc.get("issues", feedback)
                        break

                if ch_feedback or ch.quality_score < 7.0:
                    spec = next((s for s in batch_specs if s.chapter_number == ch.chapter_number), None)
                    if spec:
                        logger.info(f"[Orchestrator] 重新生成第{ch.chapter_number}章")
                        new_ch = session.regenerate_chapter(spec, ch_feedback or feedback)
                        if new_ch:
                            chapters[i] = new_ch

        # 更新质量分
        for ch in chapters:
            ch.quality_score = score

        # 6. 批次总结
        logger.info(f"[Orchestrator] 生成批次总结")
        summary = session.generate_batch_summary()
        if summary:
            logger.info(f"[Orchestrator] 批次总结: {summary.get('summary_text', '')[:50]}...")

        # 7. 导出 Context Brief
        brief = session.export_context_brief()

        return chapters, brief

    # =====================================================================
    # 爽点单元上下文解析
    # =====================================================================

    def _get_stage_context_for_chapter(self, chapter_number: int) -> Dict[str, Any]:
        """
        根据章节号定位大阶段，提取爽点单元上下文

        Args:
            chapter_number: 章节号

        Returns:
            大阶段上下文字典
        """
        overall = self.novel_data.get("overall_stage_plans", {})
        if not overall:
            return {}

        stage_plan = overall.get("overall_stage_plan", overall)

        # 大阶段映射
        stage_keys = ["opening_stage", "development_stage", "climax_stage", "ending_stage"]
        stage_names = {
            "opening_stage": "黄金开局阶段",
            "development_stage": "成长发展阶段",
            "climax_stage": "高潮爆发阶段",
            "ending_stage": "收尾完结阶段",
        }

        for key in stage_keys:
            stage_info = stage_plan.get(key)
            if not stage_info:
                continue

            chapter_range = stage_info.get("chapter_range", "")
            # 解析范围，如 "1-100"
            import re
            numbers = re.findall(r'\d+', chapter_range)
            if len(numbers) >= 2:
                start, end = int(numbers[0]), int(numbers[1])
                if start <= chapter_number <= end:
                    return {
                        "stage_name": stage_names.get(key, key),
                        "stage_chapter_range": chapter_range,
                        "core_payoff": stage_info.get("core_payoff", ""),
                        "suppression_setup": stage_info.get("suppression_setup", ""),
                        "key_events": stage_info.get("key_events", []),
                        "emotional_focus": stage_info.get("emotional_focus", ""),
                        "climax": stage_info.get("climax", ""),
                        "next_stage_hook": stage_info.get("next_stage_hook", ""),
                    }

        # 未找到，返回第一个阶段的信息（兜底）
        for key in stage_keys:
            stage_info = stage_plan.get(key)
            if stage_info:
                return {
                    "stage_name": stage_names.get(key, key),
                    "stage_chapter_range": stage_info.get("chapter_range", ""),
                    "core_payoff": stage_info.get("core_payoff", ""),
                    "suppression_setup": stage_info.get("suppression_setup", ""),
                    "key_events": stage_info.get("key_events", []),
                    "emotional_focus": stage_info.get("emotional_focus", ""),
                }

        return {}

    def _build_core_setting_text(self) -> str:
        """
        构建核心设定圣经文本（Layer 1 完整版，批次首章注入）

        Returns:
            核心设定文本
        """
        parts = []

        # 小说基本信息
        title = self.novel_data.get("novel_title", "未命名")
        category = self.novel_data.get("category", "未分类")
        synopsis = self.novel_data.get("novel_synopsis", "")
        parts.append(f"【小说】{title}（{category}）")
        if synopsis:
            parts.append(f"【简介】{synopsis}")

        # 世界观
        worldview = self.novel_data.get("core_worldview", self.novel_data.get("worldview", {}))
        if worldview and isinstance(worldview, dict):
            overview = worldview.get("overview", worldview.get("description", ""))
            if overview:
                parts.append(f"【世界观】{overview}")

        # 主角
        character = self.novel_data.get("character_design", {})
        if character and isinstance(character, dict):
            protagonist = character.get("protagonist", {})
            if protagonist and isinstance(protagonist, dict):
                name = protagonist.get("name", "")
                personality = protagonist.get("personality", "")
                if name:
                    parts.append(f"【主角】{name} — {personality}")

        # 金手指
        golden_finger = self.novel_data.get("golden_finger", {})
        if golden_finger and isinstance(golden_finger, dict):
            gf_name = golden_finger.get("name", "")
            gf_desc = golden_finger.get("description", "")
            if gf_name:
                parts.append(f"【金手指】{gf_name} — {gf_desc}")

        # 成长规划
        growth = self.novel_data.get("global_growth_plan", {})
        if growth and isinstance(growth, dict):
            milestones = growth.get("milestones", [])
            if milestones:
                parts.append(f"【成长里程碑】{', '.join(str(m) for m in milestones[:3])}")

        # 情绪蓝图
        blueprint = self.novel_data.get("emotional_blueprint", {})
        if blueprint and isinstance(blueprint, dict):
            spectrum = blueprint.get("爽感光谱", blueprint.get("spectrum", ""))
            if spectrum:
                parts.append(f"【爽感光谱】{spectrum}")

        return "\n".join(parts)

    def _build_chapter_context(self) -> ChapterContext:
        """构建 ChapterContext（供 QualityGate 使用）"""
        return ChapterContext(
            novel_title=self.novel_data.get("novel_title", "未命名"),
            core_setting=self._build_core_setting_text(),
            writing_style=self.novel_data.get("writing_style_guide", {}).get("style_description", "番茄小说爽文风格"),
        )

    # =====================================================================
    # 滑动优化
    # =====================================================================

    def _trigger_sliding_window_review(self):
        """
        触发滑动窗口优化

        每生成10章后触发一次，检查最近10章的质量和连贯性。
        """
        if not self.project_path or not self.project_path.exists():
            logger.warning("[Orchestrator] 项目路径未设置，跳过滑动优化")
            return

        if not self.sliding_optimizer:
            try:
                from web.services.market_driven.stage_review_optimizer import StageReviewOptimizer
                self.sliding_optimizer = StageReviewOptimizer(
                    project_path=str(self.project_path),
                    api_client=self.api_client,
                )
                logger.info("[Orchestrator] StageReviewOptimizer 初始化完成")
            except Exception as e:
                logger.error(f"[Orchestrator] 滑动优化器初始化失败: {e}")
                return

        # 计算窗口范围
        total = len(self.all_chapters)
        window_end = self.all_chapters[-1].chapter_number
        window_start = max(1, window_end - 9)

        logger.info(f"[Orchestrator] 触发滑动优化: 第{window_start}-{window_end}章")

        try:
            review_result = self.sliding_optimizer.optimize_window(
                window_start=window_start,
                window_end=window_end,
            )
            logger.info(
                f"[Orchestrator] 滑动优化完成: "
                f"状态={review_result.get('status', 'unknown')} | "
                f"修复={len(review_result.get('fixes', []))}处"
            )
        except Exception as e:
            logger.error(f"[Orchestrator] 滑动优化执行失败: {e}")
