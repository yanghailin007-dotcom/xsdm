"""
ChapterBatchSession - 章节批次对话会话

核心职责：
1. 在单一会话中生成一个爽点单元批次（默认4章）
2. 利用对话历史保持上下文连贯性
3. 批次内质检 + 总结

架构：
- 继承 NovelGenerationSession（底层 ConversationSession 自动维护对话历史）
- System Prompt = Layer 1-4（核心设定+爽点单元上下文+题材技法+文风）
- User Prompt = Layer 5-6（AI约束+情绪曲线+自检清单）+ 任务指令
- 批次首章额外注入完整核心设定圣经

复用：
- V2 prompt layers（通过 src.core.chapter_engine.prompt_layers）
- NovelGenerationSession（对话管理、JSON解析、Brief生成）
"""

import json
import re
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from src.core.session_mode.novel_generation_session import NovelGenerationSession
from src.core.chapter_engine.prompt_layers import (
    get_emotion_curve_text,
    get_emotion_curve_for_role,
    infer_chapter_role,
    get_chapter_type_from_role,
    CHAPTER_ROLES,
    GenreTechniquesLoader,
    WritingStyleLoader,
    AIConstraintsLoader,
    SelfCheckLoader,
)
from src.core.chapter_engine.types import ChapterSpec, GeneratedChapter

logger = logging.getLogger("ChapterBatchSession")


