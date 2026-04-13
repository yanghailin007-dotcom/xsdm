# -*- coding: utf-8 -*-
"""
V2 六层架构 - 各层Loader实现
负责从YAML/JSON加载各层配置
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .models import (
    CoreSetting, WorldView, WorldRule, PowerSystem, GoldenFinger, Protagonist, BurstFormula,
    TacticalPlanning, StageInfo, EmotionPhase, BurstDesign, HookDesign, CurrentChapter,
    ChapterStructure, ChapterSection,
    GenreTechniques, ShockStep, BarrageRules, BarrageTemplate, MoneyRules, SystemPrompt,
    BystanderTemplate, ForbiddenElement, RequiredElement, DialogueMethod,
    WritingStyle, ParagraphRule, SentenceRule, DialogueRule, PacingRule, ShockFlowRule,
    EmotionControlRule, ForbiddenItem,
    AIConstraints, WordCountConstraint, FormatConstraint, FormatRule, SafetyConstraint,
    SelfCheck, CheckItem, DuringWritingCheckpoint, QualityMetric, QualityScore,
    EmotionPlan
)

logger = logging.getLogger(__name__)


# ==================== Base Loader ====================

class BaseLoader:
    """基础加载器
    
    加载优先级:
    1. 用户配置的提示词包: prompt_packages/default/market_driven/v2_config/
    2. 系统默认: prompt_packages/v2_architecture/
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent.parent.parent
            
            # 优先使用用户可配置的提示词包
            user_config_path = project_root / "prompt_packages" / "default" / "market_driven" / "v2_config"
            if user_config_path.exists():
                self.base_path = user_config_path
                logger.info(f"[BaseLoader] 使用用户配置: {self.base_path}")
            else:
                # 回退到系统默认
                self.base_path = project_root / "prompt_packages" / "v2_architecture"
                logger.info(f"[BaseLoader] 使用系统默认: {self.base_path}")
        else:
            self.base_path = Path(base_path)
        
        self._cache: Dict[str, Any] = {}
    
    def _load_yaml(self, file_path: Path) -> Dict:
        """加载YAML文件"""
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_json(self, file_path: Path) -> Dict:
        """加载JSON文件"""
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)


# ==================== Layer 1 Loader ====================

class CoreSettingLoader(BaseLoader):
    """Layer 1: 核心设定加载器"""
    
    def load(self, project_id: str) -> CoreSetting:
        """加载核心设定"""
        cache_key = f"core_setting_{project_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        file_path = self.base_path / "core_settings" / f"{project_id}.yaml"
        
        try:
            data = self._load_yaml(file_path)
        except FileNotFoundError:
            # 返回默认设定
            logger.warning(f"找不到核心设定: {project_id}，使用默认")
            data = self._get_default_core_setting()
        
        setting = self._parse_core_setting(data)
        self._cache[cache_key] = setting
        return setting
    
    def _parse_core_setting(self, data: Dict) -> CoreSetting:
        """解析核心设定"""
        # 解析世界观
        worldview_data = data.get('worldview', {})
        worldview = WorldView(
            overview=worldview_data.get('overview', ''),
            core_rules=[WorldRule(r.get('rule', ''), r.get('description', '')) 
                       for r in worldview_data.get('core_rules', [])],
            power_system=PowerSystem(
                name=worldview_data.get('power_system', {}).get('name', ''),
                levels=worldview_data.get('power_system', {}).get('levels', []),
                upgrade_method=worldview_data.get('power_system', {}).get('upgrade_method', ''),
                current_level=worldview_data.get('power_system', {}).get('current_level', '')
            ),
            world_rules=worldview_data.get('world_rules', [])
        )
        
        # 解析金手指
        gf_data = data.get('golden_finger', {})
        golden_finger = GoldenFinger(
            name=gf_data.get('name', ''),
            type=gf_data.get('type', ''),
            core_mechanism=gf_data.get('core_mechanism', ''),
            current_level=gf_data.get('current_level', ''),
            current_ability=gf_data.get('current_ability', ''),
            limitations=gf_data.get('limitations', []),
            growth_path=gf_data.get('growth_path', []),
            reward_sound=gf_data.get('reward_sound', '')
        )
        
        # 解析主角
        pro_data = data.get('protagonist', {})
        protagonist = Protagonist(
            name=pro_data.get('name', '主角'),
            age=pro_data.get('age', 22),
            background=pro_data.get('background', ''),
            surface_identity=pro_data.get('surface_identity', ''),
            true_identity=pro_data.get('true_identity', ''),
            personality_tags=pro_data.get('personality_tags', []),
            core_motivation=pro_data.get('core_motivation', ''),
            catchphrases=pro_data.get('catchphrases', []),
            signature_actions=pro_data.get('signature_actions', []),
            forbidden_behaviors=pro_data.get('forbidden_behaviors', [])
        )
        
        return CoreSetting(
            version=data.get('version', '1.0'),
            worldview=worldview,
            golden_finger=golden_finger,
            protagonist=protagonist,
            core_selling_point=data.get('core_selling_point', ''),
            burst_formula=BurstFormula(
                pattern=data.get('burst_formula', {}).get('pattern', ''),
                shock_hierarchy=data.get('burst_formula', {}).get('shock_hierarchy', []),
                reward_types=data.get('burst_formula', {}).get('reward_types', [])
            ),
            core_taboos=data.get('core_taboos', [])
        )
    
    def _get_default_core_setting(self) -> Dict:
        """获取默认核心设定"""
        return {
            'version': '1.0',
            'worldview': {
                'overview': '请设置世界观',
                'core_rules': [],
                'power_system': {'name': '', 'levels': [], 'upgrade_method': '', 'current_level': ''},
                'world_rules': []
            },
            'golden_finger': {
                'name': '请设置金手指',
                'type': '系统',
                'core_mechanism': '',
                'current_level': '1级',
                'current_ability': '',
                'limitations': [],
                'growth_path': [],
                'reward_sound': ''
            },
            'protagonist': {
                'name': '主角',
                'age': 22,
                'background': '',
                'surface_identity': '',
                'true_identity': '',
                'personality_tags': [],
                'core_motivation': '',
                'catchphrases': [],
                'signature_actions': [],
                'forbidden_behaviors': []
            },
            'core_selling_point': '',
            'burst_formula': {'pattern': '', 'shock_hierarchy': [], 'reward_types': []},
            'core_taboos': []
        }


