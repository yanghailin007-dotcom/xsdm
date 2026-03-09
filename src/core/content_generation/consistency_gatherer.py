"""一致性收集器 - 专门负责收集和管理一致性数据"""
import json
from typing import Dict
from src.utils.logger import get_logger


class ConsistencyGatherer:
    """统一的一致性收集器 - 整合所有一致性数据收集逻辑"""
    
    def __init__(self, generator):
        self.logger = get_logger("ConsistencyGatherer")
        self.generator = generator
    
    def gather_all(self, novel_title: str, chapter_num: int, novel_data: Dict = None) -> Dict:
        """一次性收集所有一致性数据"""
        world_state = self._get_previous_world_state(novel_title)
        consistency_guid = self._build_consistency_guidance(world_state, novel_title)
        relationships = self._get_relationship_consistency_note(world_state)
        char_dev = self._get_character_development_guidance(chapter_num, novel_data)
        return {
            "world_state": world_state,
            "consistency_guidance": consistency_guid,
            "relationships": relationships,
            "character_development": char_dev
        }
    
    def _get_previous_world_state(self, novel_title: str) -> Dict:
        """从文件中加载前面章节的世界状态"""
        from src.managers.WorldStateManager import WorldStateManager
        username = getattr(self.generator, '_username', None)
        wsm = WorldStateManager(novel_title=novel_title, username=username)
        return wsm.get_novel_world_state(novel_title)
    
    def _build_consistency_guidance(self, world_state: Dict, novel_title: str) -> str:
        """基于世界状态构建一致性指导（使用压缩后的数据）"""
        if hasattr(self.generator, 'quality_assessor') and self.generator.quality_assessor:
            compressed_state = self.generator.quality_assessor._compress_world_state_for_assessment(
                world_state, max_chars=8000
            )
            return f"【一致性指导】\n请保持与以下已有信息的一致性：\n{compressed_state}"
        else:
            return f"【一致性指导】\n请保持与已有世界设定的一致性"
    
    def _get_relationship_consistency_note(self, world_state: Dict) -> str:
        """获取关系一致性说明"""
        relationships = world_state.get("relationships", {})
        return f"已有关系：{json.dumps(relationships, ensure_ascii=False)}"
    
    def _get_character_development_guidance(self, chapter_num: int, novel_data: Dict = None) -> str:
        """获取角色发展指导"""
        if novel_data is None:
            return f"第 {chapter_num} 章的角色应该有相应的发展和变化"
        if hasattr(self.generator, 'quality_assessor') and self.generator.quality_assessor:
            novel_title = novel_data.get("novel_title", "Unknown")
            char_dev_data = self.generator.quality_assessor._load_character_development_data(novel_title)
            if char_dev_data:
                return f"第 {chapter_num} 章 - 角色发展指导已根据历史数据生成"
        return f"第 {chapter_num} 章的角色应该有相应的发展和变化"