class ChapterBatchSession(NovelGenerationSession):
    """
    章节批次对话会话

    一个 session 负责生成一个批次（默认4章）的章节内容。
    利用对话历史保持风格一致性和情节连贯性。
    """

    STEPS = ["chapter_batch_generation"]

    def __init__(
        self,
        api_client,
        novel_data: Optional[Dict] = None,
        context_briefs: Optional[List[str]] = None,
        batch_start_chapter: int = 1,
        batch_size: int = 4,
        stage_context: Optional[Dict] = None,
        provider: str = "kimi",
        model_name: str = "kimi-k2.5",
        temperature: float = 0.9,
        word_count_min: int = 2000,
        word_count_max: int = 2500,
    ):
        """
        初始化章节批次对话会话

        Args:
            api_client: APIClient 实例
            novel_data: 小说数据（含 overall_stage_plans、character_design 等）
            context_briefs: 上游 Context Brief（上一批次的总结）
            batch_start_chapter: 批次起始章节号
            batch_size: 批次大小（默认4章）
            stage_context: 大阶段上下文（爽点单元信息）
            provider: 模型提供商
            model_name: 模型名称
            temperature: 温度参数
            word_count_min: 最小字数
            word_count_max: 最大字数
        """
        self.batch_start_chapter = batch_start_chapter
        self.batch_size = batch_size
        self.stage_context = stage_context or {}
        self.word_count_min = word_count_min
        self.word_count_max = word_count_max
        self.core_setting_full = ""  # 完整核心设定圣经（批次首章注入）
        self.generated_chapters: List[GeneratedChapter] = []
        self.batch_summary: Optional[Dict] = None

        # 加载V2 layers
        self._load_v2_layers(novel_data)

        # 调用父类 __init__（构建 system_prompt）
        super().__init__(
            api_client=api_client,
            domain="writing",
            context_briefs=context_briefs or [],
            novel_data=novel_data or {},
            provider=provider,
            model_name=model_name,
            temperature=temperature,
        )

        # 覆盖 max_history：批次需要更多历史（4章+质检+总结 ≈ 8-10轮）
        self.max_history = 30

        logger.info(
            f"[ChapterBatchSession] 创建完成 | 批次: {batch_start_chapter}-{batch_start_chapter + batch_size - 1} | "
            f"模型: {model_name} | 历史限制: {self.max_history}"
        )

    # =====================================================================
    # 覆盖父类方法：System Prompt 构建
    # =====================================================================

    def _get_role_prompt(self) -> str:
        """角色定位：顶级网文写手"""
        return """# 角色定位
你是一位顶级的网络小说执笔创作专家，擅长爽文创作。
你的任务是为小说生成高质量章节内容，确保情节紧凑、情绪到位、人设一致。
你精通番茄小说平台的爽文套路，深谙打脸、爆发、收获、危机等爽点节奏。"""

    def _get_constraint_prompt(self) -> str:
        """当前会话规则"""
        constraints = [
            "1. 每章输出必须包含 ---标题--- 和 ---正文--- 标记",
            f"2. 字数严格控制在 {self.word_count_min}-{self.word_count_max} 字之间（绝对禁止超过{self.word_count_max}字）",
            "3. 使用第三人称叙述视角",
            "4. 章尾必须留钩子（悬念/转折/期待），位于最后50字内",
            "5. 段落: 每段3-4行，多用换行，平均长度50-80字",
            "6. 对话: 对话占比≥30%，用引号\"\"包裹，一句一段",
            "7. 节奏: 短句(<10字)占比≥40%，单句最长25字",
            "8. 禁止连续150字无对话",
            "9. 禁止元文本、作者旁白、\"本章结束\"等提示",
            "10. 所有输出只包含章节正文，不要输出大纲或分析",
        ]
        return "## 当前会话规则（必须遵守）\n" + "\n".join(constraints)

    def _get_output_format_prompt(self) -> str:
        """输出格式要求"""
        return """## 输出格式要求
每章输出格式如下：

---第N章 章节标题---

（正文内容，2000-2500字）

注意：
- 必须包含 ---第N章 标题--- 标记
- 标题和正文之间空一行
- 不要在正文中出现章节标记"""

    def _build_system_prompt(self) -> str:
        """
        构建 System Prompt = Layer 1-4 + 爽点单元上下文
        """
        parts = []

        # 1. 角色定位
        parts.append(self._get_role_prompt())

        # 2. 小说基础信息
        parts.append(self._get_novel_info_prompt())

        # 3. 上游 Context Briefs
        if self.context_briefs:
            parts.append(self._get_context_briefs_prompt())

        # 4. 爽点单元上下文（Layer 2 战术规划）
        parts.append(self._build_stage_context_prompt())

        # 5. 题材技法（Layer 3）
        parts.append(self._build_genre_techniques_prompt())

        # 6. 文风技法（Layer 4）
        parts.append(self._build_writing_style_prompt())

        # 7. 自约束机制
        parts.append(self._get_constraint_prompt())

        # 8. 输出格式
        parts.append(self._get_output_format_prompt())

        return "\n\n".join(parts)

    def _build_stage_context_prompt(self) -> str:
        """构建爽点单元上下文 prompt"""
        if not self.stage_context:
            return "## 当前爽点单元上下文\n（暂无详细规划，请根据已有设定合理发挥）"

        stage_name = self.stage_context.get("stage_name", "未命名阶段")
        stage_range = self.stage_context.get("stage_chapter_range", "未知")
        stage_goal = self.stage_context.get("stage_goal", "")

        # 爽点单元信息
        payoff_unit_name = self.stage_context.get("payoff_unit_name", "")
        payoff_unit_range = self.stage_context.get("payoff_unit_range", "")
        core_payoff = self.stage_context.get("core_payoff", "")
        suppression_setup = self.stage_context.get("suppression_setup", "")
        emotional_arc = self.stage_context.get("emotional_arc", "")
        key_beats = self.stage_context.get("key_beats", [])
        role_in_stage = self.stage_context.get("role_in_stage", "")

        lines = [
            "## 当前爽点单元上下文（Layer 2 战术规划）",
            f"- 所属大阶段: {stage_name}（章节范围: {stage_range}）",
        ]
        if stage_goal:
            lines.append(f"- 阶段目标: {stage_goal}")

        lines.append("")
        lines.append("### 爽点单元详情")
        if payoff_unit_name:
            lines.append(f"- 单元名称: {payoff_unit_name}（{payoff_unit_range}）")
        if role_in_stage:
            lines.append(f"- 阶段定位: {role_in_stage}")
        if core_payoff:
            lines.append(f"- 核心爽点: {core_payoff}")
        if suppression_setup:
            lines.append(f"- 压抑铺垫: {suppression_setup}")
        if emotional_arc:
            lines.append(f"- 情绪弧线: {emotional_arc}")

        if key_beats:
            lines.append("- 关键节拍:")
            for beat in key_beats:
                lines.append(f"  • {beat}")

        return "\n".join(line for line in lines if line)

    def _build_genre_techniques_prompt(self) -> str:
        """构建题材技法 prompt（Layer 3）"""
        try:
            genre_data = self.genre_loader.load(self.genre)
            # 简化为文本格式（不依赖V2的完整renderer）
            lines = ["## 题材技法（Layer 3）"]
            if hasattr(genre_data, 'shock_steps') and genre_data.shock_steps:
                lines.append("### 震惊流技法")
                for step in genre_data.shock_steps:
                    lines.append(f"- {step.name}: {step.description}")
            if hasattr(genre_data, 'barrage_rules') and genre_data.barrage_rules:
                lines.append("### 弹幕/评论流")
                for rule in genre_data.barrage_rules:
                    lines.append(f"- {rule}")
            if hasattr(genre_data, 'forbidden') and genre_data.forbidden:
                lines.append("### 题材禁忌")
                for f in genre_data.forbidden:
                    desc = f.description if hasattr(f, 'description') else str(f)
                    lines.append(f"- 🚫 {desc}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"加载题材技法失败: {e}")
            return "## 题材技法（Layer 3）\n（加载失败，使用通用爽文技法）"

    def _build_writing_style_prompt(self) -> str:
        """构建文风技法 prompt（Layer 4）"""
        try:
            style_data = self.style_loader.load()
            lines = ["## 文风技法（Layer 4）"]

            # 段落规范
            if hasattr(style_data, 'paragraph') and style_data.paragraph:
                p = style_data.paragraph
                lines.append(f"### 段落规范")
                if hasattr(p, 'avg_length'):
                    lines.append(f"- 平均长度: {p.avg_length}")
                if hasattr(p, 'max_lines'):
                    lines.append(f"- 最大行数: {p.max_lines}")

            # 句子规范
            if hasattr(style_data, 'sentence') and style_data.sentence:
                s = style_data.sentence
                lines.append(f"### 句子规范")
                if hasattr(s, 'short_ratio'):
                    lines.append(f"- 短句占比: {s.short_ratio}")
                if hasattr(s, 'max_length'):
                    lines.append(f"- 最大长度: {s.max_length}")

            # 对话规范
            if hasattr(style_data, 'dialogue') and style_data.dialogue:
                d = style_data.dialogue
                lines.append(f"### 对话规范")
                if hasattr(d, 'wrapper'):
                    lines.append(f"- 包裹方式: {d.wrapper}")
                if hasattr(d, 'min_ratio'):
                    lines.append(f"- 最小占比: {d.min_ratio}")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"加载文风技法失败: {e}")
            return "## 文风技法（Layer 4）\n（加载失败，使用通用番茄爽文风格）"

    def _load_v2_layers(self, novel_data: Optional[Dict]):
        """加载V2 layers"""
        self.genre = novel_data.get("category", "都市") if novel_data else "都市"
        self.genre_loader = GenreTechniquesLoader()
        self.style_loader = WritingStyleLoader()
        self.constraints_loader = AIConstraintsLoader()
        self.selfcheck_loader = SelfCheckLoader()

    # =====================================================================
    # 核心方法：批次生成
    # =====================================================================

    def generate_batch(self, specs: List[ChapterSpec]) -> List[GeneratedChapter]:
        """
        生成批次内所有章节

        Args:
            specs: 章节规格列表（长度应 ≤ batch_size）

        Returns:
            GeneratedChapter 列表
        """
        chapters = []
        for i, spec in enumerate(specs):
            is_first = (i == 0)
            chapter = self._generate_single_chapter(spec, is_first)
            if chapter:
                chapters.append(chapter)
                self.generated_chapters.append(chapter)
            else:
                logger.error(f"第{spec.chapter_number}章生成失败")
        return chapters

    def _generate_single_chapter(
        self, spec: ChapterSpec, is_first: bool = False
    ) -> Optional[GeneratedChapter]:
        """
        生成单章（在同一会话中发送消息）

        Args:
            spec: 章节规格
            is_first: 是否为批次首章（注入完整核心设定）

        Returns:
            GeneratedChapter 或 None
        """
        chapter_number = spec.chapter_number
        title = spec.title or f"第{chapter_number}章"

        # 推断章节角色和情绪曲线
        role = infer_chapter_role(
            chapter_index_in_batch=chapter_number - self.batch_start_chapter,
            batch_size=self.batch_size,
        )
        chapter_type = get_chapter_type_from_role(role)
        emotion_curve_text = get_emotion_curve_for_role(role)

        # 构建任务指令（User Prompt）
        task_prompt = self._build_chapter_prompt(
            spec=spec,
            role=role,
            chapter_type=chapter_type,
            emotion_curve=emotion_curve_text,
            is_first=is_first,
        )

        logger.info(f"[批次会话] 生成第{chapter_number}章 | 角色: {role} | 类型: {chapter_type}")

        # 发送消息（利用对话历史）
        response = self.send_message(
            user_prompt=task_prompt,
            temperature=self.temperature,
            purpose=f"chapter_{chapter_number}",
        )

        if not response:
            logger.error(f"第{chapter_number}章 API 返回空")
            return None

        # 解析响应
        parsed = self._parse_chapter_response(response, chapter_number)
        if not parsed:
            logger.error(f"第{chapter_number}章解析失败")
            return None

        content = parsed.get("content", "")

        # 🔥 字数超标：让AI自己精简。如果精简失败，返回原文（不截断，避免情节断裂）
        if len(content) > self.word_count_max:
            logger.warning(
                f"第{chapter_number}章字数超标: {len(content)}字 > 上限{self.word_count_max}字，发送精简指令"
            )
            compressed = self._ask_ai_to_compress(content, chapter_number)
            if len(compressed) <= self.word_count_max:
                content = compressed
                logger.info(f"第{chapter_number}章AI精简成功: {len(content)}字")
            else:
                logger.warning(
                    f"第{chapter_number}章AI精简失败({len(compressed)}字)，保留原文({len(content)}字)等后续修复"
                )
                # 不截断，保留原文

        # 字数不足警告（不拦截，因为AI容易写不够）
        if len(content) < self.word_count_min:
            logger.warning(
                f"第{chapter_number}章字数不足: {len(content)}字 < 下限{self.word_count_min}字"
            )

        return GeneratedChapter(
            chapter_number=chapter_number,
            title=parsed.get("title", title),
            content=content,
            word_count=len(content),
        )

    def _ask_ai_to_compress(self, content: str, chapter_number: int) -> str:
        """
        让AI自己精简内容到目标字数以内。
        如果精简后仍超标，外层会保留原文，不做截断。
        """
        compress_prompt = f"""【字数死刑通知】

你刚才写的第{chapter_number}章严重超标：{len(content)}字。
系统硬性限制：{self.word_count_max}字。超过部分会被直接丢弃，导致情节断裂。

【必须执行】
1. 将内容压缩到 {self.word_count_max} 字以内，这是死命令
2. 保留：核心情节、关键对话1-2句、高潮动作、章尾钩子
3. 删除：所有环境描写、所有心理活动、所有过渡叙述、所有非关键配角
4. 每个场景用1-2句话推进，不要展开

【输出格式】
直接输出压缩后的正文，不要标题、不要分析、不要说明。

请立即执行压缩："""

        try:
            response = self.send_message(
                user_prompt=compress_prompt + "\n\n" + content,
                temperature=0.3,
                purpose=f"compress_chapter_{chapter_number}",
            )
            if response:
                parsed = self._parse_chapter_response(response, chapter_number)
                if parsed and parsed.get("content"):
                    return parsed.get("content", "").strip()
        except Exception as e:
            logger.error(f"AI精简第{chapter_number}章失败: {e}")

        # 精简失败，返回原文
        return content

    def _emergency_truncate(self, content: str, max_len: int) -> str:
        """
        极端兜底截断：只有当AI完全失控（如5000+字）且无法精简时才使用。
        优先在段落边界截断，避免截断在句子中间。
        """
        if len(content) <= max_len:
            return content
        truncated = content[:max_len]
        last_para_break = truncated.rfind('\n\n')
        if last_para_break > max_len * 0.8:
            truncated = truncated[:last_para_break]
        else:
            last_line_break = truncated.rfind('\n')
            if last_line_break > max_len * 0.8:
                truncated = truncated[:last_line_break]
            else:
                last_period = truncated.rfind('。')
                if last_period > max_len * 0.8:
                    truncated = truncated[:last_period + 1]
        return truncated.strip()

    def _get_current_payoff_context(self, chapter_number: int) -> Dict[str, Any]:
        """
        根据章节号从 novel_data 中动态查询当前爽点单元上下文。
        避免整批次共用一个过期的 stage_context。
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

        # 获取爽点单元列表（优先从缓存读取）
        payoff_units = []
        cached = self.novel_data.get("_payoff_units", {}).get(stage_key)
        if cached:
            payoff_units = cached
        else:
            # fallback: 从 stage_info 中读取
            payoff_units = stage_info.get("payoff_units", []) or stage_info.get("爽点单元", [])

        # 找到覆盖当前章节号的爽点单元
        payoff_unit = None
        for unit in payoff_units:
            cr = unit.get("chapter_range", "")
            numbers = re.findall(r'\d+', cr)
            if len(numbers) >= 2:
                start, end = int(numbers[0]), int(numbers[1])
                if start <= chapter_number <= end:
                    payoff_unit = unit
                    break

        result = {
            "stage_name": stage_names.get(stage_key, stage_key),
            "stage_chapter_range": stage_info.get("chapter_range", ""),
            "stage_goal": stage_info.get("stage_goal") or stage_info.get("core_payoff", ""),
        }

        if payoff_unit:
            result.update({
                "payoff_unit_name": payoff_unit.get("unit_name", ""),
                "payoff_unit_range": payoff_unit.get("chapter_range", ""),
                "core_payoff": payoff_unit.get("core_payoff", ""),
                "suppression_setup": payoff_unit.get("suppression_setup", ""),
                "emotional_arc": payoff_unit.get("emotional_arc", ""),
                "key_beats": payoff_unit.get("key_beats", []),
                "role_in_stage": payoff_unit.get("role_in_stage", ""),
            })
        else:
            # fallback: 使用大阶段信息
            result["core_payoff"] = stage_info.get("core_payoff") or stage_info.get("stage_goal", "")
            result["key_beats"] = stage_info.get("key_developments") or stage_info.get("key_events", [])

        return result

    def _build_chapter_prompt(
        self,
        spec: ChapterSpec,
        role: str,
        chapter_type: str,
        emotion_curve: str,
        is_first: bool = False,
    ) -> str:
        """
        构建单章任务指令（User Prompt = Layer 5 + 6 + 任务指令）
        """
        lines = []

        # Layer 5: AI约束 + 情绪曲线
        lines.append("## 第{}章创作指令".format(spec.chapter_number))
        lines.append("")
        lines.append("### 本章概要")
        lines.append(spec.outline or "（请根据上下文合理发挥）")
        lines.append("")

        # 🔥 前章衔接（同批次内已生成章节的摘要）
        if self.generated_chapters:
            recent = self.generated_chapters[-2:]  # 最近1-2章
            lines.append("### 前章衔接（本批次已生成章节摘要）")
            for ch in recent:
                lines.append(f"- 第{ch.chapter_number}章《{ch.title}》结尾状态:")
                # 提取最后100字作为结尾摘要
                ending = ch.content[-150:] if len(ch.content) > 150 else ch.content
                lines.append(f"  {ending}")
            lines.append("【要求】本章必须自然衔接上述结尾，保持剧情连贯")
            lines.append("")

        # 情绪曲线
        lines.append(emotion_curve)
        lines.append("")

        # 字数约束
        lines.append("### AI约束")
        lines.append(f"- 字数要求: {self.word_count_min}-{self.word_count_max}字")
        lines.append(f"- 章节类型: {chapter_type}")
        lines.append(f"- 章节角色: {CHAPTER_ROLES.get(role, {}).get('name', role)}")
        lines.append("- 格式: ---第N章 标题--- 标记")
        lines.append("- 第三人称叙述")
        lines.append("")
        lines.append("### 【字数死刑规定 - 必须遵守】")
        lines.append(f"- 你的输出会被硬性截断到{self.word_count_max}字")
        lines.append("- 超过部分直接丢弃，情节会断裂")
        lines.append("- 每个场景只用1-2句话推进，不要展开描写")
        lines.append("- 环境描写控制在1句以内，心理活动控制在1句以内")
        lines.append("- 对话每句不超过15字，一段对话只保留最关键的1-2轮")
        lines.append("- 如果字数超标，系统会强制删除后半段，你的故事就烂了")
        lines.append("")

        # 批次首章注入完整核心设定
        if is_first and self.core_setting_full:
            lines.append("【核心设定圣经 - 本批次必须严格遵守】")
            lines.append(self.core_setting_full)
            lines.append("=" * 60)
            lines.append("")

        # 🔥 当前爽点单元上下文（动态查询，避免整批次共用过期信息）
        payoff_ctx = self._get_current_payoff_context(spec.chapter_number)
        if payoff_ctx:
            lines.append("【当前爽点单元上下文 - 本章必须服务此单元目标】")
            lines.append(f"- 所属阶段: {payoff_ctx.get('stage_name', '')} ({payoff_ctx.get('stage_chapter_range', '')})")
            lines.append(f"- 爽点单元: {payoff_ctx.get('payoff_unit_name', '')} ({payoff_ctx.get('payoff_unit_range', '')})")
            lines.append(f"- 核心爽点: {payoff_ctx.get('core_payoff', '')}")
            if payoff_ctx.get('suppression_setup'):
                lines.append(f"- 压抑铺垫: {payoff_ctx.get('suppression_setup', '')}")
            if payoff_ctx.get('emotional_arc'):
                lines.append(f"- 情绪弧线: {payoff_ctx.get('emotional_arc', '')}")
            if payoff_ctx.get('key_beats'):
                beats = payoff_ctx.get('key_beats', [])
                if isinstance(beats, list):
                    lines.append(f"- 关键节拍: {' → '.join(str(b) for b in beats)}")
            # 🔥 场景设计下沉：根据章节在爽点单元中的位置，分配具体节拍任务
            pu_range = payoff_ctx.get("payoff_unit_range", "")
            beats = payoff_ctx.get("key_beats", [])
            if pu_range and beats and isinstance(beats, list) and len(beats) > 0:
                numbers = re.findall(r'\d+', pu_range)
                if len(numbers) >= 2:
                    pu_start, pu_end = int(numbers[0]), int(numbers[1])
                    total_in_unit = pu_end - pu_start + 1
                    if total_in_unit > 0:
                        rel_pos = spec.chapter_number - pu_start  # 0-based
                        if len(beats) >= total_in_unit:
                            beat_idx = min(rel_pos, len(beats) - 1)
                        else:
                            beat_idx = min(int(rel_pos * len(beats) / total_in_unit), len(beats) - 1)
                        chapter_beat = beats[beat_idx]
                        lines.append(f"- 本章任务: 负责关键节拍「{chapter_beat}」")
                        if beat_idx + 1 < len(beats):
                            lines.append(f"- 下章预告: 将过渡至「{beats[beat_idx + 1]}」")
            lines.append("【要求】本章内容必须服务于上述爽点单元目标，不能偏离")
            lines.append("")

        # 战术指令
        lines.append("### 战术指令")
        lines.append(f"- 核心事件: {spec.outline or '根据爽点单元上下文推进'}")

        # 如果是 golden chapter（前3章）额外要求
        if spec.is_golden_chapter:
            lines.append("- 🔥 黄金三章：本章节是小说的开篇/关键章节，必须极具吸引力")
            lines.append("  - 前500字必须有强钩子")
            lines.append("  - 主角必须在第一章出场")
            lines.append("  - 金手指必须在三章内出现")

        lines.append("- 结尾钩子: 章尾必须留悬念或期待")
        lines.append("")

        # Layer 6: 自检清单
        lines.append("### 自检清单（输出前逐项确认）")
        lines.append("[ ] 主角行为符合人设？")
        lines.append("[ ] 金手指使用符合成长规划？")
        lines.append("[ ] 字数在范围内？")
        lines.append("[ ] 情绪曲线执行到位？")
        lines.append("[ ] 章尾有钩子？")
        lines.append("[ ] 没有元文本或作者旁白？")
        lines.append("")

        return "\n".join(lines)

    def _parse_chapter_response(self, response: str, chapter_number: int) -> Optional[Dict[str, str]]:
        """
        解析章节生成响应

        优先匹配 ---第N章 标题--- 格式
        """
        # 清理
        text = response.strip()

        # 优先匹配 ---第N章 标题---\n内容 格式
        pattern = re.compile(
            r'---\s*第\s*(\d+)\s*章\s+(.*?)\s*---\s*\n(.*)',
            re.DOTALL
        )
        match = pattern.search(text)
        if match:
            num = int(match.group(1))
            title = match.group(2).strip()
            content = match.group(3).strip()
            # 移除尾部可能的总结/分析
            content = self._sanitize_chapter_content(content)
            return {"title": title, "content": content}

        # fallback: 匹配 第N章 标题\n内容
        pattern2 = re.compile(
            r'第\s*(\d+)\s*章[：:\s]+(.*?)\n+(.*)',
            re.DOTALL
        )
        match2 = pattern2.search(text)
        if match2:
            title = match2.group(2).strip()
            content = match2.group(3).strip()
            content = self._sanitize_chapter_content(content)
            return {"title": title, "content": content}

        # 最终fallback：把整段当作正文，标题用默认
        content = self._sanitize_chapter_content(text)
        return {"title": f"第{chapter_number}章", "content": content}

    def _sanitize_chapter_content(self, content: str) -> str:
        """清理章节内容"""
        # 移除元文本
        content = re.sub(r'（.*?）', '', content)
        content = re.sub(r'\[.*?\]', '', content)
        # 移除章节结束标记
        content = re.sub(r'本章完[。]?', '', content)
        content = re.sub(r'第\d+章\s*完', '', content)
        # 移除AI分析
        content = re.sub(r'(?:分析|总结|自检|检查).*?[：:].*?(?=\n|$)', '', content, flags=re.MULTILINE)
        # 🔥 移除正文内部残留的标题行（---第N章 标题--- 或 第N章 标题）
        content = re.sub(r'^---\s*第\s*\d+\s*章\s+.*?---\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'^第\s*\d+\s*章[：:\s]+.*?\n', '', content, flags=re.MULTILINE)
        return content.strip()

    # =====================================================================
    # 批次质检
    # =====================================================================

    def assess_batch_quality(self, chapters: List[GeneratedChapter]) -> Dict[str, Any]:
        """
        在同一会话中进行批次质检

        Args:
            chapters: 已生成的章节列表

        Returns:
            {"score": float, "can_proceed": bool, "feedback": str, "per_chapter": [...]}
        """
        if not chapters:
            return {"score": 0.0, "can_proceed": False, "feedback": "无内容", "per_chapter": []}

        # 构建质检 prompt
        content_block = "\n\n".join(
            f"### 第{ch.chapter_number}章 {ch.title}\n{ch.content[:600]}"
            for ch in chapters
        )

        prompt = f"""请对以下批次章节进行质量评估。你是质检编辑，严格把关。

