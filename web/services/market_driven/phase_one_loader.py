"""
Phase One Data Loader
一阶段产物数据加载器

负责从 phase_one_products 目录加载所有一阶段生成的设定数据
供细纲规划使用
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PhaseOneDataLoader:
    """
    一阶段产物数据加载器
    
    加载内容：
    - 角色设计.json
    - 世界观设定.json
    - 升级路线.json
    - 情绪蓝图.json
    - 阶段目标.json
    - 市场分析.json（可选）
    """
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.products_path = self.project_path / "phase_one_products"
        self._cache = {}
        
    def load_all(self) -> Dict:
        """加载所有一阶段产物"""
        logger.info(f"[PhaseOneDataLoader] 开始加载一阶段产物: {self.products_path}")
        
        if not self.products_path.exists():
            logger.warning(f"[PhaseOneDataLoader] 一阶段产物目录不存在: {self.products_path}")
            return self._get_default_data()
        
        data = {
            'character_design': self.load_character_design(),
            'world_setting': self.load_world_setting(),
            'progression_path': self.load_progression_path(),
            'emotional_blueprint': self.load_emotional_blueprint(),
            'stage_goals': self.load_stage_goals(),
            'market_analysis': self.load_market_analysis(),
        }
        
        # 验证关键数据
        self._validate_critical_data(data)
        
        logger.info("[PhaseOneDataLoader] 一阶段产物加载完成")
        return data
    
    def load_character_design(self) -> Dict:
        """加载角色设计"""
        return self._load_json("角色设计.json", {})
    
    def load_world_setting(self) -> Dict:
        """加载世界观设定"""
        return self._load_json("世界观设定.json", {})
    
    def load_progression_path(self) -> Dict:
        """加载升级路线"""
        return self._load_json("升级路线.json", {})
    
    def load_emotional_blueprint(self) -> Dict:
        """加载情绪蓝图"""
        return self._load_json("情绪蓝图.json", {})
    
    def load_stage_goals(self) -> List[Dict]:
        """加载阶段目标"""
        data = self._load_json("阶段目标.json", [])
        return data if isinstance(data, list) else [data]
    
    def load_market_analysis(self) -> Dict:
        """加载市场分析（可选）"""
        return self._load_json("市场分析.json", {})
    
    def _load_json(self, filename: str, default: any) -> any:
        """加载JSON文件"""
        if filename in self._cache:
            return self._cache[filename]
        
        filepath = self.products_path / filename
        if not filepath.exists():
            logger.warning(f"[PhaseOneDataLoader] 文件不存在: {filename}")
            return default
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[filename] = data
            logger.info(f"[PhaseOneDataLoader] 加载成功: {filename}")
            return data
        except Exception as e:
            logger.error(f"[PhaseOneDataLoader] 加载失败 {filename}: {e}")
            return default
    
    def _validate_critical_data(self, data: Dict):
        """验证关键数据是否存在"""
        # 检查主角名
        char_design = data.get('character_design', {})
        protagonist = char_design.get('protagonist', {})
        if not protagonist.get('name'):
            logger.warning("[PhaseOneDataLoader] ⚠️ 主角名缺失！")
        else:
            logger.info(f"[PhaseOneDataLoader] 主角名: {protagonist.get('name')}")
        
        # 检查世界观
        world = data.get('world_setting', {})
        if not world.get('world_overview', {}).get('background'):
            logger.warning("[PhaseOneDataLoader] ⚠️ 世界观背景缺失！")
        
        # 检查金手指
        power = world.get('power_system', {})
        if not power.get('shen_lang_exclusive'):
            logger.warning("[PhaseOneDataLoader] ⚠️ 金手指详细规则缺失！")
        
        # 检查情绪蓝图
        emotion = data.get('emotional_blueprint', {})
        if not emotion.get('climax_moments'):
            logger.warning("[PhaseOneDataLoader] ⚠️ 高潮节点缺失！")
        else:
            logger.info(f"[PhaseOneDataLoader] 高潮节点: {emotion.get('climax_moments')}")
    
    def _get_default_data(self) -> Dict:
        """获取默认数据（当一阶段产物不存在时）"""
        logger.warning("[PhaseOneDataLoader] 使用默认数据")
        return {
            'character_design': {},
            'world_setting': {},
            'progression_path': {},
            'emotional_blueprint': {},
            'stage_goals': [],
            'market_analysis': {},
        }
    
    def get_character_list(self) -> List[Dict]:
        """
        获取标准化角色列表
        
        返回格式：
        [
            {'name': '沈浪', 'type': 'protagonist', 'role': '主角', 'traits': [...]},
            {'name': '二哈', 'type': 'ally', 'role': '战宠', 'traits': [...]},
            ...
        ]
        """
        char_design = self.load_character_design()
        characters = []
        
        # 主角
        protagonist = char_design.get('protagonist', {})
        if protagonist:
            characters.append({
                'name': protagonist.get('name', '主角'),
                'type': 'protagonist',
                'role': '主角',
                'traits': protagonist.get('traits', []),
                'identity': protagonist.get('identity', ''),
                'age': protagonist.get('age'),
                'source': '角色设计.json/protagonist'
            })
        
        # 核心盟友
        for ally in char_design.get('core_allies', []):
            characters.append({
                'name': ally.get('name', ''),
                'type': 'ally',
                'role': ally.get('role', '盟友'),
                'traits': ally.get('traits', []),
                'contribution': ally.get('contribution', ''),
                'source': '角色设计.json/core_allies'
            })
        
        # 反派
        antagonists = char_design.get('main_antagonists', {})
        for stage, villains in antagonists.items():
            for villain in villains:
                characters.append({
                    'name': villain.get('name', ''),
                    'type': 'villain',
                    'role': f'反派({stage})',
                    'motivation': villain.get('motivation', ''),
                    'hate_point': villain.get('hate_point', ''),
                    'face_slapping_arc': villain.get('face_slapping_arc', ''),
                    'source': f'角色设计.json/main_antagonists/{stage}'
                })
        
        # 配角
        for role in char_design.get('supporting_roles', []):
            characters.append({
                'name': role.get('name', ''),
                'type': 'supporting',
                'role': role.get('role', '配角'),
                'traits': role.get('traits', []),
                'source': '角色设计.json/supporting_roles'
            })
        
        return characters
    
    def get_golden_finger(self) -> Dict:
        """
        获取金手指详细设定
        
        返回标准化格式的金手指信息
        """
        world = self.load_world_setting()
        power = world.get('power_system', {})
        
        return {
            'name': '弹幕干涉系统',
            'mechanics': power.get('shen_lang_exclusive', ''),
            'level_standard': power.get('level_standard', 'F-SSS级'),
            'pet_system': power.get('pet_system', ''),
            'combat_mechanics': power.get('combat_mechanics', {}),
        }
    
    def get_current_stage_goal(self, chapter_range_start: int) -> Optional[Dict]:
        """
        获取指定章节范围对应的阶段目标
        
        Args:
            chapter_range_start: 章节范围开始（如1表示1-30章）
        """
        stage_goals = self.load_stage_goals()
        
        for goal in stage_goals:
            expected = goal.get('expected_chapters', '')
            if expected:
                # 解析 "1-30章" 格式
                try:
                    parts = expected.replace('章', '').split('-')
                    start = int(parts[0])
                    if start <= chapter_range_start <= start + 30:
                        return goal
                except:
                    continue
        
        # 默认返回第一个
        return stage_goals[0] if stage_goals else None


# 全局加载器实例缓存
_loaders = {}

def get_phase_one_loader(project_path: Path) -> PhaseOneDataLoader:
    """获取或创建加载器实例"""
    path_str = str(project_path)
    if path_str not in _loaders:
        _loaders[path_str] = PhaseOneDataLoader(project_path)
    return _loaders[path_str]


def load_phase_one_data(project_path: Path) -> Dict:
    """便捷函数：加载所有一阶段数据"""
    loader = get_phase_one_loader(project_path)
    return loader.load_all()
