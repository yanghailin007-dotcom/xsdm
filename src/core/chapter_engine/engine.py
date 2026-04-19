import logging
from typing import List, Optional, Dict, Any
from .types import ChapterContext, ChapterSpec, GeneratedChapter, BatchResult, Callbacks
from .generator import ChapterContentGenerator
from .quality_gate import QualityGate

logger = logging.getLogger(__name__)


class ChapterGenerationEngine:
    """
    章节生成引擎

    支持两种模式：
    1. 对话模式（默认）：使用 ChapterBatchOrchestrator，按爽点单元批次生成
    2. 传统模式（回退）：使用 ChapterContentGenerator，Stateless 批量/逐章生成
    """

    def __init__(
        self,
        api_client,
        batch_size: int = 4,  # 🔥 对话模式默认4章/批次
        use_conversation: bool = True,  # 🔥 新增：是否使用对话模式
        provider: str = "kimi",  # 🔥 新增：对话模型提供商
        model_name: str = "kimi-k2.5",  # 🔥 新增：对话模型名称
        novel_data: Optional[Dict[str, Any]] = None,  # 🔥 新增：小说数据（对话模式需要）
        project_path: Optional[str] = None,  # 🔥 新增：项目路径（滑动优化需要）
    ):
        self.api_client = api_client
        self.batch_size = batch_size
        self.use_conversation = use_conversation
        self.provider = provider
        self.model_name = model_name
        self.novel_data = novel_data
        self.project_path = project_path

        if use_conversation:
            # 对话模式：使用 ChapterBatchOrchestrator（延迟初始化，需要novel_data）
            self.orchestrator = None
            self.generator = None
            self.quality_gate = None
            logger.info(
                f"[ChapterEngine] 对话模式已启用 | 批次: {batch_size} | "
                f"模型: {model_name}"
            )
        else:
            # 传统模式：保留原有实现
            self.generator = ChapterContentGenerator(api_client)
            self.quality_gate = QualityGate(api_client)
            self.orchestrator = None
            logger.info("[ChapterEngine] 传统模式（Stateless）")

    def generate_batch(
        self,
        context: ChapterContext,
        specs: List[ChapterSpec],
        callbacks: Callbacks = None
    ) -> BatchResult:
        """
        生成批次章节

        Args:
            context: 章节上下文（含 novel_data 时启用对话模式）
            specs: 章节规格列表
            callbacks: 回调

        Returns:
            BatchResult
        """
        if callbacks is None:
            callbacks = Callbacks()

        # 🔥 判断使用哪种模式
        # 优先使用对话模式，如果条件不满足则回退到传统模式
        if self.use_conversation:
            # 尝试获取 novel_data（从参数或引擎初始化时传入）
            novel_data = getattr(context, 'novel_data', None) or self.novel_data
            if novel_data:
                return self._generate_batch_conversation(specs, callbacks, novel_data)
            else:
                logger.warning(
                    "[ChapterEngine] 对话模式需要 novel_data，回退到传统模式"
                )

        return self._generate_batch_legacy(context, specs, callbacks)

    def _generate_batch_conversation(
        self,
        specs: List[ChapterSpec],
        callbacks: Callbacks,
        novel_data: Dict[str, Any]
    ) -> BatchResult:
        """
        对话模式：使用 ChapterBatchOrchestrator 生成
        """
        from .chapter_batch_orchestrator import ChapterBatchOrchestrator

        if not self.orchestrator:
            self.orchestrator = ChapterBatchOrchestrator(
                api_client=self.api_client,
                novel_data=novel_data,
                project_path=self.project_path,
                batch_size=self.batch_size,
                provider=self.provider,
                model_name=self.model_name,
            )
            logger.info("[ChapterEngine] ChapterBatchOrchestrator 已创建")

        return self.orchestrator.generate_all(specs, callbacks)

    def _generate_batch_legacy(
        self,
        context: ChapterContext,
        specs: List[ChapterSpec],
        callbacks: Callbacks
    ) -> BatchResult:
        """
        传统模式：保留原有 Stateless 生成逻辑
        """
        result = BatchResult()
        all_chapters: List[GeneratedChapter] = []
        previous_ending = ""

        total = len(specs)
        for i in range(0, total, self.batch_size):
            batch_specs = specs[i:i + self.batch_size]
            logger.info(
                "生成批次 %s-%s / %s",
                i + 1,
                min(i + self.batch_size, total),
                total
            )
            if callbacks.on_progress:
                callbacks.on_progress({
                    "current": i + 1,
                    "total": total,
                    "batch_start": batch_specs[0].chapter_number,
                    "batch_end": batch_specs[-1].chapter_number,
                    "status": "generating"
                })

            # 1. 尝试批量生成
            batch_chapters = self.generator.generate_batch(
                context, batch_specs, previous_ending
            )
            if not batch_chapters:
                # fallback: 逐章生成
                batch_chapters = []
                for spec in batch_specs:
                    ch = self.generator.generate_single(
                        context, spec, previous_ending
                    )
                    if ch:
                        batch_chapters.append(ch)

            if not batch_chapters:
                logger.error("批次 %s-%s 生成失败", batch_specs[0].chapter_number, batch_specs[-1].chapter_number)
                result.issues.append(
                    f"批次 {batch_specs[0].chapter_number}-{batch_specs[-1].chapter_number} 生成失败"
                )
                continue

            # 2. 质量评估
            qa = self.quality_gate.assess(context, batch_chapters)
            if callbacks.on_progress:
                callbacks.on_progress({
                    "current": i + len(batch_chapters),
                    "total": total,
                    "status": "assessing",
                    "score": qa.get("score"),
                    "can_proceed": qa.get("can_proceed")
                })

            # 3. 按需润笔（低于7分或存在严重问题）
            if qa.get("score", 10) < 7.0 or not qa.get("can_proceed", True):
                feedback = qa.get("feedback", "质量不达标，需要优化")
                for ch in batch_chapters:
                    spec = next(
                        (s for s in batch_specs if s.chapter_number == ch.chapter_number),
                        None
                    )
                    if spec:
                        optimized = self.quality_gate.optimize(
                            context, spec, ch.content, feedback
                        )
                        ch.content = optimized
                        ch.word_count = len(optimized)

            # 更新质量分与问题记录
            for ch in batch_chapters:
                ch.quality_score = qa.get("score", 0.0)
                fb = qa.get("feedback", "")
                ch.issues = [fb] if fb else []

            # 4. 回调 + 更新前文衔接
            for ch in batch_chapters:
                all_chapters.append(ch)
                if callbacks.on_chapter_done:
                    callbacks.on_chapter_done(ch)
                previous_ending = (
                    ch.content[-300:] if len(ch.content) > 300 else ch.content
                )

        result.chapters = all_chapters
        if all_chapters:
            scores = [
                ch.quality_score for ch in all_chapters if ch.quality_score
            ]
            result.overall_score = sum(scores) / len(scores) if scores else 0.0
            result.can_proceed = all(ch.quality_score >= 6.0 for ch in all_chapters)
        return result