{content_block}

【评估维度】
1. 流畅度 (0-10)：文字是否流畅，有无语病
2. 情节连贯性 (0-10)：批次内章节是否衔接自然
3. 人设一致性 (0-10)：主角行为是否符合设定
4. 爽点/吸引力 (0-10)：是否具备爽文吸引力
5. 对话质量 (0-10)：对话是否自然、有张力

【输出格式】
请输出如下 JSON（不要添加 markdown 代码块标记）：
{{
  "overall_score": 7.5,
  "can_proceed": true,
  "feedback": "具体问题和改进建议",
  "per_chapter": [
    {{"chapter": 1, "score": 8.0, "issues": "..."}},
    {{"chapter": 2, "score": 7.0, "issues": "..."}}
  ]
}}

JSON:"""

        logger.info(f"[批次会话] 开始质检（{len(chapters)}章）")

        response = self.send_message(
            user_prompt=prompt,
            temperature=0.3,
            purpose="batch_quality_assessment",
        )

        if not response:
            logger.warning("质检返回空，默认通过")
            return {"score": 6.0, "can_proceed": True, "feedback": "质检超时，默认通过", "per_chapter": []}

        # 解析JSON
        result = self._parse_json_response(response, "quality_assessment")
        if result:
            return {
                "score": float(result.get("overall_score", 6.0)),
                "can_proceed": bool(result.get("can_proceed", True)),
                "feedback": result.get("feedback", ""),
                "per_chapter": result.get("per_chapter", []),
            }

        # fallback
        return {"score": 6.0, "can_proceed": True, "feedback": "质检解析失败，默认通过", "per_chapter": []}

    def regenerate_chapter(self, spec: ChapterSpec, feedback: str) -> Optional[GeneratedChapter]:
        """
        在同一会话中重新生成某章（质检不达标时）

        Args:
            spec: 章节规格
            feedback: 质检反馈

        Returns:
            重新生成的章节
        """
        prompt = f"""上一章生成质量不达标，请重新生成。

