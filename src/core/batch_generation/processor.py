# -*- coding: utf-8 -*-
"""
中型事件批量生成主处理器

协调场景生成、正文生成、质量评估的完整流程
实现按中型事件批量生成，减少API调用次数
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from .multi_chapter_generator import MultiChapterContentGenerator, ChapterContent
from .quality_assessor import LayeredQualityAssessor, AssessmentResult, AssessmentLevel
from .fallback_handler import BatchFallbackHandler, FallbackResult, FailureType
from .writing_style_loader import WritingStyleGuideLoader
from .golden_chapters import GoldenChaptersGenerator
from .golden_chapters_assessor import GoldenChaptersAssessor, GoldenChaptersAssessment

logger = logging.getLogger(__name__)


@dataclass
class BatchProcessResult:
    """批量处理结果"""
    success: bool
    chapters: Dict[int, ChapterContent] = field(default_factory=dict)
    assessment: Optional[AssessmentResult] = None
    api_calls_used: int = 0  # 实际使用的API调用次数（=创造点消耗）
    points_consumed: int = 0  # 消耗的创造点（1次API调用=1点）
    points_saved: int = 0  # 相比逐章生成节省的点数
    fallback_used: bool = False
    fallback_level: str = ""
    warnings: List[str] = field(default_factory=list)
    error: str = ""


class MediumEventBatchProcessor:
    """
    中型事件批量生成处理器
    
    核心流程:
    1. 检测中型事件章节跨度
    2. 批量生成场景（或复用已有场景）
    3. 批量生成正文（核心优化点）
    4. 分层质量评估
    5. [可选] 批量优化
    
    API调用优化:
    - 2-3章中型事件：1次场景 + 1次正文 + 1次评估 = 3次API（原需6-9次）
    - 节省约50-60%的API调用
    """
    
    def __init__(self, api_client, novel_generator=None):
        """
        初始化处理器
        
        Args:
            api_client: API客户端
            novel_generator: 小说生成器实例（用于获取世界状态等）
        """
        self.api_client = api_client
        self.novel_generator = novel_generator
        
        # 子组件
        self.content_generator = MultiChapterContentGenerator(api_client)
        self.golden_generator = GoldenChaptersGenerator(api_client)
        self.golden_assessor = GoldenChaptersAssessor(api_client)
        self.assessor = LayeredQualityAssessor(api_client)
        self.fallback_handler = BatchFallbackHandler(
            scene_generator=self,
            content_generator=self.content_generator,
            novel_generator=novel_generator
        )
        
        self.logger = logging.getLogger(__name__)
        
        # 统计
        self.stats = {
            "total_events": 0,
            "batch_success": 0,
            "fallback_count": 0,
            "api_calls_saved": 0
        }
    
    def process_medium_event(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        novel_data: Dict,
        context: Any = None,
        scenes_by_chapter: Optional[Dict[int, List[Dict]]] = None,
        skip_assessment: bool = False
    ) -> BatchProcessResult:
        """
        处理单个中型事件（批量生成）
        
        Args:
            medium_event: 中型事件数据
            chapter_range: (start_ch, end_ch) 章节范围
            novel_data: 小说数据（包含world_state, style_guide等）
            context: 生成上下文
            scenes_by_chapter: 预生成的场景（如有）
            skip_assessment: 是否跳过质量评估
            
        Returns:
            BatchProcessResult: 处理结果
        """
        start_ch, end_ch = chapter_range
        span = end_ch - start_ch + 1
        
        # 验证 medium_event 类型
        if not isinstance(medium_event, dict):
            self.logger.error(f"[BatchProcessor] medium_event 类型错误: {type(medium_event)}, 值: {medium_event}")
            return BatchProcessResult(
                success=False,
                error=f"medium_event 类型错误: 期望 dict, 得到 {type(medium_event)}"
            )
        
        # 调试：记录 medium_event 的内容
        self.logger.info(f"[BatchProcessor] medium_event 内容: {medium_event}")
        
        novel_title = novel_data.get("novel_title", "Unknown")
        username = novel_data.get("username")
        
        self.logger.info(
            f"[BatchProcessor] 开始处理中型事件: {medium_event.get('name', 'Unknown')} "
            f"第{start_ch}-{end_ch}章(共{span}章)"
        )
        
        # 特殊处理：黄金三章（第1-3章）必须整体生成
        if self._is_golden_chapters(chapter_range):
            self.logger.info(f"[BatchProcessor] 检测到黄金三章，使用整体生成模式")
            return self._process_golden_chapters(
                medium_event=medium_event,
                chapter_range=chapter_range,
                novel_data=novel_data,
                scenes_by_chapter=scenes_by_chapter,
                skip_assessment=skip_assessment
            )
        
        self.stats["total_events"] += 1
        
        # 获取API调用前的计数（用于计算实际消耗）
        api_calls_before = getattr(self.api_client, 'api_call_counter', 0)
        
        # 1. 获取或生成场景
        if not scenes_by_chapter:
            scenes_by_chapter = self._get_scenes_for_medium_event(
                medium_event, chapter_range, novel_data
            )
        
        # 2. 构建一致性指导
        consistency_guidance = self._build_consistency_guidance(
            novel_data, start_ch
        )
        
        # 3. 批量生成正文（核心优化）
        try:
            chapters_content = self.content_generator.generate(
                medium_event=medium_event,
                chapter_range=chapter_range,
                scenes_by_chapter=scenes_by_chapter,
                consistency_guidance=consistency_guidance,
                novel_title=novel_title,
                previous_state=self._get_previous_state(novel_data, start_ch),
                username=username
            )
            
            # 计算实际API调用次数（通过计数器差值）
            api_calls_after = getattr(self.api_client, 'api_call_counter', api_calls_before + 1)
            api_calls_used = api_calls_after - api_calls_before
            
        except Exception as e:
            import traceback
            self.logger.error(f"[BatchProcessor] 批量生成失败: {e}")
            self.logger.error(f"[BatchProcessor] 堆栈追踪:\n{traceback.format_exc()}")
            
            # 回退到逐章生成
            import asyncio
            fallback_result = asyncio.run(self.fallback_handler.handle_failure(
                failure_type=FailureType.CONTENT_GENERATION_FAILED,
                medium_event=medium_event,
                chapter_range=chapter_range,
                scenes_by_chapter=scenes_by_chapter,
                consistency_guidance=consistency_guidance,
                novel_title=novel_title,
                error_info=str(e)
            ))
            
            if not fallback_result.success:
                return BatchProcessResult(
                    success=False,
                    error=fallback_result.error or "批量生成和回退均失败"
                )
            
            # 转换回ChapterContent格式
            chapters_content = {}
            for ch_num, ch_data in fallback_result.chapters_content.items():
                chapters_content[ch_num] = ChapterContent(
                    chapter_number=ch_num,
                    title=ch_data.get("title", f"第{ch_num}章"),
                    content=ch_data.get("content", ""),
                    key_events=ch_data.get("key_events", []),
                    character_states=ch_data.get("character_states", {}),
                    items_delta=ch_data.get("items_delta", {}),
                    time_progression=ch_data.get("time_progression", "0天")
                )
            
            # 计算回退后的API调用次数
            api_calls_after = getattr(self.api_client, 'api_call_counter', api_calls_before)
            api_calls_used = api_calls_after - api_calls_before
            
            self.stats["fallback_count"] += 1
            
            return BatchProcessResult(
                success=True,
                chapters=chapters_content,
                api_calls_used=api_calls_used,
                points_consumed=api_calls_used,  # 1次API=1点
                points_saved=0,  # 回退后没有节省
                fallback_used=True,
                fallback_level=fallback_result.fallback_level,
                warnings=fallback_result.warnings
            )
        
        # 4. 质量评估（可选）
        assessment = None
        if not skip_assessment:
            api_calls_before_assessment = getattr(self.api_client, 'api_call_counter', 0)
            
            style_guide = WritingStyleGuideLoader.load_and_format(
                novel_title, username, use_cache=True
            )
            
            world_state_before = self._get_world_state_before(novel_data, start_ch)
            
            assessment = self.assessor.assess(
                chapters_content={
                    ch_num: {
                        "title": content.title,
                        "content": content.content,
                        "key_events": content.key_events,
                        "character_states": content.character_states,
                        "items_delta": content.items_delta,
                        "time_progression": content.time_progression
                    }
                    for ch_num, content in chapters_content.items()
                },
                medium_event=medium_event,
                world_state_before=world_state_before,
                style_guide={"key_principles": []},  # 简化传递
                novel_title=novel_title
            )
            
            # 计算评估消耗的API调用
            api_calls_after_assessment = getattr(self.api_client, 'api_call_counter', api_calls_before_assessment)
            assessment_calls = api_calls_after_assessment - api_calls_before_assessment
            api_calls_used += assessment_calls
        
        # 5. 计算节省的API调用和点数
        traditional_calls = span * 3  # 原：每章场景+正文+评估
        points_consumed = api_calls_used  # 1次API=1点
        points_saved = max(0, traditional_calls - api_calls_used)
        
        self.stats["api_calls_saved"] += points_saved
        self.stats["batch_success"] += 1
        
        self.logger.info(
            f"[BatchProcessor] 中型事件处理完成: {medium_event.get('name', 'Unknown')} "
            f"API调用:{api_calls_used}(消耗{points_consumed}创造点), "
            f"节省:{points_saved}点, "
            f"评估:{assessment.level.value if assessment else 'skipped'}"
        )
        
        return BatchProcessResult(
            success=True,
            chapters=chapters_content,
            assessment=assessment,
            api_calls_used=api_calls_used,
            points_consumed=points_consumed,
            points_saved=points_saved,
            fallback_used=False
        )
    
    def should_use_batch(self, chapter_range: Tuple[int, int]) -> bool:
        """
        判断是否应使用批量生成
        
        策略：
        - 单章（span=1）：逐章生成
        - 2-3章（span=2-3）：批量生成（最优）
        - 4+章（span>=4）：拆分为多个批次
        """
        start, end = chapter_range
        span = end - start + 1
        
        return span >= 2  # 2章及以上使用批量
    
    def split_large_event(
        self,
        chapter_range: Tuple[int, int],
        batch_size: int = 3
    ) -> List[Tuple[int, int]]:
        """
        将大型事件拆分为多个批次
        
        Args:
            chapter_range: (start, end) 原始章节范围
            batch_size: 每批最大章节数
            
        Returns:
            [(start1, end1), (start2, end2), ...] 拆分后的批次
        """
        start, end = chapter_range
        batches = []
        
        current = start
        while current <= end:
            batch_end = min(current + batch_size - 1, end)
            batches.append((current, batch_end))
            current = batch_end + 1
        
        return batches
    
    def _get_scenes_for_medium_event(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        novel_data: Dict
    ) -> Dict[int, List[Dict]]:
        """获取中型事件的场景（复用或生成）"""
        # 尝试从novel_data中获取已有场景
        stage_plans = novel_data.get("stage_writing_plans", {})
        
        # 这里简化处理，实际应从stage_plan_manager获取
        # 返回空，让上层处理场景生成
        return {}
    
    def _build_consistency_guidance(self, novel_data: Dict, start_chapter: int) -> str:
        """构建一致性指导"""
        # 从WorldStateManager获取状态
        if self.novel_generator and hasattr(self.novel_generator, 'world_state_manager'):
            return self.novel_generator.world_state_manager.build_consistency_guidance()
        
        # 简化版本
        guidance_parts = ["## 世界状态（截至上一章）"]
        
        # 角色状态
        characters = novel_data.get("character_status", {})
        if characters:
            guidance_parts.append("### 角色状态")
            for char, status in characters.items():
                guidance_parts.append(f"- {char}: {status}")
        
        return "\n".join(guidance_parts)
    
    def _get_previous_state(self, novel_data: Dict, chapter_num: int) -> Optional[Dict]:
        """获取前一中型事件的最终状态"""
        # 从WorldStateManager获取
        if self.novel_generator and hasattr(self.novel_generator, 'world_state_manager'):
            return self.novel_generator.world_state_manager.get_state_before_chapter(chapter_num)
        
        return None
    
    def _get_world_state_before(self, novel_data: Dict, chapter_num: int) -> Dict:
        """获取指定章节前的世界状态"""
        if self.novel_generator and hasattr(self.novel_generator, 'world_state_manager'):
            return self.novel_generator.world_state_manager.get_state_before_chapter(chapter_num)
        
        return {"characters": {}, "items": {}}
    
    def get_stats(self) -> Dict:
        """获取处理统计"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["batch_success"] / self.stats["total_events"]
                if self.stats["total_events"] > 0 else 0
            )
        }
    
    def reset_stats(self):
        """重置统计"""
        self.stats = {
            "total_events": 0,
            "batch_success": 0,
            "fallback_count": 0,
            "api_calls_saved": 0
        }
    
    def _is_golden_chapters(self, chapter_range: Tuple[int, int]) -> bool:
        """
        判断是否为黄金三章（第1-3章）
        
        黄金三章必须整体生成以保证连贯性
        """
        start_ch, end_ch = chapter_range
        # 包含第1章且至少到第2章
        return start_ch == 1 and end_ch >= 2
    
    def _process_golden_chapters(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        novel_data: Dict,
        scenes_by_chapter: Optional[Dict[int, List[Dict]]],
        skip_assessment: bool
    ) -> BatchProcessResult:
        """
        处理黄金三章（整体生成）
        
        第1-3章一次性生成，确保开篇连贯性
        """
        novel_title = novel_data.get("novel_title", "Unknown")
        username = novel_data.get("username")
        
        # 获取API调用前的计数
        api_calls_before = getattr(self.api_client, 'api_call_counter', 0)
        
        try:
            # 使用黄金三章专用生成器
            chapters_content = self.golden_generator.generate(
                novel_data=novel_data,
                creative_seed=novel_data.get("creative_seed", {}),
                selected_plan=novel_data.get("selected_plan", {}),
                scenes_by_chapter=scenes_by_chapter,
                username=username
            )
            
            # 计算API调用消耗
            api_calls_after = getattr(self.api_client, 'api_call_counter', api_calls_before + 1)
            api_calls_used = api_calls_after - api_calls_before
            
            # 黄金三章的特殊统计
            self.stats["total_events"] += 1
            self.stats["batch_success"] += 1
            
            # 计算节省（原逐章需9点，批量约3-4点）
            traditional_calls = 9  # 3章 * 3
            points_saved = max(0, traditional_calls - api_calls_used)
            self.stats["api_calls_saved"] += points_saved
            
            self.logger.info(
                f"[BatchProcessor] 黄金三章整体生成完成: {novel_title} "
                f"消耗{api_calls_used}创造点, 节省{points_saved}点"
            )
            
            # 质量评估（黄金三章必须评估，使用专用评估器）
            assessment = None
            if not skip_assessment:
                golden_assessment = self._assess_golden_chapters(
                    chapters_content=chapters_content,
                    novel_data=novel_data
                )
                
                if golden_assessment:
                    assessment = golden_assessment
                    api_calls_used += 1  # 评估消耗1点
                    
                    # 如果评分低，记录改进建议
                    if golden_assessment.overall_score < 7.0:
                        self.logger.warning(
                            f"[BatchProcessor] 黄金三章评分偏低({golden_assessment.overall_score})，"
                            f"建议改进: {golden_assessment.improvement_suggestions[:2]}"
                        )
            
            return BatchProcessResult(
                success=True,
                chapters=chapters_content,
                assessment=assessment,
                api_calls_used=api_calls_used,
                points_consumed=api_calls_used,
                points_saved=points_saved,
                fallback_used=False
            )
            
        except Exception as e:
            self.logger.error(f"[BatchProcessor] 黄金三章整体生成失败: {e}")
            
            # 回退到逐章生成
            return self._fallback_golden_chapters(
                medium_event=medium_event,
                chapter_range=chapter_range,
                novel_data=novel_data,
                scenes_by_chapter=scenes_by_chapter,
                error=str(e)
            )
    
    def _assess_golden_chapters(
        self,
        chapters_content: Dict[int, ChapterContent],
        novel_data: Dict
    ) -> Optional[GoldenChaptersAssessment]:
        """
        黄金三章专用评估
        
        使用专门的评估器，侧重吸引力和类型卖点契合度
        """
        novel_title = novel_data.get("novel_title", "Unknown")
        
        self.logger.info(f"[BatchProcessor] 开始黄金三章专用评估: {novel_title}")
        
        try:
            assessment = self.golden_assessor.assess(
                chapters_content=chapters_content,
                novel_data=novel_data,
                creative_seed=novel_data.get("creative_seed", {}),
                selected_plan=novel_data.get("selected_plan", {})
            )
            
            self.logger.info(
                f"[BatchProcessor] 黄金三章评估完成: "
                f"总体{assessment.overall_score}分, "
                f"类型契合{assessment.type_match}分, "
                f"读者吸引{assessment.reader_attraction}分"
            )
            
            # 记录读者反馈
            for ch, reaction in assessment.reader_reactions.items():
                self.logger.info(f"  {ch}读者反馈: {reaction}")
            
            return assessment
            
        except Exception as e:
            self.logger.warning(f"[BatchProcessor] 黄金三章评估失败: {e}")
            return None
    
    def _fallback_golden_chapters(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        novel_data: Dict,
        scenes_by_chapter: Optional[Dict[int, List[Dict]]],
        error: str
    ) -> BatchProcessResult:
        """
        黄金三章生成失败回退
        
        即使回退，也尽量保持批量生成（2+1批次）
        """
        self.logger.warning(f"[BatchProcessor] 黄金三章回退: {error}")
        
        # 尝试2+1分批生成（第1-2章批量，第3章单独）
        try:
            # 第1-2章批量
            batch1_result = self.content_generator.generate(
                medium_event=medium_event,
                chapter_range=(1, 2),
                scenes_by_chapter={
                    k: v for k, v in (scenes_by_chapter or {}).items() if k in [1, 2]
                },
                consistency_guidance="",
                novel_title=novel_data.get("novel_title", "Unknown"),
                username=novel_data.get("username")
            )
            
            # 第3章单独
            batch2_result = self.content_generator.generate(
                medium_event=medium_event,
                chapter_range=(3, 3),
                scenes_by_chapter={
                    k: v for k, v in (scenes_by_chapter or {}).items() if k == 3
                },
                consistency_guidance="",
                novel_title=novel_data.get("novel_title", "Unknown"),
                username=novel_data.get("username")
            )
            
            # 合并结果
            all_chapters = {**batch1_result, **batch2_result}
            
            api_calls_used = 2  # 2次批量生成
            points_saved = 9 - (api_calls_used + 1)  # 原9点，现约3点
            
            self.stats["fallback_count"] += 1
            
            return BatchProcessResult(
                success=True,
                chapters=all_chapters,
                api_calls_used=api_calls_used,
                points_consumed=api_calls_used,
                points_saved=max(0, points_saved),
                fallback_used=True,
                fallback_level="golden_2plus1",
                warnings=["黄金三章整体生成失败，已回退到2+1分批生成"]
            )
            
        except Exception as e2:
            self.logger.error(f"[BatchProcessor] 黄金三章回退也失败: {e2}")
            return BatchProcessResult(
                success=False,
                error=f"黄金三章生成完全失败: {error}; 回退失败: {e2}"
            )


# 便捷函数
def process_medium_event_batch(
    api_client,
    medium_event: Dict,
    chapter_range: Tuple[int, int],
    novel_data: Dict,
    **kwargs
) -> BatchProcessResult:
    """
    便捷函数：处理中型事件批量生成
    
    使用示例:
    result = process_medium_event_batch(
        api_client=api_client,
        medium_event=event,
        chapter_range=(5, 7),
        novel_data=novel_data
    )
    
    if result.success:
        print(f"生成成功，使用API调用: {result.api_calls_used}")
        for ch_num, content in result.chapters.items():
            print(f"第{ch_num}章: {content.title}")
    """
    processor = MediumEventBatchProcessor(api_client)
    return processor.process_medium_event(
        medium_event=medium_event,
        chapter_range=chapter_range,
        novel_data=novel_data,
        **kwargs
    )