# ==================== Layer 2 Loader ====================

class TacticalPlanningLoader(BaseLoader):
    """Layer 2: 战术规划加载器"""
    
    def load(self, batch_id: str, chapter_num: int) -> TacticalPlanning:
        """加载战术规划"""
        cache_key = f"tactical_{batch_id}_{chapter_num}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        file_path = self.base_path / "tactical_plans" / f"{batch_id}.yaml"
        
        try:
            data = self._load_yaml(file_path)
        except FileNotFoundError:
            logger.warning(f"找不到战术规划: {batch_id}，使用默认")
            return self._get_default_tactical_planning(chapter_num)
        
        planning = self._parse_tactical_planning(data, chapter_num)
        self._cache[cache_key] = planning
        return planning
    
    def _parse_tactical_planning(self, data: Dict, chapter_num: int) -> TacticalPlanning:
        """解析战术规划"""
        # 解析阶段信息
        stage_data = data.get('current_stage', {})
        stage = StageInfo(
            stage_name=stage_data.get('stage_name', ''),
            chapter_range=stage_data.get('chapter_range', ''),
            word_range=stage_data.get('word_range', ''),
            core_mission=stage_data.get('core_mission', ''),
            stage_climax=stage_data.get('stage_climax', {}),
            key_milestones=stage_data.get('key_milestones', [])
        )
        
        # 解析情绪曲线
        emotion_phases = [
            EmotionPhase(
                range=p.get('range', ''),
                emotion=p.get('emotion', ''),
                intensity=p.get('intensity', ''),
                description=p.get('description', ''),
                key_hook=p.get('key_hook', '')
            )
            for p in data.get('stage_emotion_curve', {}).get('phases', [])
        ]
        
        # 解析本章规划
        chapter_data = data.get('current_chapter', {})
        burst_design = BurstDesign(
            target=chapter_data.get('burst_design', {}).get('target', ''),
            method=chapter_data.get('burst_design', {}).get('method', ''),
            shock_levels=chapter_data.get('burst_design', {}).get('shock_levels', []),
            rewards=chapter_data.get('burst_design', {}).get('rewards', [])
        )
        
        hook_design = HookDesign(
            type=chapter_data.get('hook_design', {}).get('type', ''),
            content=chapter_data.get('hook_design', {}).get('content', ''),
            tease=chapter_data.get('hook_design', {}).get('tease', '')
        )
        
        current_chapter = CurrentChapter(
            chapter_num=chapter_num,
            chapter_type=chapter_data.get('chapter_type', '打脸章'),
            tactical_intent=chapter_data.get('tactical_intent', {}),
            burst_design=burst_design,
            hook_design=hook_design,
            must_include=chapter_data.get('must_include', {})
        )
        
        return TacticalPlanning(
            version=data.get('version', '1.0'),
            current_stage=stage,
            stage_emotion_curve=emotion_phases,
            current_chapter=current_chapter,
            chapter_structure=ChapterStructure([]),
            continuity=data.get('continuity', {}),
            foreshadowing=data.get('foreshadowing', [])
        )
    
    def _get_default_tactical_planning(self, chapter_num: int) -> TacticalPlanning:
        """获取默认战术规划"""
        return TacticalPlanning(
            current_chapter=CurrentChapter(
                chapter_num=chapter_num,
                chapter_type="打脸章",
                tactical_intent={},
                burst_design=BurstDesign("", "", [], []),
                hook_design=HookDesign("", "", ""),
                must_include={}
            )
        )


