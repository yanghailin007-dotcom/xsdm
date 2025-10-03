# Contexts.py
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class GenerationContext:
    """统一的生成上下文"""
    chapter_number: int
    total_chapters: int
    novel_data: Dict[str, Any]
    stage_plan: Optional[Dict] = None
    event_context: Optional[Dict] = None
    foreshadowing_context: Optional[Dict] = None
    growth_context: Optional[Dict] = None
    
    def validate(self) -> bool:
        """验证上下文完整性"""
        required = ['chapter_number', 'total_chapters', 'novel_data']
        return all(hasattr(self, attr) for attr in required)

@dataclass
class ChapterParameters:
    """章节生成参数"""
    context: GenerationContext
    previous_content: Optional[Dict] = None
    design_requirements: Optional[Dict] = None
    
    @classmethod
    def from_context(cls, context: GenerationContext) -> 'ChapterParameters':
        """从上下文构建参数"""
        return cls(context=context)