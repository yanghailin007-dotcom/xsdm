# -*- coding: utf-8 -*-
"""
批量生成功能与ContentGenerator的集成适配器

提供与现有ContentGenerator的无缝集成
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

from .processor import MediumEventBatchProcessor, BatchProcessResult
from .writing_style_loader import WritingStyleGuideLoader

logger = logging.getLogger(__name__)


class BatchGenerationAdapter:
    """
    批量生成功能适配器
    
    为ContentGenerator提供批量生成能力的封装
    """
    
    def __init__(self, content_generator):
        """
        初始化适配器
        
        Args:
            content_generator: 现有的ContentGenerator实例
        """
        self.content_generator = content_generator
        self.api_client = content_generator.api_client
        
        # 初始化批量处理器
        self.batch_processor = MediumEventBatchProcessor(
            api_client=self.api_client,
            novel_generator=getattr(content_generator, 'novel_generator', None)
        )
        
        self.logger = logging.getLogger(__name__)
    
    def generate_single_chapter_with_style(
        self,
        chapter_params: Dict,
        novel_title: str = "",
        username: str = None
    ) -> Optional[Dict]:
        """
        增强版单章生成（带风格指南自动加载）
        
        这是现有generate_chapter_content的包装，自动注入风格指南
        """
        # 自动加载风格指南
        if novel_title and "writing_style_guide" not in chapter_params:
            style_guide = WritingStyleGuideLoader.load_and_format(
                novel_title, username, use_cache=True
            )
            chapter_params["writing_style_guide"] = {
                "core_style": style_guide.core_style,
                "key_principles": style_guide.key_principles,
                "language_characteristics": style_guide.language_characteristics,
                "narration_techniques": style_guide.narration_techniques,
                "chapter_techniques": style_guide.chapter_techniques,
                "dialogue_style": style_guide.dialogue_style,
            }
        
        # 调用原始生成方法
        return self.content_generator.generate_chapter_content(chapter_params)
    
    def try_batch_generation(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        novel_data: Dict,
        context: Any = None,
        scenes_by_chapter: Optional[Dict[int, List[Dict]]] = None
    ) -> Optional[BatchProcessResult]:
        """
        尝试批量生成
        
        根据中型事件跨度决定是否使用批量生成
        
        Args:
            medium_event: 中型事件数据
            chapter_range: (start, end) 章节范围
            novel_data: 小说数据
            context: 生成上下文
            scenes_by_chapter: 预生成场景
            
        Returns:
            BatchProcessResult: 批量生成结果，如不适合批量则返回None
        """
        # 判断是否适合批量生成
        if not self.batch_processor.should_use_batch(chapter_range):
            self.logger.info(f"[BatchAdapter] 单章事件，使用逐章生成: {chapter_range}")
            return None
        
        # 执行批量生成
        self.logger.info(f"[BatchAdapter] 使用批量生成: {chapter_range}")
        
        result = self.batch_processor.process_medium_event(
            medium_event=medium_event,
            chapter_range=chapter_range,
            novel_data=novel_data,
            context=context,
            scenes_by_chapter=scenes_by_chapter,
            skip_assessment=False
        )
        
        if result.success:
            self.logger.info(
                f"[BatchAdapter] 批量生成成功: "
                f"API调用={result.api_calls_used}, "
                f"创造点={result.points_consumed}, "
                f"节省={result.points_saved}点, "
                f"评估={result.assessment.level.value if result.assessment else 'N/A'}"
            )
        else:
            self.logger.error(f"[BatchAdapter] 批量生成失败: {result.error}")
        
        return result
    
    def generate_medium_event(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        novel_data: Dict,
        context: Any = None,
        scenes_by_chapter: Optional[Dict[int, List[Dict]]] = None,
        force_batch: bool = False
    ) -> Dict[int, Dict]:
        """
        生成中型事件内容（智能选择批量或逐章）
        
        这是主要的集成入口，智能判断使用批量还是逐章
        
        Args:
            medium_event: 中型事件数据
            chapter_range: (start, end) 章节范围
            novel_data: 小说数据
            context: 生成上下文
            scenes_by_chapter: 预生成场景
            force_batch: 强制使用批量（即使跨度为1）
            
        Returns:
            {chapter_num: chapter_data} 生成的章节内容
        """
        # 判断是否使用批量
        use_batch = force_batch or self.batch_processor.should_use_batch(chapter_range)
        
        if use_batch:
            # 尝试批量生成
            result = self.try_batch_generation(
                medium_event=medium_event,
                chapter_range=chapter_range,
                novel_data=novel_data,
                context=context,
                scenes_by_chapter=scenes_by_chapter
            )
            
            if result and result.success:
                # 转换为标准格式
                return {
                    ch_num: {
                        "chapter_number": ch_num,
                        "title": content.title,
                        "content": content.content,
                        "key_events": content.key_events,
                        "character_states": content.character_states,
                        "items_delta": content.items_delta,
                        "time_progression": content.time_progression
                    }
                    for ch_num, content in result.chapters.items()
                }
        
        # 回退到逐章生成
        return self._generate_chapter_by_chapter(
            medium_event=medium_event,
            chapter_range=chapter_range,
            novel_data=novel_data,
            context=context,
            scenes_by_chapter=scenes_by_chapter
        )
    
    def _generate_chapter_by_chapter(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        novel_data: Dict,
        context: Any,
        scenes_by_chapter: Optional[Dict[int, List[Dict]]]
    ) -> Dict[int, Dict]:
        """逐章生成（回退方案）"""
        start_ch, end_ch = chapter_range
        results = {}
        
        novel_title = novel_data.get("novel_title", "")
        username = novel_data.get("username")
        
        for ch_num in range(start_ch, end_ch + 1):
            self.logger.info(f"[BatchAdapter] 逐章生成第{ch_num}章")
            
            # 获取场景
            scenes = scenes_by_chapter.get(ch_num, []) if scenes_by_chapter else []
            
            # 生成章节
            chapter_content = self.generate_single_chapter_with_style(
                chapter_params={
                    "chapter_number": ch_num,
                    "pre_designed_scenes": scenes,
                    "novel_data": novel_data,
                    "context": context,
                    "medium_event": medium_event
                },
                novel_title=novel_title,
                username=username
            )
            
            if chapter_content:
                results[ch_num] = chapter_content
            else:
                self.logger.error(f"[BatchAdapter] 第{ch_num}章生成失败")
        
        return results
    
    def get_generation_stats(self) -> Dict:
        """获取生成统计"""
        return self.batch_processor.get_stats()


def patch_content_generator(content_generator):
    """
    为ContentGenerator动态添加批量生成功能
    
    使用示例:
        from src.core.batch_generation import patch_content_generator
        
        # 在ContentGenerator初始化后调用
        patch_content_generator(content_generator)
        
        # 然后可以通过content_generator.batch_adapter访问批量功能
        result = content_generator.batch_adapter.generate_medium_event(...)
    """
    adapter = BatchGenerationAdapter(content_generator)
    content_generator.batch_adapter = adapter
    
    # 添加便捷方法
    content_generator.generate_medium_event_batch = adapter.generate_medium_event
    content_generator.get_batch_stats = adapter.get_generation_stats
    
    logger.info("[BatchPatch] ContentGenerator已添加批量生成功能")
    
    return adapter