# ==================== Layer 3 Loader ====================

class GenreTechniquesLoader(BaseLoader):
    """Layer 3: 题材技法加载器"""
    
    def load(self, genre: str) -> GenreTechniques:
        """加载题材技法 - 支持关键字匹配"""
        cache_key = f"genre_{genre}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 关键字匹配逻辑
        genre_file = None
        genre_lower = genre.lower()
        
        # 🔥 英文题材 key 映射
        english_mapping = {
            "god-tier-spending": "神豪文.yaml",
            "god-tier-checkin": "神豪文.yaml",
            "nation-live": "国运文.yaml",
            "nation-explore": "国运文.yaml",
            "sign-in-daily": "神豪文.yaml",
            "simulator-life": "神豪文.yaml",
            "food-system": "神豪文.yaml",
            "farming-rich": "神豪文.yaml",
            "entertainment-copy": "神豪文.yaml",
            "courtyard-life": "神豪文.yaml",
            "god-select": "灵气复苏-觉醒类.yaml",
            "aura-recovery": "灵气复苏-觉醒类.yaml",
            "game-vr": "灵气复苏-觉醒类.yaml",
            "apocalypse-hoard": "末日求生-囤货类.yaml",
            "weird-recovery": "诡异复苏-规则怪谈类.yaml",
            "anime-infinite": "诡异复苏-规则怪谈类.yaml",
            "pet-evolution": "宠物文-御兽进化类.yaml",
            "dad-baby": "奶爸文-萌宝类.yaml",
            "dad-cultivate": "奶爸文-萌宝类.yaml",
            "historical-power": "国运文.yaml",
            "tomb-raider": "国运文.yaml",
        }
        if genre_lower in english_mapping:
            genre_file = english_mapping[genre_lower]
        
        if not genre_file:
            if "神豪" in genre or "花钱" in genre or "返利" in genre or "签到" in genre or "百倍" in genre or "盲盒" in genre:
                genre_file = "神豪文.yaml"
            elif "国运" in genre or "禁地" in genre or "直播" in genre or "国战" in genre:
                genre_file = "国运文.yaml"
        
        if not genre_file:
            # 尝试直接匹配
            direct_file = self.base_path / "genre_techniques" / f"{genre}.yaml"
            if direct_file.exists():
                genre_file = f"{genre}.yaml"
        
        if genre_file:
            file_path = self.base_path / "genre_techniques" / genre_file
        else:
            logger.warning(f"找不到题材技法: {genre}，使用通用模板")
            file_path = self.base_path / "genre_techniques" / "通用.yaml"
        
        # 如果匹配的文件不存在，回退到通用
        if not file_path.exists():
            logger.warning(f"题材文件不存在: {file_path}，使用通用模板")
            file_path = self.base_path / "genre_techniques" / "通用.yaml"
        
        data = self._load_yaml(file_path)
        techniques = self._parse_genre_techniques(data)
        self._cache[cache_key] = techniques
        return techniques
    
    def _parse_genre_techniques(self, data: Dict) -> GenreTechniques:
        """解析题材技法"""
        # 解析系统提示音
        system_prompts = [
            SystemPrompt(sp.get('type', ''), sp.get('template', ''), sp.get('usage', ''))
            for sp in data.get('system_prompts', [])
        ]
        
        # 解析禁用元素
        forbidden_elements = [
            ForbiddenElement(
                element=fe.get('element', ''),
                examples=fe.get('examples', []),
                reason=fe.get('reason', '')
            )
            for fe in data.get('forbidden_elements', {}).get('items', [])
        ]
        
        # 解析必须元素
        required_elements = [
            RequiredElement(
                element=re.get('element', ''),
                check=re.get('check', ''),
                severity=re.get('severity', 'warning')
            )
            for re in data.get('required_elements', {}).get('items', [])
        ]
        
        # 解析对话达成方式
        dialogue_methods = [
            DialogueMethod(
                method=dm.get('method', ''),
                description=dm.get('description', ''),
                weight=dm.get('weight', '')
            )
            for dm in data.get('dialogue_achievement', {}).get('methods', [])
        ]
        
        return GenreTechniques(
            genre=data.get('genre', '通用'),
            version=data.get('version', '1.0'),
            description=data.get('description', ''),
            shock_progression=data.get('shock_progression', {}),
            system_prompts=system_prompts,
            forbidden_elements=forbidden_elements,
            required_elements=required_elements,
            dialogue_achievement=dialogue_methods,
            pacing=data.get('pacing', {}),
            quality_checkpoints=data.get('quality_checkpoints', [])
        )


