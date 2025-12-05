"""配置文件 - 兼容性版本"""

from .BasePrompts import BasePrompts
from .AnalysisPrompts import AnalysisPrompts
from .WorldviewPrompts import WorldviewPrompts
from .PlanningPrompts import PlanningPrompts
from .WritingPrompts import WritingPrompts
from .OptimizationPrompts import OptimizationPrompts

class Prompts:
    def __init__(self):
        # 合并所有提示词字典
        base = BasePrompts()
        analysis = AnalysisPrompts()
        worldview = WorldviewPrompts()
        planning = PlanningPrompts()
        writing = WritingPrompts()
        optimization = OptimizationPrompts()
        
        self.prompts = {}
        self.prompts.update(base.prompts)
        self.prompts.update(analysis.prompts)
        self.prompts.update(worldview.prompts)
        self.prompts.update(planning.prompts)
        self.prompts.update(writing.prompts)
        self.prompts.update(optimization.prompts)
    
    # 添加兼容性方法
    def get(self, key, default=None):
        """兼容原来的 get 方法"""
        return self.prompts.get(key, default)
    
    def __getitem__(self, key):
        """支持字典式的访问"""
        return self.prompts[key]
    
    def __contains__(self, key):
        """支持 in 操作符"""
        return key in self.prompts

# 创建全局实例以保持向后兼容
_Pprompts_instance = Prompts()