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
            'golden_finger': self.load_golden_finger(),
            'plan': self._load_json("完整方案.json", {}) or self._load_json("plan.json", {}) or self._load_project_info().get("plan", {}),
            'emotion_curve': self._load_json("情绪曲线.json", []),
            'faction_system': self._load_faction_system(),
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
        """加载情绪蓝图（已废弃独立文件，从情绪曲线自动推导）"""
        # 🔥 情绪蓝图.json 已废弃，不再生成独立文件
        # 改为从情绪曲线自动推导高潮节点
        emotion_curve = self._load_json("情绪曲线.json", [])
        if emotion_curve and isinstance(emotion_curve, list):
            climax_moments = [
                f"第{e.get('chapter')}章-{e.get('emotion', '高潮')}"
                for e in emotion_curve
                if e.get('intensity', 0) >= 9
            ]
            return {"climax_moments": climax_moments}
        
        # fallback：从 project_info.json 的 generation_metadata 中读取（兼容旧项目）
        # fallback：从 project_info.json 的 generation_metadata 中读取（兼容旧项目，静默）
        project_info = self._load_project_info()
        try:
            metadata = project_info.get("generation_metadata", {})
            mode_info = metadata.get("mode_specific", {}).get("info", {})
            return mode_info.get("emotional_blueprint", {})
        except Exception:
            return {}
    
    def load_stage_goals(self) -> List[Dict]:
        """加载阶段目标"""
        data = self._load_json("阶段目标.json", [])
        return data if isinstance(data, list) else [data]
    
    def load_market_analysis(self) -> Dict:
        """加载市场分析（可选）"""
        return self._load_json("市场分析.json", {})
    
    def _load_json(self, filename: str, default: any, silent: bool = False) -> any:
        """加载JSON文件
        
        Args:
            filename: 文件名
            default: 默认值
            silent: 如果为True，文件不存在时不输出warning（用于fallback读取）
        """
        if filename in self._cache:
            return self._cache[filename]
        
        filepath = self.products_path / filename
        if not filepath.exists():
            if not silent:
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
        """验证关键数据是否存在，并就地修复格式错误的数据"""
        # 检查主角名
        char_design = data.get('character_design', {})
        if not isinstance(char_design, dict):
            logger.warning(f"[PhaseOneDataLoader] ⚠️ 角色设计数据格式错误，期望dict，实际为{type(char_design).__name__}！")
            data['character_design'] = {}
            char_design = data['character_design']
        protagonist = char_design.get('protagonist', {}) if isinstance(char_design.get('protagonist'), dict) else {}
        if not isinstance(protagonist, dict):
            char_design['protagonist'] = {}
            protagonist = char_design['protagonist']
        if not protagonist.get('name'):
            logger.warning("[PhaseOneDataLoader] ⚠️ 主角名缺失！")
        else:
            logger.info(f"[PhaseOneDataLoader] 主角名: {protagonist.get('name')}")
        
        # 检查世界观
        world = data.get('world_setting', {})
        if not isinstance(world, dict):
            logger.warning(f"[PhaseOneDataLoader] ⚠️ 世界观数据格式错误，期望dict，实际为{type(world).__name__}！")
            data['world_setting'] = {}
            world = data['world_setting']
        world_overview = world.get('world_overview', {})
        if not isinstance(world_overview, dict):
            logger.warning(f"[PhaseOneDataLoader] ⚠️ world_overview格式错误，期望dict，实际为{type(world_overview).__name__}！")
            world['world_overview'] = {}
            world_overview = world['world_overview']
        if not world_overview.get('background'):
            logger.warning("[PhaseOneDataLoader] ⚠️ 世界观背景缺失！")
        
        # 检查金手指
        power = world.get('power_system', {})
        if not isinstance(power, dict):
            logger.warning(f"[PhaseOneDataLoader] ⚠️ power_system格式错误，期望dict，实际为{type(power).__name__}！")
            world['power_system'] = {}
            power = world['power_system']
        if not power.get('shen_lang_exclusive'):
            logger.warning("[PhaseOneDataLoader] ⚠️ 金手指详细规则缺失！")
        
        # 检查情绪蓝图
        emotion = data.get('emotional_blueprint', {})
        if not isinstance(emotion, dict):
            logger.warning(f"[PhaseOneDataLoader] ⚠️ 情绪蓝图数据格式错误，期望dict，实际为{type(emotion).__name__}！")
            data['emotional_blueprint'] = {}
            emotion = data['emotional_blueprint']
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
            {'name': '主角', 'type': 'protagonist', 'role': '主角', 'traits': ['冷静', '果断']},
            {'name': '同伴', 'type': 'ally', 'role': '伙伴', 'traits': ['忠诚', '可靠']},
            ...
        ]
        """
        char_design = self.load_character_design()
        characters = []
        
        # 确保 char_design 是字典
        if not isinstance(char_design, dict):
            logger.warning(f"[PhaseOneDataLoader] 角色设计数据格式错误，期望dict，实际为{type(char_design).__name__}")
            return characters
        
        # 主角
        protagonist = char_design.get('protagonist', {})
        if isinstance(protagonist, dict) and protagonist:
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
        core_allies = char_design.get('core_allies', [])
        if isinstance(core_allies, list):
            for ally in core_allies:
                if isinstance(ally, dict):
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
        if isinstance(antagonists, dict):
            for stage, villains in antagonists.items():
                if isinstance(villains, list):
                    for villain in villains:
                        if isinstance(villain, dict):
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
        supporting_roles = char_design.get('supporting_roles', [])
        if isinstance(supporting_roles, list):
            for role in supporting_roles:
                if isinstance(role, dict):
                    characters.append({
                        'name': role.get('name', ''),
                        'type': 'supporting',
                        'role': role.get('role', '配角'),
                        'traits': role.get('traits', []),
                        'source': '角色设计.json/supporting_roles'
                    })
        
        return characters
    
    def load_golden_finger(self) -> Dict:
        """
        加载金手指详细设定（统一入口）
        
        优先从金手指设定.json读取，如不存在则从其他数据源回退
        """
        # 1. 优先从专用文件读取
        gf = self._load_json("金手指设计.json", None)
        if gf and isinstance(gf, dict):
            logger.info(f"[PhaseOneDataLoader] 从金手指设计.json加载")
            return gf
        
        # 兼容旧命名
        gf = self._load_json("金手指设定.json", None)
        if gf and isinstance(gf, dict):
            logger.info(f"[PhaseOneDataLoader] 从金手指设定.json加载")
            return gf
        
        # 2. 从 project_info.json 读取（兼容新结构）
        project_info = self._load_project_info()
        if project_info:
            plan = project_info.get("plan", {})
            gf = plan.get("golden_finger", None)
            if gf and isinstance(gf, dict):
                # 检查是否是完整结构
                if "abilities" in gf or "basic_info" in gf:
                    logger.info(f"[PhaseOneDataLoader] 从project_info.json加载完整金手指")
                    return gf
                else:
                    logger.warning(f"[PhaseOneDataLoader] 金手指结构不完整，尝试转换")
                    return self._normalize_golden_finger(gf)
            
            # 3. 尝试读取旧字段 golden_finger_summary
            summary = plan.get("golden_finger_summary", "")
            if summary:
                logger.warning(f"[PhaseOneDataLoader] 使用旧版golden_finger_summary回退")
                return self._create_simple_golden_finger(summary)
        
        # 4. 从世界观回退（mc_exclusive字段）
        world = self.load_world_setting()
        if isinstance(world, dict):
            power = world.get("power_system", {})
            if isinstance(power, dict):
                mechanics = power.get("mechanics", {})
                if isinstance(mechanics, dict):
                    mc_exclusive = mechanics.get("mc_exclusive", "")
                    if mc_exclusive:
                        logger.warning(f"[PhaseOneDataLoader] 从世界观mc_exclusive回退")
                        return self._create_simple_golden_finger(mc_exclusive)
        
        # 5. 空对象（不再硬编码）
        logger.error(f"[PhaseOneDataLoader] 无法找到金手指设定！")
        return self._create_empty_golden_finger()
    
    def _load_project_info(self) -> Dict:
        """加载项目信息文件"""
        try:
            project_info_path = self.project_path / "project_info.json"
            if project_info_path.exists():
                with open(project_info_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[PhaseOneDataLoader] 加载project_info.json失败: {e}")
        return {}
    
    def _load_faction_system(self) -> Dict:
        """加载势力系统（从专用文件、完整方案或项目信息回退）"""
        # 1. 尝试读取专用文件（修复：使用正确的文件名）
        fs = self._load_json("势力设定.json", {})
        if fs:
            return fs
        
        # 兼容旧命名（静默读取，避免输出废弃文件警告）
        fs = self._load_json("faction_system.json", {}, silent=True)
        if fs:
            return fs
        
        # 2. 从完整方案回退
        plan = self._load_json("完整方案.json", {}) or self._load_json("plan.json", {})
        if isinstance(plan, dict) and plan.get("faction_system"):
            return plan["faction_system"]
        
        # 3. 从项目信息回退
        project_info = self._load_project_info()
        plan = project_info.get("plan", {})
        if isinstance(plan, dict) and plan.get("faction_system"):
            return plan["faction_system"]
        
        return {}
    
    def _normalize_golden_finger(self, data: Dict) -> Dict:
        """标准化金手指数据结构（处理不同版本）"""
        # 如果已经是新结构，直接返回
        if "basic_info" in data:
            return data
        
        # 转换旧结构到新结构
        return {
            "basic_info": {
                "name": data.get("name", "未命名系统"),
                "type": data.get("type", "unknown"),
                "type_label": data.get("type_label", "❓ 未知"),
                "concept": data.get("concept", data.get("description", ""))
            },
            "abilities": {
                "initial": data.get("initial_ability", data.get("initial", "")),
                "growth": data.get("growth_curve", data.get("growth", "")),
                "max": data.get("max_potential", data.get("max", ""))
            },
            "restrictions": {
                "limitations": data.get("limitations", []),
                "side_effects": data.get("side_effects", []),
                "cooldown": data.get("cooldown_rules", data.get("cooldown", ""))
            },
            "applications": {
                "combat": data.get("combat_usage", ""),
                "daily": data.get("daily_usage", ""),
                "special": data.get("special_mechanics", {})
            },
            "protagonist_synergy": {
                "compatibility": data.get("compatibility", ""),
                "combo_effects": data.get("combo_effects", [])
            },
            "plot_role": {
                "hooks": data.get("plot_hooks", data.get("hooks", [])),
                "twist_potential": data.get("twist_potential", "")
            },
            "_source": "normalized",
            "_original_data": data
        }
    
    def _create_simple_golden_finger(self, summary: str) -> Dict:
        """从简单描述创建简化金手指结构"""
        return {
            "basic_info": {
                "name": "待命名系统",
                "type": "unknown",
                "type_label": "❓ 待补充",
                "concept": summary
            },
            "abilities": {
                "initial": "初始能力待补充",
                "growth": "成长曲线待补充",
                "max": "最终形态待补充"
            },
            "restrictions": {
                "limitations": [],
                "side_effects": [],
                "cooldown": ""
            },
            "applications": {
                "combat": "",
                "daily": "",
                "special": {}
            },
            "protagonist_synergy": {
                "compatibility": "",
                "combo_effects": []
            },
            "plot_role": {
                "hooks": [],
                "twist_potential": ""
            },
            "_source": "fallback_summary",
            "_needs_completion": True
        }
    
    def _create_empty_golden_finger(self) -> Dict:
        """创建空金手指对象（最终回退）"""
        return {
            "basic_info": {
                "name": "未设定",
                "type": "unknown",
                "type_label": "❌ 缺失",
                "concept": "金手指设定未找到"
            },
            "abilities": {
                "initial": "",
                "growth": "",
                "max": ""
            },
            "restrictions": {
                "limitations": [],
                "side_effects": [],
                "cooldown": ""
            },
            "applications": {
                "combat": "",
                "daily": "",
                "special": {}
            },
            "protagonist_synergy": {
                "compatibility": "",
                "combo_effects": []
            },
            "plot_role": {
                "hooks": [],
                "twist_potential": ""
            },
            "_error": "金手指设定缺失",
            "_source": "empty"
        }
    
    def get_golden_finger(self) -> Dict:
        """
        获取金手指详细设定（向后兼容接口）
        
        建议使用新的 load_golden_finger() 方法
        """
        return self.load_golden_finger()
    
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
