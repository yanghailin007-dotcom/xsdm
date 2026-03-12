# -*- coding: utf-8 -*-
"""
中型事件批量生成模块

提供按中型事件批量生成章节内容的功能，优化API调用效率。

主要组件:
- MediumEventBatchProcessor: 主处理器，协调批量生成流程
- MultiChapterContentGenerator: 多章内容生成器
- LayeredQualityAssessor: 分层质量评估器
- BatchFallbackHandler: 错误回退处理器
- WritingStyleGuideLoader: 写作风格指南加载器

使用示例:
    from src.core.batch_generation import MediumEventBatchProcessor
    
    processor = MediumEventBatchProcessor(api_client, novel_generator)
    
    result = processor.process_medium_event(
        medium_event=medium_event,
        chapter_range=(5, 7),
        novel_data=novel_data,
        context=context
    )
    
    if result.success:
        for ch_num, content in result.chapters.items():
            print(f"第{ch_num}章生成成功: {content.title}")
"""

from .processor import MediumEventBatchProcessor, BatchProcessResult
from .multi_chapter_generator import (
    MultiChapterContentGenerator, 
    ChapterContent,
    generate_multi_chapter_content
)
from .quality_assessor import (
    LayeredQualityAssessor,
    AssessmentResult,
    AssessmentLevel,
    quick_assess_batch
)
from .fallback_handler import BatchFallbackHandler, FallbackResult, FailureType
from .writing_style_loader import (
    WritingStyleGuideLoader,
    FormattedStyleGuide,
    get_writing_style_for_prompt
)
from .integration import (
    BatchGenerationAdapter,
    patch_content_generator
)
from .golden_chapters import (
    GoldenChaptersGenerator,
    generate_golden_chapters
)
from .golden_chapters_assessor import (
    GoldenChaptersAssessor,
    GoldenChaptersAssessment,
    assess_golden_chapters
)

__all__ = [
    # 主处理器
    'MediumEventBatchProcessor',
    'BatchProcessResult',
    
    # 内容生成
    'MultiChapterContentGenerator',
    'ChapterContent',
    'generate_multi_chapter_content',
    
    # 黄金三章
    'GoldenChaptersGenerator',
    'generate_golden_chapters',
    'GoldenChaptersAssessor',
    'GoldenChaptersAssessment',
    'assess_golden_chapters',
    
    # 质量评估
    'LayeredQualityAssessor',
    'AssessmentResult',
    'AssessmentLevel',
    'quick_assess_batch',
    
    # 错误回退
    'BatchFallbackHandler',
    'FallbackResult',
    'FailureType',
    
    # 风格指南
    'WritingStyleGuideLoader',
    'FormattedStyleGuide',
    'get_writing_style_for_prompt',
    
    # 集成
    'BatchGenerationAdapter',
    'patch_content_generator',
]