# ==================== Layer 4 Loader ====================

class WritingStyleLoader(BaseLoader):
    """Layer 4: 文风技法加载器"""
    
    def load(self) -> WritingStyle:
        """加载文风技法"""
        cache_key = "writing_style"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        file_path = self.base_path / "writing_style.yaml"
        
        try:
            data = self._load_yaml(file_path)
        except FileNotFoundError:
            logger.warning("找不到文风技法，使用默认")
            data = self._get_default_writing_style()
        
        style = self._parse_writing_style(data)
        self._cache[cache_key] = style
        return style
    
    def _parse_writing_style(self, data: Dict) -> WritingStyle:
        """解析文风技法"""
        return WritingStyle(
            paragraph=ParagraphRule(
                max_lines=data.get('paragraph', {}).get('max_lines', 3),
                avg_length=data.get('paragraph', {}).get('avg_length', '30-50字'),
                mobile_first=data.get('paragraph', {}).get('mobile_first', True)
            ),
            sentence=SentenceRule(
                short_ratio=data.get('sentence', {}).get('short_ratio', 0.6),
                max_length=data.get('sentence', {}).get('max_length', 15),
                colloquial=data.get('sentence', {}).get('colloquial', True)
            ),
            dialogue=DialogueRule(
                ratio=data.get('dialogue', {}).get('ratio', 0.5),
                format=data.get('dialogue', {}).get('format', '""'),
                one_per_paragraph=data.get('dialogue', {}).get('one_per_paragraph', True),
                tags=data.get('dialogue', {}).get('tags', [])
            ),
            pacing=PacingRule(
                conflict_first_300=data.get('pacing', {}).get('conflict_first_300', True),
                mini_burst_every_1000=data.get('pacing', {}).get('mini_burst_every_1000', True),
                hook_last_50=data.get('pacing', {}).get('hook_last_50', True),
                no_dialogue_limit=data.get('pacing', {}).get('no_dialogue_limit', 200)
            ),
            shock_flow=ShockFlowRule(
                principles=data.get('shock_flow', {}).get('principles', []),
                forbidden=data.get('shock_flow', {}).get('forbidden', [])
            ),
            emotion_control=EmotionControlRule(
                transitions_per_chapter=data.get('emotion_control', {}).get('transitions_per_chapter', 3),
                climax_intensity=data.get('emotion_control', {}).get('climax_intensity', 8),
                no_regression=data.get('emotion_control', {}).get('no_regression', True)
            ),
            forbidden=[
                ForbiddenItem(
                    item=f.get('item', ''),
                    description=f.get('description', ''),
                    example=f.get('example', '')
                )
                for f in data.get('forbidden', {}).get('content', [])
            ]
        )
    
    def _get_default_writing_style(self) -> Dict:
        """获取默认文风技法"""
        return {
            'paragraph': {'max_lines': 3, 'avg_length': '30-50字', 'mobile_first': True},
            'sentence': {'short_ratio': 0.6, 'max_length': 15, 'colloquial': True},
            'dialogue': {'ratio': 0.5, 'format': '""', 'one_per_paragraph': True, 'tags': []},
            'pacing': {'conflict_first_300': True, 'mini_burst_every_1000': True, 'hook_last_50': True, 'no_dialogue_limit': 200},
            'shock_flow': {'principles': [], 'forbidden': []},
            'emotion_control': {'transitions_per_chapter': 3, 'climax_intensity': 8, 'no_regression': True},
            'forbidden': {'content': []}
        }


# ==================== Layer 5 Loader ====================