【质检反馈】
{feedback}

【要求】
- 保持剧情连贯性（参考对话历史中的前文）
- 严格解决质检反馈中的问题
- 字数 {self.word_count_min}-{self.word_count_max} 字
- 格式：---第{spec.chapter_number}章 标题---

请重新生成第{spec.chapter_number}章。"""

        response = self.send_message(
            user_prompt=prompt,
            temperature=self.temperature,
            purpose=f"chapter_{spec.chapter_number}_regenerate",
        )

        if not response:
            return None

        parsed = self._parse_chapter_response(response, spec.chapter_number)
        if not parsed:
            return None

        return GeneratedChapter(
            chapter_number=spec.chapter_number,
            title=parsed.get("title", spec.title),
            content=parsed.get("content", ""),
            word_count=len(parsed.get("content", "")),
        )

    # =====================================================================
    # 批次总结与 Context Brief
    # =====================================================================

    def generate_batch_summary(self) -> Optional[Dict[str, Any]]:
        """
        在同一会话中生成批次总结

        Returns:
            批次总结字典
        """
        if not self.generated_chapters:
            return None

        # 构建总结 prompt
        chapter_summaries = "\n".join(
            f"- 第{ch.chapter_number}章 {ch.title}: {ch.content[:100]}..."
            for ch in self.generated_chapters
        )

        prompt = f"""请对当前批次章节生成总结报告。

