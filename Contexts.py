# Contexts.py
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class GenerationContext:
    def __init__(self, chapter_number, total_chapters, novel_data, stage_plan, 
                 event_context, foreshadowing_context, growth_context):
        self.chapter_number = chapter_number
        self.total_chapters = total_chapters
        self.novel_data = novel_data
        self.stage_plan = stage_plan
        self.event_context = event_context
        self.foreshadowing_context = foreshadowing_context
        self.growth_context = growth_context
        self.generator = None  # 用于存储生成器引用
    
    def validate(self):
        """验证上下文是否有效"""
        try:
            # 基本验证
            if not isinstance(self.chapter_number, int) or self.chapter_number <= 0:
                return False, f"无效的章节号: {self.chapter_number}"
            
            if not isinstance(self.total_chapters, int) or self.total_chapters <= 0:
                return False, f"无效的总章节数: {self.total_chapters}"
            
            if not self.novel_data or not isinstance(self.novel_data, dict):
                return False, "novel_data 为空或不是字典"
            
            # 检查必要的基础数据
            required_keys = ['novel_title', 'novel_synopsis', 'current_progress']
            for key in required_keys:
                if key not in self.novel_data:
                    return False, f"novel_data 缺少必要字段: {key}"
            
            # 检查当前进度
            progress = self.novel_data.get('current_progress', {})
            if not isinstance(progress, dict):
                return False, "current_progress 不是字典"
            
            # 其他上下文可以是空的，但不能是None
            if self.stage_plan is None:
                return False, "stage_plan 不能为 None"
            if self.event_context is None:
                return False, "event_context 不能为 None"
            if self.foreshadowing_context is None:
                return False, "foreshadowing_context 不能为 None"
            if self.growth_context is None:
                return False, "growth_context 不能为 None"
            
            return True, "上下文验证通过"
            
        except Exception as e:
            return False, f"验证过程中出错: {e}"
    
    def is_valid(self):
        """简单的有效性检查"""
        success, message = self.validate()
        return success
    
    def __str__(self):
        return f"GenerationContext(第{self.chapter_number}章, 总{self.total_chapters}章)"
    
    def __repr__(self):
        return self.__str__()

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