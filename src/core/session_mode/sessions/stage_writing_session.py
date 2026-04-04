"""
Stage Writing Session - 阶段写作会话
负责: 按阶段生成章节正文
"""

import json
from typing import Dict, Optional, Any, List

from src.core.session_mode.novel_generation_session import NovelGenerationSession


class StageWritingSession(NovelGenerationSession):
    """阶段写作会话"""

    STEPS = ["stage_outline", "chapter_writing", "stage_summary"]

    def __init__(self, *args, stage_number: int = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_number = stage_number
        self.results: Dict[str, Any] = {}
        self.generated_chapters: Dict[int, Dict] = {}
        self.stage_summary_text: str = ""

    def _get_domain_chinese_name(self) -> str:
        return f"阶段写作（第 {self.stage_number} 阶段）"

    def execute_all_steps(self) -> bool:
        """执行 Stage Writing 域的所有步骤"""
        self.session_logger.info(f"[StageWritingSession-{self.stage_number}] 开始执行步骤...")

        # Step 1: 生成/精炼阶段细纲
        outline = self._execute_stage_outline()
        if not outline:
            self.session_logger.error(f"[StageWritingSession-{self.stage_number}] 阶段细纲生成失败")
            return False
        self.results["stage_outline"] = outline

        # Step 2: 逐章生成正文
        chapter_success = self._execute_chapter_writing(outline)
        if not chapter_success:
            self.session_logger.error(f"[StageWritingSession-{self.stage_number}] 章节正文生成失败")
            return False

        # Step 3: 生成阶段总结
        summary = self._execute_stage_summary()
        if summary:
            self.stage_summary_text = summary

        self.session_logger.info(f"[StageWritingSession-{self.stage_number}] 所有步骤执行完成")
        return True

    def _get_stage_plan(self) -> Optional[Dict]:
        """获取当前阶段的计划"""
        overall = self.novel_data.get("overall_stage_plans", {})
        stages = overall.get("stages", []) if isinstance(overall, dict) else []
        
        for stage in stages:
            if stage.get("stage_number") == self.stage_number:
                return stage
        return None

    def _get_stage_writing_plan(self) -> Optional[Dict]:
        """获取当前阶段的详细写作计划"""
        stage_plans = self.novel_data.get("stage_writing_plans", {})
        stage = self._get_stage_plan()
        if not stage:
            return None
        stage_name = stage.get("stage_name", f"阶段{self.stage_number}")
        return stage_plans.get(stage_name)

    def _execute_stage_outline(self) -> Optional[Dict]:
        """执行步骤1: 生成阶段细纲"""
        stage = self._get_stage_plan()
        writing_plan = self._get_stage_writing_plan()

        if not stage:
            self.session_logger.error(f"未找到第 {self.stage_number} 阶段的计划")
            return None

        stage_name = stage.get("stage_name", f"阶段{self.stage_number}")
        chapter_range = stage.get("chapter_range", "未知")
        key_events = stage.get("key_events", [])

        # 提取已有的 chapter_breakdown 作为参考
        existing_breakdown = []
        if writing_plan and isinstance(writing_plan, dict):
            existing_breakdown = writing_plan.get("chapter_breakdown", [])

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "stage_outline",
            default="",
            stage_name=stage_name,
            chapter_range=chapter_range,
            key_events=json.dumps(key_events, ensure_ascii=False, indent=2),
            existing_breakdown=json.dumps(existing_breakdown, ensure_ascii=False, indent=2)
        )
        
        if not prompt:
            self.session_logger.error(f"[StageWritingSession-{self.stage_number}] 未找到 stage_outline 提示词模板")
            return None
            
        return self.send_structured_message(prompt, purpose="stage_outline")

    def _execute_chapter_writing(self, outline: Dict) -> bool:
        """执行步骤2: 逐章生成正文"""
        chapters = outline.get("chapters", [])
        if not chapters:
            self.session_logger.error("细纲中没有章节信息")
            return False

        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 200)
        writing_style = self.novel_data.get("writing_style_guide", {})
        core_style = writing_style.get("core_style", "")
        key_principles = writing_style.get("key_principles", [])

        for chapter_info in chapters:
            chapter_num = chapter_info.get("chapter_num")
            if not chapter_num:
                continue

            self.session_logger.info(f"正在生成第 {chapter_num} 章...")

            # 获取前一章结尾（用于上下文衔接）
            previous_ending = ""
            if chapter_num > 1 and (chapter_num - 1) in self.generated_chapters:
                prev_content = self.generated_chapters[chapter_num - 1].get("content", "")
                # 提取最后 300 字作为上下文
                previous_ending = prev_content[-300:] if len(prev_content) > 300 else prev_content

            previous_ending_section = f"\n## 上一章结尾上下文\n{previous_ending}\n" if previous_ending else ""
            
            prompt = f"""
请执行【步骤2：生成第 {chapter_num} 章正文】

## 本章信息
- 章节号: 第 {chapter_num} 章 / 全书 {total_chapters} 章
- 标题: {chapter_info.get('title', '待定')}
- 关键事件: {chapter_info.get('key_events', '')}
- 情绪节奏: {chapter_info.get('emotional_beats', '')}
- 剧情推进点: {chapter_info.get('plot_progression', '')}
- 悬念设置: {chapter_info.get('suspense_setup', '')}

## 写作风格约束
- 核心风格: {core_style}
- 核心原则: {key_principles}
{previous_ending_section}
## 输出要求
请直接输出本章正文内容，约 2500-3500 字。
要求：
1. 情节紧凑，符合细纲要求
2. 与上一章自然衔接（如果有）
3. 保留本章应有的悬念或爽点
4. 符合给定的写作风格
5. 不要输出 JSON，直接输出正文
"""
            content = self.send_message(prompt, purpose=f"chapter_{chapter_num}")
            if not content:
                self.session_logger.error(f"第 {chapter_num} 章生成失败")
                return False

            self.generated_chapters[chapter_num] = {
                "chapter_number": chapter_num,
                "chapter_title": chapter_info.get("title", f"第{chapter_num}章"),
                "content": content,
                "stage_number": self.stage_number,
            }

        return True

    def _execute_stage_summary(self) -> Optional[str]:
        """执行步骤3: 生成阶段总结"""
        chapter_titles = [
            f"第{num}章: {data['chapter_title']}"
            for num, data in sorted(self.generated_chapters.items())
        ]

        from src.prompts.Prompts import Prompts
        prompts = Prompts()
        prompt = prompts.format(
            "stage_summary",
            default="",
            stage_number=self.stage_number,
            chapter_titles=chr(10).join(chapter_titles)
        )
        
        if not prompt:
            self.session_logger.error(f"[StageWritingSession-{self.stage_number}] 未找到 stage_summary 提示词模板")
            return ""
            
        return self.send_message(prompt, purpose="stage_summary")

    def get_generated_chapters(self) -> Dict[int, Dict]:
        """获取已生成的章节"""
        return self.generated_chapters

    def get_stage_summary(self) -> str:
        """获取阶段总结"""
        return self.stage_summary_text
