# EventBus.py
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from typing import Dict
from src.utils.logger import get_logger


class EventBus:
    """统一事件总线，负责模块间通信"""
    
    def __init__(self):
        self.logger = get_logger("EventBus")
        self._listeners = {}
        self._async_listeners = {}
    
    def subscribe(self, event_type: str, callback: callable):
        """订阅事件"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def publish(self, event_type: str, data: Dict = None):
        """发布事件"""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.info(f"事件处理错误 {event_type}: {e}")
    
    # Events.py
    STANDARD_EVENTS = {
        # 生命周期事件
        'project.initialized': '项目初始化完成',
        'generation.started': '生成开始',
        'generation.completed': '生成完成',
        
        # 章节相关事件
        'chapter.preparing': '章节准备开始',
        'chapter.design.generated': '章节设计方案生成',
        'chapter.content.generated': '章节内容生成', 
        'chapter.quality.assessed': '章节质量评估',
        'chapter.optimized': '章节优化完成',
        'chapter.saved': '章节保存完成',
        
        # 阶段事件
        'stage.plan.generated': '阶段计划生成',
        'stage.transition': '阶段转换',
        
        # 错误事件
        'error.occurred': '发生错误',
        'warning.occurred': '发生警告'
    }