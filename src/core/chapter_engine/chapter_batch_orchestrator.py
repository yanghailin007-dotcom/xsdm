"""
ChapterBatchOrchestrator - 章节批次调度编排器

职责：
1. 从 overall_stage_plans 解析大阶段上下文
2. 🔥 基于大阶段信息动态生成爽点单元规划
3. 按爽点单元切分批次
4. 循环创建 ChapterBatchSession 生成每批
5. 批次间传递 Context Brief
6. 触发滑动优化（每10章）
7. 管理回调和进度
"""

import logging
import json
import re
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

        # 🔥 爽点单元缓存（按大阶段缓存）
        self._payoff_units_cache: Dict[str, List[Dict]] = {}
        self._current_stage_name: Optional[str] = None

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
        
        # 计算实际章节范围
        if specs:
            min_chapter = min(s.chapter_number for s in specs)
            max_chapter = max(s.chapter_number for s in specs)
        else:
            min_chapter, max_chapter = 1, 1
        
        # 将实际章节范围存入 novel_data，供后续使用
        self.novel_data['_actual_chapter_range'] = (min_chapter, max_chapter)

        logger.info(f"[Orchestrator] 开始生成 {total} 章（第{min_chapter}-{max_chapter}章），批次大小: {self.batch_size}")
        
        # 🔥 预生成全书爽点单元（一次性生成所有大阶段的爽点单元）
        self._pre_generate_all_payoff_units(max_chapter=max_chapter)

        # 🔥 为每个 spec 填充细纲（从爽点单元中提取）
        self._fill_specs_outline(specs)

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

    def _build_novel_context_section(self) -> str:
        """构建小说核心设定上下文，注入 prompt 防止 AI 跑偏"""
        parts = []
        nd = self.novel_data
        
        # 1. 小说标题
        title = nd.get('novel_title') or nd.get('title', '未命名')
        parts.append(f"【小说标题】\n{title}")
        
        # 2. 小说简介/故事梗概
        synopsis = nd.get('novel_synopsis') or nd.get('story_synopsis') or nd.get('synopsis', '')
        if synopsis:
            parts.append(f"\n【小说简介/故事梗概】\n{synopsis}")
        
        # 3. 核心世界观
        worldview = nd.get('core_worldview', {})
        if isinstance(worldview, dict) and worldview:
            worldview_text = json.dumps(worldview, ensure_ascii=False)
            if len(worldview_text) > 800:
                worldview_text = worldview_text[:800] + "..."
            parts.append(f"\n【核心世界观】\n{worldview_text}")
        
        # 4. 主要角色设计
        char_design = nd.get('character_design', {})
        if isinstance(char_design, dict) and char_design:
            char_text = json.dumps(char_design, ensure_ascii=False)
            if len(char_text) > 800:
                char_text = char_text[:800] + "..."
            parts.append(f"\n【主要角色设计】\n{char_text}")
        
        # 5. 金手指设定
        golden_finger = nd.get('golden_finger', {})
        if isinstance(golden_finger, dict) and golden_finger:
            gf_text = json.dumps(golden_finger, ensure_ascii=False)
            if len(gf_text) > 600:
                gf_text = gf_text[:600] + "..."
            parts.append(f"\n【金手指设定】\n{gf_text}")
        elif isinstance(golden_finger, str) and golden_finger:
            parts.append(f"\n【金手指设定】\n{golden_finger}")
        
        # 6. 写作风格
        style = nd.get('writing_style_guide', {})
        if isinstance(style, dict) and style:
            style_text = json.dumps(style, ensure_ascii=False)
            if len(style_text) > 400:
                style_text = style_text[:400] + "..."
            parts.append(f"\n【写作风格】\n{style_text}")
        
        # 7. 核心设定（备选）
        creative_seed = nd.get('creative_seed', {})
        if isinstance(creative_seed, dict) and creative_seed:
            core_setting = creative_seed.get('coreSetting') or creative_seed.get('core_setting', '')
            if core_setting:
                parts.append(f"\n【核心设定】\n{core_setting}")
            genre = creative_seed.get('genre') or creative_seed.get('category', '')
            if genre:
                parts.append(f"\n【题材类型】\n{genre}")
        
        if len(parts) <= 1:  # 只有标题，说明没拿到多少数据
            logger.warning("[Orchestrator] 小说核心设定数据不足，prompt 上下文可能薄弱")
        
        return "\n".join(parts)

    # =====================================================================
    # 爽点单元生成与管理
    # =====================================================================

    def _fill_specs_outline(self, specs: List[ChapterSpec]) -> None:
        """
        为每个 ChapterSpec 填充细纲（outline）。
        从爽点单元或阶段计划中提取对应章节的核心内容描述。
        """
        for spec in specs:
            if spec.outline:
                continue  # 已有细纲，跳过

            ctx = self._get_stage_context_for_chapter(spec.chapter_number)
            if not ctx:
                continue

            parts = []
            # 爽点单元信息
            pu_name = ctx.get("payoff_unit_name", "")
            pu_range = ctx.get("payoff_unit_range", "")
            core_payoff = ctx.get("core_payoff", "")
            suppression = ctx.get("suppression_setup", "")
            beats = ctx.get("key_beats", [])

            if pu_name:
                parts.append(f"所属爽点单元: {pu_name} ({pu_range})")
            if core_payoff:
                parts.append(f"核心爽点: {core_payoff}")
            if suppression:
                parts.append(f"压抑铺垫: {suppression}")
            if beats:
                if isinstance(beats, list):
                    parts.append(f"关键节拍: {' → '.join(str(b) for b in beats)}")
                else:
                    parts.append(f"关键节拍: {beats}")

            # 尝试从阶段key_events中找到更具体的章节事件
            stage_key = self._get_stage_key_for_chapter(spec.chapter_number)
            if stage_key:
                stage_info = self._get_stage_info_by_key(stage_key)
                if stage_info:
                    key_events = stage_info.get("key_events", [])
                    # 简单映射：按章节号对事件数量取模分配
                    if key_events and isinstance(key_events, list):
                        idx = (spec.chapter_number - 1) % len(key_events)
                        event_desc = key_events[idx]
                        if event_desc and isinstance(event_desc, str):
                            parts.append(f"本章关键事件: {event_desc}")

            if parts:
                spec.outline = "\n".join(parts)
                logger.info(f"[Orchestrator] 第{spec.chapter_number}章细纲已填充: {spec.outline[:60]}...")

    def _get_stage_info_by_key(self, stage_key: str) -> Optional[Dict]:
        """根据阶段键名获取阶段信息"""
        overall = self.novel_data.get("overall_stage_plans", {})
        if not overall:
            return None
        stage_plan = overall.get("overall_stage_plan", overall)
        return stage_plan.get(stage_key)

    def _pre_generate_all_payoff_units(self, max_chapter: int = None) -> bool:
        """
        🔥 一次性预生成全书所有大阶段的爽点单元
        
        在章节生成开始前，遍历所有大阶段，一次性调用 API 生成全书爽点单元规划。
        这样可以全局把控爽点节奏，避免阶段间重复或断层。
        
        Args:
            max_chapter: 实际要生成的最大章节号，用于截断超出范围的阶段
        
        Returns:
            是否成功
        """
        # 检查是否已经预生成
        if hasattr(self, '_all_payoff_units_generated') and self._all_payoff_units_generated:
            logger.info("[Orchestrator] 全书爽点单元已预生成，跳过")
            return True
        
        overall = self.novel_data.get("overall_stage_plans", {})
        if not overall:
            logger.warning("[Orchestrator] 未找到 overall_stage_plans，无法预生成爽点单元")
            return False
        
        stage_plan = overall.get("overall_stage_plan", overall)
        stage_keys = ["opening_stage", "development_stage", "climax_stage", "ending_stage"]
        
        # 收集所有大阶段信息
        stage_infos = []
        for key in stage_keys:
            info = stage_plan.get(key)
            if not info:
                continue
            stage_infos.append((key, info))
        
        if not stage_infos:
            logger.warning("[Orchestrator] 未找到任何大阶段信息")
            return False
        
        # 检查是否已全部缓存
        all_cached = True
        for key, _ in stage_infos:
            if key not in self._payoff_units_cache and not self.novel_data.get("_payoff_units", {}).get(key):
                all_cached = False
                break
        
        if all_cached:
            logger.info("[Orchestrator] 所有爽点单元已缓存，跳过预生成")
            self._all_payoff_units_generated = True
            return True
        
        logger.info(f"[Orchestrator] 🔥 开始预生成全书爽点单元，共 {len(stage_infos)} 个大阶段")
        
        # 构建全书 prompt
        novel_context = self._build_novel_context_section()
        
        # 计算实际总章节数提示
        total_chapters_hint = ""
        if max_chapter:
            total_chapters_hint = f"\n\n【实际生成范围】\n本书实际共 {max_chapter} 章。你只需为第 1-{max_chapter} 章规划爽点单元，不要超出此范围。"
        
        prompt_parts = [
            "你是一位顶级的网络小说结构规划专家。请基于以下小说核心设定和全书大阶段信息，生成全书的爽点单元规划。",
            "",
            "【重要约束】",
            "你必须严格遵循下方【小说核心设定】中的世界观、角色、金手指等设定来规划爽点单元，",
            "绝不能偏离原小说的题材和风格。如果【全书架构】中的描述与【小说核心设定】冲突，",
            "以【小说核心设定】为准进行纠正。",
            total_chapters_hint,
            "",
            novel_context,
            "",
            "【爽点单元定义】",
            "一个爽点单元 = 铺垫(setup) + 压抑(suppression) + 爆发(payoff) + 收获(harvest)",
            "每个爽点单元跨3-5章，构成一个完整的情绪闭环（压抑→爆发→爽）。",
            "",
            "【全书架构】",
        ]
        
        for key, info in stage_infos:
            stage_name = info.get("stage_name", key)
            chapter_range = info.get("chapter_range", "")
            
            # 🔥 修复：根据实际 max_chapter 截断阶段范围
            if max_chapter and chapter_range:
                numbers = re.findall(r'\d+', str(chapter_range))
                if len(numbers) >= 2:
                    stage_start, stage_end = int(numbers[0]), int(numbers[1])
                    if stage_start > max_chapter:
                        # 整个阶段都超出范围，跳过
                        logger.info(f"[Orchestrator] 跳过超出范围的阶段 {key}: {chapter_range} > max={max_chapter}")
                        continue
                    if stage_end > max_chapter:
                        stage_end = max_chapter
                        chapter_range = f"{stage_start}-{stage_end}"
                        logger.info(f"[Orchestrator] 截断阶段 {key} 范围: {info.get('chapter_range', '')} -> {chapter_range}")
            
            core_payoff = info.get("core_payoff") or info.get("stage_goal", "")
            suppression_setup = info.get("suppression_setup") or info.get("core_conflicts", "")
            key_events = info.get("key_events") or info.get("key_developments", [])
            emotional_focus = info.get("emotional_focus", "")
            climax = info.get("climax", "")
            next_stage_hook = info.get("next_stage_hook", "")
            
            prompt_parts.append(f"\n【大阶段: {stage_name}】")
            prompt_parts.append(f"- 章节范围: 第{chapter_range}章")
            if core_payoff:
                prompt_parts.append(f"- 核心爽点: {core_payoff}")
            if suppression_setup:
                prompt_parts.append(f"- 压抑铺垫: {suppression_setup}")
            if key_events:
                prompt_parts.append(f"- 关键事件: {json.dumps(key_events, ensure_ascii=False)}")
            if emotional_focus:
                prompt_parts.append(f"- 情绪焦点: {emotional_focus}")
            if climax:
                prompt_parts.append(f"- 阶段高潮: {climax}")
            if next_stage_hook:
                prompt_parts.append(f"- 下阶段钩子: {next_stage_hook}")
        
        prompt_parts.extend([
            "",
            "【输出要求】",
            "请输出 JSON 对象。键名为大阶段键名（opening_stage, development_stage, climax_stage, ending_stage），每个键对应一个爽点单元数组。",
            "",
            "每个爽点单元的结构：",
            "{",
            '  "unit_name": "爽点单元名称（4-8字，有画面感）",',
            '  "chapter_range": "如 1-4",',
            '  "role_in_stage": "该单元在阶段中的定位（如：开局钩子、成长转折、高潮铺垫）",',
            '  "core_payoff": "核心爽点（一句话描述，如：主角觉醒金手指反杀反派）",',
            '  "suppression_setup": "压抑铺垫设计（如：主角被陷害，濒死之际）",',
            '  "emotional_arc": "情绪弧线（如：绝望→震惊→狂喜→期待）",',
            '  "key_beats": ["关键节拍1", "关键节拍2", "关键节拍3", "关键节拍4"]',
            "}",
            "",
            "要求：",
            "1. 全书爽点单元之间要有递进关系，不能重复",
            "2. 每个单元必须有明确的 core_payoff（核心爽点）",
            "3. 单元的 suppression_setup 要具体，让读者感到憋屈",
            "4. 阶段之间要留钩子衔接，最后一个单元要留悬念",
            "5. 情绪弧线要符合番茄爽文节奏：先抑后扬",
            "6. key_beats 要具体到情节层面，不要笼统",
            "7. 爽点单元数量约 每个大阶段章节数 // 4 个",
            "",
            "请只输出 JSON 对象，不要添加 markdown 代码块标记。",
        ])
        
        prompt = "\n".join(prompt_parts)
        
        try:
            logger.info("[Orchestrator] 调用 API 生成全书爽点单元...")
            result = self.api_client.generate_content_with_retry(
                content_type="payoff_unit_generation",
                user_prompt=prompt,
                provider="gemini",
                purpose="all_payoff_units",
            )
            
            if not result:
                logger.error("[Orchestrator] 全书爽点单元生成返回空")
                return False
            
            # 解析JSON
            if isinstance(result, dict):
                all_units = result
            elif isinstance(result, str):
                # 尝试提取 JSON 对象
                match = re.search(r'\{[\s\S]*\}', result)
                if not match:
                    logger.error("[Orchestrator] 无法从响应中提取 JSON 对象")
                    return False
                all_units = json.loads(match.group(0))
            else:
                logger.error(f"[Orchestrator] 未知响应类型: {type(result)}")
                return False
            
            if not isinstance(all_units, dict):
                logger.error(f"[Orchestrator] 解析结果不是字典: {type(all_units)}")
                return False
            
            # 缓存到各个阶段
            success_count = 0
            for key, _ in stage_infos:
                units = all_units.get(key)
                if units and isinstance(units, list) and len(units) > 0:
                    self._payoff_units_cache[key] = units
                    if "_payoff_units" not in self.novel_data:
                        self.novel_data["_payoff_units"] = {}
                    self.novel_data["_payoff_units"][key] = units
                    logger.info(f"[Orchestrator] ✅ 预生成爽点单元: {key} ({len(units)} 个)")
                    success_count += 1
                else:
                    logger.warning(f"[Orchestrator] ⚠️ 阶段 {key} 未返回爽点单元，将回退到单阶段生成")
            
            if success_count == len(stage_infos):
                self._all_payoff_units_generated = True
                logger.info("[Orchestrator] ✅ 全书爽点单元预生成完成")
                return True
            elif success_count > 0:
                logger.info(f"[Orchestrator] ⚠️ 部分预生成完成 ({success_count}/{len(stage_infos)})，缺失的将在章节生成时动态生成")
                return True
            else:
                logger.error("[Orchestrator] ❌ 全书爽点单元预生成失败")
                return False
                
        except Exception as e:
            logger.error(f"[Orchestrator] 全书爽点单元预生成异常: {e}")
            import traceback
            logger.error(f"[Orchestrator] 错误堆栈: {traceback.format_exc()}")
            return False

    def _get_or_generate_payoff_units(self, stage_key: str, stage_info: Dict) -> List[Dict]:
        """
        获取或生成大阶段的爽点单元规划

        Args:
            stage_key: 大阶段键名（opening_stage等）
            stage_info: 大阶段信息

        Returns:
            爽点单元列表
        """
        # 检查缓存
        if stage_key in self._payoff_units_cache:
            logger.info(f"[Orchestrator] 使用缓存的爽点单元: {stage_key}")
            return self._payoff_units_cache[stage_key]

        # 检查 novel_data 缓存
        cached = self.novel_data.get("_payoff_units", {}).get(stage_key)
        if cached:
            logger.info(f"[Orchestrator] 从 novel_data 加载爽点单元: {stage_key}")
            self._payoff_units_cache[stage_key] = cached
            return cached

        # 生成爽点单元
        logger.info(f"[Orchestrator] 生成爽点单元: {stage_key}")
        payoff_units = self._generate_payoff_units_for_stage(stage_key, stage_info)
        if payoff_units:
            self._payoff_units_cache[stage_key] = payoff_units
            # 保存到 novel_data 缓存
            if "_payoff_units" not in self.novel_data:
                self.novel_data["_payoff_units"] = {}
            self.novel_data["_payoff_units"][stage_key] = payoff_units

        return payoff_units

    def _generate_payoff_units_for_stage(self, stage_key: str, stage_info: Dict) -> List[Dict]:
        """
        基于大阶段信息生成爽点单元规划

        使用 gemini-3-flash 生成，快速便宜。

        Args:
            stage_key: 大阶段键名
            stage_info: 大阶段信息

        Returns:
            爽点单元列表
        """
        stage_name = stage_info.get("stage_name", stage_key)
        chapter_range = stage_info.get("chapter_range", "1-30")
        # 🔥 修复：兼容阶段计划.json 的实际字段名
        stage_goal = stage_info.get("stage_goal") or stage_info.get("core_payoff", "")
        key_developments = stage_info.get("key_developments") or stage_info.get("key_events", [])
        core_conflicts = stage_info.get("core_conflicts") or stage_info.get("suppression_setup", "")

        # 解析章节范围
        numbers = re.findall(r'\d+', chapter_range)
        if len(numbers) >= 2:
            stage_start, stage_end = int(numbers[0]), int(numbers[1])
        else:
            stage_start, stage_end = 1, 30

        stage_chapter_count = stage_end - stage_start + 1

        novel_context = self._build_novel_context_section()
        
        prompt = f"""你是一位顶级的网络小说结构规划专家。请基于以下小说核心设定和大阶段信息，生成爽点单元规划。

【重要约束】
你必须严格遵循下方【小说核心设定】中的世界观、角色、金手指等设定来规划爽点单元，
绝不能偏离原小说的题材和风格。如果【大阶段信息】中的描述与【小说核心设定】冲突，
以【小说核心设定】为准进行纠正。

{novel_context}

【爽点单元定义】
一个爽点单元 = 铺垫(setup) + 压抑(suppression) + 爆发(payoff) + 收获(harvest)
每个爽点单元跨3-5章，构成一个完整的情绪闭环（压抑→爆发→爽）。

【大阶段信息】
- 阶段名称: {stage_name}
- 章节范围: 第{chapter_range}章（共{stage_chapter_count}章）
- 阶段目标: {stage_goal}
- 关键发展: {json.dumps(key_developments, ensure_ascii=False)}
- 核心冲突: {core_conflicts}

【输出要求】
请输出 JSON 数组。爽点单元数量约 {max(1, stage_chapter_count // 4)} 个。

每个爽点单元的结构：
{{
  "unit_name": "爽点单元名称（4-8字，有画面感）",
  "chapter_range": "如 1-4",
  "role_in_stage": "该单元在阶段中的定位（如：开局钩子、成长转折、高潮铺垫）",
  "core_payoff": "核心爽点（一句话描述，如：主角觉醒金手指反杀反派）",
  "suppression_setup": "压抑铺垫设计（如：主角被陷害，濒死之际）",
  "emotional_arc": "情绪弧线（如：绝望→震惊→狂喜→期待）",
  "key_beats": ["关键节拍1", "关键节拍2", "关键节拍3", "关键节拍4"]
}}

要求：
1. 爽点单元之间要有递进关系，不能重复
2. 每个单元必须有明确的 core_payoff（核心爽点）
3. 单元的 suppression_setup 要具体，让读者感到憋屈
4. 最后一个单元要留钩子，衔接下一阶段
5. 情绪弧线要符合番茄爽文节奏：先抑后扬
6. key_beats 要具体到情节层面，不要笼统

请只输出 JSON 数组，不要添加 markdown 代码块标记。"""

        try:
            logger.info(f"[Orchestrator] 调用 gemini-3-flash 生成爽点单元: {stage_name}")
            result = self.api_client.generate_content_with_retry(
                content_type="payoff_unit_generation",
                user_prompt=prompt,
                provider="gemini",
                purpose=f"payoff_units_{stage_key}",
            )

            if not result:
                logger.error("[Orchestrator] 爽点单元生成返回空")
                return self._create_fallback_payoff_units(stage_start, stage_end)

            # 解析JSON
            if isinstance(result, list):
                units = result
                if len(units) > 0:
                    logger.info(f"[Orchestrator] 生成爽点单元 {len(units)} 个")
                    return units
            elif isinstance(result, str):
                # 提取JSON数组
                match = re.search(r'\[.*\]', result, re.DOTALL)
                if match:
                    units = json.loads(match.group(0))
                    if isinstance(units, list) and len(units) > 0:
                        logger.info(f"[Orchestrator] 生成爽点单元 {len(units)} 个")
                        return units

            logger.warning("[Orchestrator] 爽点单元解析失败，使用fallback")
            return self._create_fallback_payoff_units(stage_start, stage_end)

        except Exception as e:
            logger.error(f"[Orchestrator] 爽点单元生成失败: {e}")
            return self._create_fallback_payoff_units(stage_start, stage_end)

    def _create_fallback_payoff_units(self, stage_start: int, stage_end: int) -> List[Dict]:
        """创建fallback爽点单元（均匀分配）"""
        units = []
        total = stage_end - stage_start + 1
        unit_size = 4
        count = 0
        for i in range(stage_start, stage_end + 1, unit_size):
            count += 1
            end = min(i + unit_size - 1, stage_end)
            units.append({
                "unit_name": f"爽点单元{count}",
                "chapter_range": f"{i}-{end}",
                "role_in_stage": "阶段推进",
                "core_payoff": f"第{i}-{end}章的核心爽点",
                "suppression_setup": "主角面临挑战",
                "emotional_arc": "压抑→爆发→爽",
                "key_beats": ["铺垫", "压抑", "爆发", "收获"]
            })
        return units

    def _get_payoff_unit_for_chapter(self, chapter_number: int, stage_info: Dict) -> Optional[Dict]:
        """
        根据章节号获取所在爽点单元

        Args:
            chapter_number: 章节号
            stage_info: 大阶段信息

        Returns:
            爽点单元字典或None
        """
        stage_key = self._get_stage_key_for_chapter(chapter_number)
        if not stage_key:
            return None

        payoff_units = self._get_or_generate_payoff_units(stage_key, stage_info)
        if not payoff_units:
            return None

        for unit in payoff_units:
            cr = unit.get("chapter_range", "")
            numbers = re.findall(r'\d+', cr)
            if len(numbers) >= 2:
                start, end = int(numbers[0]), int(numbers[1])
                if start <= chapter_number <= end:
                    return unit

        return None

    def _get_stage_key_for_chapter(self, chapter_number: int) -> Optional[str]:
        """根据章节号获取大阶段键名"""
        overall = self.novel_data.get("overall_stage_plans", {})
        if not overall:
            return None
        stage_plan = overall.get("overall_stage_plan", overall)
        stage_keys = ["opening_stage", "development_stage", "climax_stage", "ending_stage"]
        for key in stage_keys:
            stage_info = stage_plan.get(key)
            if not stage_info:
                continue
            cr = stage_info.get("chapter_range", "")
            numbers = re.findall(r'\d+', cr)
            if len(numbers) >= 2:
                start, end = int(numbers[0]), int(numbers[1])
                if start <= chapter_number <= end:
                    return key
        return None

    def _get_stage_context_for_chapter(self, chapter_number: int) -> Dict[str, Any]:
        """
        根据章节号定位大阶段和爽点单元，提取上下文

        Args:
            chapter_number: 章节号

        Returns:
            爽点单元上下文字典
        """
        overall = self.novel_data.get("overall_stage_plans", {})
        if not overall:
            return {}

        stage_plan = overall.get("overall_stage_plan", overall)
        stage_keys = ["opening_stage", "development_stage", "climax_stage", "ending_stage"]
        stage_names = {
            "opening_stage": "黄金开局阶段",
            "development_stage": "成长发展阶段",
            "climax_stage": "高潮爆发阶段",
            "ending_stage": "收尾完结阶段",
        }

        # 找到大阶段
        stage_info = None
        stage_key = None
        for key in stage_keys:
            info = stage_plan.get(key)
            if not info:
                continue
            cr = info.get("chapter_range", "")
            numbers = re.findall(r'\d+', cr)
            if len(numbers) >= 2:
                start, end = int(numbers[0]), int(numbers[1])
                if start <= chapter_number <= end:
                    stage_info = info
                    stage_key = key
                    break

        if not stage_info:
            return {}

        # 🔥 获取爽点单元
        payoff_unit = self._get_payoff_unit_for_chapter(chapter_number, stage_info)

        if payoff_unit:
            # 使用爽点单元上下文
            return {
                "stage_name": stage_names.get(stage_key, stage_key),
                "stage_chapter_range": stage_info.get("chapter_range", ""),
                "stage_goal": stage_info.get("stage_goal") or stage_info.get("core_payoff", ""),
                # 爽点单元信息
                "payoff_unit_name": payoff_unit.get("unit_name", ""),
                "payoff_unit_range": payoff_unit.get("chapter_range", ""),
                "core_payoff": payoff_unit.get("core_payoff", ""),
                "suppression_setup": payoff_unit.get("suppression_setup", ""),
                "emotional_arc": payoff_unit.get("emotional_arc", ""),
                "key_beats": payoff_unit.get("key_beats", []),
                "role_in_stage": payoff_unit.get("role_in_stage", ""),
            }
        else:
            # fallback: 使用大阶段信息
            return {
                "stage_name": stage_names.get(stage_key, stage_key),
                "stage_chapter_range": stage_info.get("chapter_range", ""),
                "stage_goal": stage_info.get("stage_goal") or stage_info.get("core_payoff", ""),
                "core_payoff": stage_info.get("core_payoff") or stage_info.get("stage_goal", ""),
                "key_beats": stage_info.get("key_developments") or stage_info.get("key_events", []),
            }

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