class AIConstraintsLoader(BaseLoader):
    """Layer 5: AI约束加载器"""
    
    def load(self) -> AIConstraints:
        """加载AI约束"""
        cache_key = "ai_constraints"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        file_path = self.base_path / "ai_constraints.yaml"
        
        try:
            data = self._load_yaml(file_path)
        except FileNotFoundError:
            logger.warning("找不到AI约束，使用默认")
            data = self._get_default_ai_constraints()
        
        constraints = self._parse_ai_constraints(data)
        self._cache[cache_key] = constraints
        return constraints
    
    def _parse_ai_constraints(self, data: Dict) -> AIConstraints:
        """解析AI约束"""
        return AIConstraints(
            word_count=WordCountConstraint(
                target=data.get('word_count', {}).get('target', 2200),
                min=data.get('word_count', {}).get('min', 2000),
                max=data.get('word_count', {}).get('max', 2500),
                tolerance=data.get('word_count', {}).get('tolerance', 0.1)
            ),
            format_rules=FormatRule(
                dialogue_wrapper=data.get('format_rules', {}).get('dialogue_wrapper', '""'),
                system_wrapper=data.get('format_rules', {}).get('system_wrapper', '【】'),
                paragraph_max_lines=data.get('format_rules', {}).get('paragraph_max_lines', 3),
                paragraph_max_chars=data.get('format_rules', {}).get('paragraph_max_chars', 80)
            ),
            safety=SafetyConstraint(
                sensitive_words_filter=data.get('safety', {}).get('sensitive_words_filter', True),
                political_correctness=data.get('safety', {}).get('political_correctness', True),
                violence_level=data.get('safety', {}).get('violence_level', '轻度')
            ),
            forbidden=data.get('forbidden', {}).get('content', [])
        )
    
    def _get_default_ai_constraints(self) -> Dict:
        """获取默认AI约束"""
        return {
            'word_count': {'target': 2200, 'min': 2000, 'max': 2500, 'tolerance': 0.1},
            'format_rules': {'dialogue_wrapper': '""', 'system_wrapper': '【】', 'paragraph_max_lines': 3, 'paragraph_max_chars': 80},
            'safety': {'sensitive_words_filter': True, 'political_correctness': True, 'violence_level': '轻度'},
            'forbidden': {'content': []}
        }


# ==================== Layer 6 Loader ====================

class SelfCheckLoader(BaseLoader):
    """Layer 6: 自检清单加载器"""
    
    def load(self) -> SelfCheck:
        """加载自检清单"""
        cache_key = "self_check"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        file_path = self.base_path / "self_check.yaml"
        
        try:
            data = self._load_yaml(file_path)
        except FileNotFoundError:
            logger.warning("找不到自检清单，使用默认")
            data = self._get_default_self_check()
        
        check = self._parse_self_check(data)
        self._cache[cache_key] = check
        return check
    
    def _parse_self_check(self, data: Dict) -> SelfCheck:
        """解析自检清单"""
        # 解析写前自检
        pre_writing = [
            CheckItem(
                item=ci.get('item', ''),
                check=ci.get('check'),
                critical=ci.get('critical', False)
            )
            for ci in data.get('pre_writing', {}).get('items', [])
        ]
        
        # 解析格式检查
        format_checks = [
            CheckItem(
                item=ci.get('item', ''),
                validator=ci.get('validator'),
                severity=ci.get('severity', 'warning')
            )
            for ci in data.get('post_writing', {}).get('format_check', [])
        ]
        
        return SelfCheck(
            pre_writing=pre_writing,
            post_writing_format=format_checks,
            execution_rules=data.get('execution_rules', {})
        )
    
    def _get_default_self_check(self) -> Dict:
        """获取默认自检清单"""
        return {
            'pre_writing': {'items': []},
            'post_writing': {'format_check': []},
            'execution_rules': {}
        }


# ==================== 快捷函数 ====================

_loaders: Dict[str, Any] = {}

def get_loader(loader_type: str) -> BaseLoader:
    """获取Loader实例（单例）"""
    global _loaders
    if loader_type not in _loaders:
        loader_map = {
            'core_setting': CoreSettingLoader,
            'tactical_planning': TacticalPlanningLoader,
            'genre_techniques': GenreTechniquesLoader,
            'writing_style': WritingStyleLoader,
            'ai_constraints': AIConstraintsLoader,
            'self_check': SelfCheckLoader
        }
        loader_class = loader_map.get(loader_type)
        if loader_class:
            _loaders[loader_type] = loader_class()
        else:
            raise ValueError(f"未知的Loader类型: {loader_type}")
    return _loaders[loader_type]