【已生成章节摘要】
{chapter_summaries}

【输出格式】
请输出如下 JSON：
{{
  "summary_text": "本批次核心剧情进展（100字以内）",
  "completed_events": ["已完成的关键事件1", "事件2"],
  "character_states": {{"主角状态": "...", "关键角色变化": "..."}},
  "pending_hooks": ["遗留悬念1", "悬念2"],
  "world_changes": ["世界观变化1"],
  "next_batch_preview": "下批次预期剧情方向"
}}

JSON:"""

        response = self.send_structured_message(
            user_prompt=prompt,
            temperature=0.5,
            purpose="batch_summary",
        )

        if response:
            self.batch_summary = response
            return response

        return None

    def export_context_brief(self) -> str:
        """
        生成下游批次可用的 Context Brief

        Returns:
            Brief 文本
        """
        if self.batch_summary:
            # 基于 batch_summary 生成精简 brief
            parts = [
                f"## 上一批次总结（第{self.batch_start_chapter}-{self.batch_start_chapter + len(self.generated_chapters) - 1}章）",
                f"剧情进展: {self.batch_summary.get('summary_text', '')}",
                f"角色状态: {json.dumps(self.batch_summary.get('character_states', {}), ensure_ascii=False)}",
                f"遗留钩子: {', '.join(self.batch_summary.get('pending_hooks', []))}",
                f"下批预告: {self.batch_summary.get('next_batch_preview', '')}",
            ]
            return "\n".join(parts)

        # fallback
        return f"## 上一批次（第{self.batch_start_chapter}章起）\n（总结生成失败）"

    def set_core_setting(self, core_setting: str):
        """设置完整核心设定圣经（批次首章注入用）"""
        self.core_setting_full = core_setting
