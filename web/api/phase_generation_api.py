

"""
两阶段小说生成API接口 - 完整版本
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
import re
import os
import json
from pathlib import Path
from functools import wraps
from typing import Dict, Any, Optional

# 创建蓝图
phase_api = Blueprint('phase_api', __name__)

# 导入全局变量和日志记录器
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

# 初始化日志记录器
logger = get_logger(__name__)

# 导入路径工具
from web.utils.path_utils import (
    get_user_novel_dir,
    get_novel_project_dir,
    find_novel_project,
    get_current_username,
    is_admin
)

# 视频项目目录
VIDEO_PROJECTS_DIR = Path(__file__).parent.parent.parent / '视频项目'

# 导入管理器
try:
    from web.managers.novel_manager import NovelGenerationManager
    manager = NovelGenerationManager()
except Exception as e:
    print(f"Cannot initialize NovelGenerationManager: {e}")
    manager = None

# API登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'logged_in' not in session:
            return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated_function


# ==================== 期待感辅助函数 ====================

def select_expectation_type(event):
    """
    根据事件特征智能选择期待感类型
    
    改进策略：
    1. 扩展关键词匹配规则
    2. 添加情感强度分析
    3. 引入多样性机制，避免所有事件都是同一类型
    4. 考虑阶段特点（不同阶段偏好不同类型）
    """
    from src.managers.ExpectationManager import ExpectationType
    import hashlib
    
    main_goal = event.get('main_goal', '').lower()
    emotional_focus = event.get('emotional_focus', '').lower()
    name = event.get('name', '').lower()
    description = event.get('description', '').lower()
    role_in_stage_arc = event.get('role_in_stage_arc', '').lower()
    
    # 组合所有文本用于分析
    all_text = f"{main_goal} {emotional_focus} {name} {description} {role_in_stage_arc}"
    
    # 决策树：根据事件特征选择期待类型（扩展版）
    scores = {
        ExpectationType.SUPPRESSION_RELEASE: 0,
        ExpectationType.SHOWCASE: 0,
        ExpectationType.MYSTERY_FORESHADOW: 0,
        ExpectationType.EMOTIONAL_HOOK: 0,
        ExpectationType.POWER_GAP: 0,
        ExpectationType.NESTED_DOLL: 0
    }
    
    # 压抑释放类型关键词
    suppression_keywords = ['击败', '战胜', '复仇', '反击', '雪耻', '逆袭', '反杀', '报仇',
                           '报复', '反击战', '翻盘', '逆转', '反攻', '压制']
    for kw in suppression_keywords:
        if kw in all_text:
            scores[ExpectationType.SUPPRESSION_RELEASE] += 3
    
    # 展示橱窗类型关键词
    showcase_keywords = ['获得', '得到', '炼成', '夺取', '夺取', '收获', '宝物', '神器',
                         '功法', '秘籍', '法宝', '装备', '宝藏', '发现', '解锁']
    for kw in showcase_keywords:
        if kw in all_text:
            scores[ExpectationType.SHOWCASE] += 3
    
    # 伏笔揭秘类型关键词
    mystery_keywords = ['揭秘', '真相', '发现', '秘密', '身世', '阴谋', '计谋', '背后',
                        '来历', '身份', '真实', '隐藏', '揭开', '曝光']
    for kw in mystery_keywords:
        if kw in all_text:
            scores[ExpectationType.MYSTERY_FORESHADOW] += 3
    
    # 情绪钩子类型关键词
    emotion_keywords = ['误解', '轻视', '震惊', '打脸', '羞辱', '嘲讽', '看不起',
                        '不屑', '挑衅', '羞耻', '愤怒', '爆发']
    for kw in emotion_keywords:
        if kw in all_text:
            scores[ExpectationType.EMOTIONAL_HOOK] += 3
    
    # 实力差距类型关键词
    power_keywords = ['展示', '学习', '修炼', '提升', '突破', '成长', '进阶', '升级',
                      '修炼', '功法', '实力', '境界', '修炼']
    for kw in power_keywords:
        if kw in all_text:
            scores[ExpectationType.POWER_GAP] += 2
    
    # 套娃期待类型关键词（默认类型）
    nested_keywords = ['挑战', '任务', '试炼', '考验', '闯关', '冒险', '探索',
                       '旅程', '征程', '历练']
    for kw in nested_keywords:
        if kw in all_text:
            scores[ExpectationType.NESTED_DOLL] += 2
    
    # 情感强度加成
    emotional_intensity = event.get('emotional_intensity', 'medium')
    if emotional_intensity == 'high':
        # 高强度事件更倾向于压抑释放或情绪钩子
        scores[ExpectationType.SUPPRESSION_RELEASE] += 1
        scores[ExpectationType.EMOTIONAL_HOOK] += 1
    elif emotional_intensity == 'low':
        # 低强度事件更倾向于展示橱窗或套娃期待
        scores[ExpectationType.SHOWCASE] += 1
        scores[ExpectationType.NESTED_DOLL] += 1
    
    # 基于事件名称的哈希值增加随机性（确保相同事件总是得到相同类型）
    event_hash = int(hashlib.md5(name.encode()).hexdigest(), 16)
    random_bonus = event_hash % 3  # 0-2的随机加成
    
    # 给得分最高的类型加随机分
    max_score = max(scores.values())
    best_types = [t for t, s in scores.items() if s == max_score]
    if best_types:
        import random
        selected_type = random.choice(best_types)
        scores[selected_type] += random_bonus
    
    # 选择得分最高的类型
    final_type = max(scores.items(), key=lambda x: x[1])[0]
    
    return final_type

# ==================== 阶段顺序常量 ====================

STAGE_ORDER = ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage']
STAGE_ORDER_MAP = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}

def get_sorted_stages(stage_names):
    """按照标准阶段顺序排序阶段名称"""
    # 分离标准阶段和非标准阶段
    standard_stages = [s for s in stage_names if s in STAGE_ORDER_MAP]
    non_standard_stages = [s for s in stage_names if s not in STAGE_ORDER_MAP]
    
    # 标准阶段按预定顺序排序，非标准阶段保持原顺序
    sorted_standard = sorted(standard_stages, key=lambda x: STAGE_ORDER_MAP[x])
    
    return sorted_standard + non_standard_stages

# ==================== 辅助函数 ====================

def normalize_chapter_range(chapter_range: str) -> str:
    """
    标准化章节范围格式
    
    支持的输入格式:
    - "101-103" -> 保持
    - "101-103章" -> "101-103章"
    - "第1章" -> "第1章"
    - "第3-4章" -> "第3-4章"
    - "101-103章" -> "101-103章"
    
    返回: 统一格式的章节范围字符串
    """
    if not chapter_range:
        return ""
    
    # 如果已经以"章"结尾，保持原样
    if chapter_range.endswith("章"):
        return chapter_range
    
    # 如果是纯数字范围格式（如"101-103"），添加"章"后缀
    # 但只在不包含其他文字时添加
    if re.match(r'^\d+-\d+$', chapter_range):
        return f"{chapter_range}章"
    
    # 如果是单个数字（如"110"），添加"第"和"章"
    if re.match(r'^\d+$', chapter_range):
        return f"第{chapter_range}章"
    
    # 其他情况保持原样
    return chapter_range

# ==================== 统一的产物加载工具类 ====================

class ProductLoader:
    """统一的产物加载器"""
    
    def __init__(self, title, logger_instance):
        self.title = title
        self.original_title = title
        self.safe_title = re.sub(r'[\\/*?"<>|]', "_", title)
        self.logger = logger_instance
        
        # 🔥 用户隔离：使用新的路径查找方法
        username = get_current_username()
        found_path = find_novel_project(self.original_title, username)
        
        if found_path:
            self.project_dir = found_path
        else:
            # 默认使用用户目录下的路径（用于新建项目）
            self.project_dir = get_novel_project_dir(self.original_title, username, create=False)
        
        # 🔥 调试信息
        if not self.project_dir.exists():
            self.logger.info(f"[PATH_DEBUG] 项目目录不存在，将使用: {self.project_dir}")
        
        # 兼容旧路径
        self.legacy_phase_one_dir = Path("小说项目") / f"{self.original_title}_第一阶段设定"
    
    def load_all_products(self):
        products = {
            'worldview': self._create_empty_product('世界观设定'),
            'characters': self._create_empty_product('角色设计'),
            'factions': self._create_empty_product('势力/阵营系统'),  # 🔥 新增：包含势力系统
            'growth': self._create_empty_product('成长路线'),
            'writing': self._create_empty_product('写作计划'),
            'storyline': self._create_empty_product('故事线'),
            'market': self._create_empty_product('市场分析')
        }
        
        self._load_from_quality_data(products)
        self._load_from_standard_structure(products)
        self._load_from_legacy_structure(products)
        self._load_from_phase_one_file(products)
        
        # 🔥 新增：尝试加载势力系统
        self._load_faction_system(products)
        
        return products
    
    def _load_faction_system(self, products):
        """内部方法：加载势力系统到产物字典"""
        try:
            # 🔥 内联势力系统加载逻辑
            faction_data = None
            
            # 1. 尝试从项目目录加载
            # 🔥 修复：优先检查 materials/worldview，因为这是新的标准路径
            worldview_dir = self.project_dir / "materials" / "worldview"
            if not worldview_dir.exists():
                worldview_dir = self.project_dir / "worldview"
            
            if worldview_dir.exists():
                faction_files = list(worldview_dir.glob("*_势力系统.json"))
                if faction_files:
                    with open(faction_files[0], 'r', encoding='utf-8') as f:
                        faction_data = json.load(f)
                    self.logger.info(f"从项目目录加载势力系统: {faction_files[0].name}")
            
            # 2. 如果项目目录未找到，尝试从 quality_data 加载
            if not faction_data and manager:
                novel_detail = manager.get_novel_detail(self.title)
                if novel_detail:
                    quality_data = novel_detail.get("quality_data", {})
                    if quality_data:
                        writing_plans = quality_data.get("writing_plans", {})
                        for stage_name, plan_data in writing_plans.items():
                            if isinstance(plan_data, dict):
                                stage_faction = plan_data.get('faction_system') or plan_data.get('stage_writing_plan', {}).get('faction_system')
                                if stage_faction:
                                    faction_data = stage_faction
                                    self.logger.info(f"从写作计划加载势力系统: {stage_name}")
                                    break
            
            # 3. 将加载的数据填充到产物字典
            if faction_data:
                products['factions']['content'] = json.dumps(faction_data, ensure_ascii=False, indent=2)
                products['factions']['complete'] = True
                self.logger.info(f"✅ 已加载产物: factions (从势力系统)")
        except Exception as e:
            self.logger.info(f"加载势力系统失败: {e}")
    
    def _create_empty_product(self, title):
        return {'title': title, 'content': '', 'complete': False, 'file_path': ''}
        
    
    def _load_from_quality_data(self, products):
        if not manager:
            return
        novel_detail = manager.get_novel_detail(self.title)
        if not novel_detail:
            return
        quality_data = novel_detail.get("quality_data", {})
        if not quality_data:
            return
        
        self.logger.info(f"[PRODUCTS_DEBUG] 从manager获取quality_data，包含 {len(quality_data)} 个键")
        
        writing_plans = quality_data.get("writing_plans", {})
        if writing_plans:
            self.logger.info(f"[PRODUCTS_DEBUG] 从quality_data找到 {len(writing_plans)} 个写作计划")
            
            # 🔥 修复：合并所有阶段的写作计划，而不是只取第一个
            all_stages = {}
            stage_names = []
            
            for stage_name, plan_data in writing_plans.items():
                if plan_data and isinstance(plan_data, dict):
                    all_stages[stage_name] = plan_data
                    stage_names.append(stage_name)
                    self.logger.info(f"  收集阶段: {stage_name}")
            
            if all_stages:
                # 创建合并后的写作计划（与_load_writing_plans中的格式一致）
                merged_plan = {
                    'stage_names': stage_names,
                    'total_stages': len(stage_names),
                    'stages': all_stages
                }
                
                products['writing']['content'] = json.dumps(merged_plan, ensure_ascii=False, indent=2)
                products['writing']['complete'] = True
                products['writing']['file_path'] = f"quality_data/writing_plans/merged"
                self.logger.info(f"从quality_data加载合并的写作计划: {len(stage_names)} 个阶段 ({stage_names})")
    
    def _load_from_standard_structure(self, products):
        if not products['worldview']['complete']:
            self._load_worldview(products)
        
        if not products['characters']['complete']:
            self._load_characters(products)
        
        if not products['growth']['complete']:
            self._load_growth_plan(products)
        
        if not products['writing']['complete']:
            self._load_writing_plans(products)
        
        if not products['market']['complete']:
            self._load_market_analysis(products)
        
        if not products['storyline']['complete'] and products['writing']['complete']:
            self._extract_storyline_from_writing(products)
    
    def _load_worldview(self, products):
        # 🔥 修复：优先检查 materials/worldview，因为这是新的标准路径
        worldview_dir = self.project_dir / "materials" / "worldview"
        if not worldview_dir.exists():
            worldview_dir = self.project_dir / "worldview"
        
        if worldview_dir.exists():
            worldview_files = list(worldview_dir.glob("*.json"))
            if worldview_files:
                try:
                    with open(worldview_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    products['worldview']['content'] = json.dumps(data, ensure_ascii=False, indent=2)
                    products['worldview']['complete'] = True
                    products['worldview']['file_path'] = str(worldview_files[0])
                    self.logger.info(f"已加载产物: worldview (从 {worldview_files[0].name})")
                except Exception as e:
                    self.logger.error(f"加载worldview失败: {e}")
    
    def _load_characters(self, products):
        characters_dir = self.project_dir / "characters"
        if not characters_dir.exists():
            return
        
        character_files = list(characters_dir.glob("*.json"))
        if character_files:
            try:
                with open(character_files[0], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products['characters']['content'] = json.dumps(data, ensure_ascii=False, indent=2)
                products['characters']['complete'] = True
                products['characters']['file_path'] = str(character_files[0])
                self.logger.info(f"已加载产物: characters (从 {character_files[0].name})")
            except Exception as e:
                self.logger.error(f"加载characters失败: {e}")
    
    def _load_writing_plans(self, products):
        # 首先尝试从 plans 目录加载所有阶段的写作计划
        plans_dir = self.project_dir / "plans"
        if plans_dir.exists():
            stage_files = list(plans_dir.glob("*_writing_plan.json"))
            if stage_files:
                try:
                    # 先收集所有文件和对应的阶段名称
                    file_stage_pairs = []
                    
                    for stage_file in stage_files:
                        # 从文件名提取阶段名称
                        # 文件名格式: 吞噬万界：从一把生锈铁剑开始_climax_stage_writing_plan.json
                        # 使用正则表达式匹配 (xxx)_stage)_writing_plan
                        import re
                        match = re.search(r'_([^_]+_stage)_writing_plan$', stage_file.name)
                        if match:
                            stage_name = match.group(1)
                        else:
                            # 备用方案：尝试从 stem 中提取
                            stem = stage_file.stem  # xxx_climax_stage
                            parts = stem.split('_')
                            # 找到包含 'stage' 的部分
                            stage_name = None
                            for i, part in enumerate(parts):
                                if 'stage' in part and i > 0:
                                    # 重建阶段名称（可能包含多个下划线）
                                    stage_parts = []
                                    for j in range(1, i + 1):
                                        stage_parts.append(parts[j])
                                    stage_name = '_'.join(stage_parts)
                                    break
                            
                            if not stage_name:
                                continue
                        
                        # 只处理标准阶段
                        if stage_name not in STAGE_ORDER_MAP:
                            self.logger.info(f"  跳过非标准阶段: {stage_name} (文件: {stage_file.name})")
                            continue
                        
                        file_stage_pairs.append((stage_name, stage_file))
                        self.logger.info(f"  找到阶段文件: {stage_name} -> {stage_file.name}")
                    
                    # 按照标准阶段顺序排序文件
                    sorted_pairs = sorted(file_stage_pairs, key=lambda x: STAGE_ORDER_MAP.get(x[0], 999))
                    self.logger.info(f"  排序后的阶段顺序: {[p[0] for p in sorted_pairs]}")
                    
                    # 合并所有阶段的写作计划
                    all_stages = {}
                    stage_names = []
                    
                    for stage_name, stage_file in sorted_pairs:
                        with open(stage_file, 'r', encoding='utf-8') as f:
                            stage_data = json.load(f)
                        
                        # 存储阶段数据
                        all_stages[stage_name] = stage_data
                        stage_names.append(stage_name)
                        self.logger.info(f"  加载阶段: {stage_name} (从 {stage_file.name})")
                    
                    # 创建合并后的写作计划
                    merged_plan = {
                        'stage_names': stage_names,
                        'total_stages': len(stage_files),
                        'stages': all_stages
                    }
                    
                    products['writing']['content'] = json.dumps(merged_plan, ensure_ascii=False, indent=2)
                    products['writing']['complete'] = True
                    products['writing']['file_path'] = str(plans_dir)
                    self.logger.info(f"已加载产物: writing (从 {len(stage_files)} 个阶段文件)")
                    return
                except Exception as e:
                    self.logger.error(f"从 plans 目录加载writing计划失败: {e}")
        
        # 备用方案：从 planning 目录加载
        planning_dir = self.project_dir / "planning"
        if planning_dir.exists():
            # 🔥 修复：只使用original_title，移除safe_title
            patterns = [
                f"{self.original_title}_*_writing_plan*.json",
                "*writing_plan*.json"
            ]
            
            for pattern in patterns:
                matching_files = list(planning_dir.glob(pattern))
                if matching_files:
                    try:
                        with open(matching_files[0], 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        products['writing']['content'] = json.dumps(data, ensure_ascii=False, indent=2)
                        products['writing']['complete'] = True
                        products['writing']['file_path'] = str(matching_files[0])
                        self.logger.info(f"已加载产物: writing (从 {matching_files[0].name})")
                        return
                    except Exception as e:
                        self.logger.error(f"加载writing计划失败: {e}")
        
        stage_plans_dir = self.project_dir / "stage_writing_plans"
        if stage_plans_dir.exists():
            plan_files = list(stage_plans_dir.glob("*.json"))
            if plan_files:
                try:
                    with open(plan_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    products['writing']['content'] = json.dumps(data, ensure_ascii=False, indent=2)
                    products['writing']['complete'] = True
                    products['writing']['file_path'] = str(plan_files[0])
                    self.logger.info(f"已加载产物: writing (从 {plan_files[0].name})")
                except Exception as e:
                    self.logger.error(f"加载writing计划失败: {e}")
    
    def _load_growth_plan(self, products):
        """加载成长路线文件"""
        self.logger.info(f"[GROWTH_DEBUG] 开始加载成长路线: original_title={self.original_title}, safe_title={self.safe_title}")
        self.logger.info(f"[GROWTH_DEBUG] 项目目录: {self.project_dir}")
        self.logger.info(f"[GROWTH_DEBUG] 项目目录是否存在: {self.project_dir.exists()}")
        
        growth_dirs = [
            self.project_dir / "planning",
            self.project_dir / "materials" / "phase_one_products"
        ]
        
        for idx, growth_dir in enumerate(growth_dirs):
            self.logger.info(f"[GROWTH_DEBUG] 检查目录 {idx}: {growth_dir}, 存在: {growth_dir.exists()}")
            
            if not growth_dir.exists():
                continue
            
            # 尝试多种可能的文件名模式
            patterns = [
                f"{self.original_title}_成长路线.json",
                f"{self.safe_title}_成长路线.json",
                "*_成长路线.json",
                "*growth*.json"
            ]
            
            for pattern in patterns:
                self.logger.info(f"[GROWTH_DEBUG]  搜索模式: {pattern}")
                matching_files = list(growth_dir.glob(pattern))
                self.logger.info(f"[GROWTH_DEBUG]  找到文件数: {len(matching_files)}")
                if matching_files:
                    self.logger.info(f"[GROWTH_DEBUG]  文件列表: {[f.name for f in matching_files]}")
                
                if matching_files:
                    try:
                        with open(matching_files[0], 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        products['growth']['content'] = json.dumps(data, ensure_ascii=False, indent=2)
                        products['growth']['complete'] = True
                        products['growth']['file_path'] = str(matching_files[0])
                        self.logger.info(f"已加载产物: growth (从 {matching_files[0].name})")
                        return
                    except Exception as e:
                        self.logger.error(f"加载growth计划失败: {e}")
        
        self.logger.info(f"[GROWTH_DEBUG] 未找到成长路线文件")
    
    def _load_market_analysis(self, products):
        market_dirs = [
            self.project_dir / "market_analysis",
            self.project_dir / "materials" / "market_analysis"
        ]
        
        for market_dir in market_dirs:
            if market_dir.exists():
                market_files = list(market_dir.glob("*.json"))
                if market_files:
                    try:
                        with open(market_files[0], 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        products['market']['content'] = json.dumps(data, ensure_ascii=False, indent=2)
                        products['market']['complete'] = True
                        products['market']['file_path'] = str(market_files[0])
                        self.logger.info(f"已加载产物: market (从 {market_files[0].name})")
                        return
                    except Exception as e:
                        self.logger.error(f"加载market分析失败: {e}")
    
    def _extract_storyline_from_writing(self, products):
        try:
            writing_content = products['writing']['content']
            if not writing_content:
                return
            
            writing_data = json.loads(writing_content)
            
            # 检查是否是多阶段合并的写作计划
            if 'stages' in writing_data and 'stage_names' in writing_data:
                # 从所有阶段提取重大事件
                all_major_events = []
                stage_info = []
                all_expectation_maps = {}  # 🔥 新增：收集所有阶段的期待感映射
                
                # 按照标准阶段顺序排序
                sorted_stage_names = get_sorted_stages(writing_data['stage_names'])
                
                for stage_name in sorted_stage_names:
                    if stage_name in writing_data['stages']:
                        stage_data = writing_data['stages'][stage_name]
                        stage_plan = stage_data.get('stage_writing_plan', {})
                        
                        # 🔥 新增：优先检查stage_plan中是否已经有expectation_map
                        expectation_map = stage_plan.get('expectation_map')
                        if expectation_map:
                            all_expectation_maps[stage_name] = expectation_map
                            total_exp = len(expectation_map.get('expectations', {}))
                            self.logger.info(f"[STORYLINE] 从{stage_name}加载已有的期待感映射: {total_exp} 个期待")
                        
                        # 提取该阶段的重大事件
                        major_events = stage_plan.get('event_system', {}).get('major_events', [])
                        # 🔥 修复：也提取特殊情感事件
                        special_emotional_events = stage_plan.get('event_system', {}).get('special_emotional_events', [])
                        
                        # 🔥 修复：无论是否有事件，都添加stage_info
                        stage_info.append({
                            'stage_name': stage_name,
                            'chapter_range': stage_plan.get('chapter_range', ''),
                            'major_event_count': len(major_events)
                        })
                        
                        if major_events:
                            # 为每个事件添加阶段信息和中级事件
                            for event in major_events:
                                event['_stage'] = stage_name
                                event['_chapter_range'] = stage_plan.get('chapter_range', '')
                                
                                # 🔥 新增：解析起始章节用于排序
                                chapter_range = event.get('chapter_range', '1-10')
                                try:
                                    from src.managers.StagePlanUtils import parse_chapter_range
                                    start_ch, _ = parse_chapter_range(chapter_range)
                                    event['_start_chapter'] = start_ch
                                except:
                                    event['_start_chapter'] = 1
                                
                                # 确保 composition 中的中级事件也添加到事件对象中
                                # 保留所有原始字段，包括 special_events
                                if 'composition' in event:
                                    for phase_name, phase_events in event['composition'].items():
                                        if isinstance(phase_events, list):
                                            if '_medium_events' not in event:
                                                event['_medium_events'] = []
                                            # 保留完整的原始数据，只添加 phase 标记
                                            for me in phase_events:
                                                # 创建副本以避免修改原始数据
                                                me_copy = dict(me)
                                                me_copy['phase'] = phase_name
                                                me_copy['_phase_name'] = phase_name  # 用于前端显示
                                                # 标准化章节范围格式
                                                if 'chapter_range' in me_copy:
                                                    me_copy['_chapter_range_normalized'] = normalize_chapter_range(me_copy['chapter_range'])
                                                event['_medium_events'].append(me_copy)
                                
                                # 🔥 修复：为每个重大事件添加特殊情感事件
                                if special_emotional_events and 'special_emotional_events' not in event:
                                    event['special_emotional_events'] = special_emotional_events
                            
                            all_major_events.extend(major_events)
                
                # 🔥 新增：按章节顺序排序所有事件
                all_major_events.sort(key=lambda e: e.get('_start_chapter', 1))
                self.logger.info(f"[STORYLINE_DEBUG] 按章节排序后的事件顺序: {[(e.get('name'), e.get('_start_chapter')) for e in all_major_events]}")
                
                if all_major_events:
                    storyline_data = {
                        'stage_info': stage_info,
                        'total_major_events': len(all_major_events),
                        'major_events': all_major_events
                    }
                    # 🔥 新增：打印调试信息
                    stage_names_debug = [s.get('stage_name', 'unknown') for s in stage_info]
                    logger.info(f"[STORYLINE_DEBUG] 提取的故事线包含阶段: {stage_names_debug}")
                    logger.info(f"[STORYLINE_DEBUG] 总事件数: {len(all_major_events)}, 各阶段事件数: {[(s.get('stage_name'), s.get('major_event_count')) for s in stage_info]}")
                    
                    # 🔥 新增：添加期待感映射到故事线数据
                    if all_expectation_maps:
                        storyline_data['expectation_maps'] = all_expectation_maps
                        total_expectations = sum(len(em.get('expectations', {})) for em in all_expectation_maps.values())
                        self.logger.info(f"[EXPECTATION_MAP] 添加期待感映射到故事线: {len(all_expectation_maps)} 个阶段, 共 {total_expectations} 个期待")
                    
                    products['storyline']['content'] = json.dumps(storyline_data, ensure_ascii=False, indent=2)
                    products['storyline']['complete'] = True
                    products['storyline']['file_path'] = products['writing']['file_path']
                    self.logger.info(f"从写作计划提取storyline数据: {len(stage_info)} 个阶段, {len(all_major_events)} 个重大事件")
                    return
            
            # 检查是否是单阶段写作计划（旧格式）
            # 🔥 修复：明确检查major_events是否存在，避免空数组被当作falsy值
            event_system = writing_data.get('stage_writing_plan', {}).get('event_system', {})
            if 'major_events' in event_system:
                # 如果有major_events字段（即使是空数组），也使用它
                storyline_data = {
                    'major_events': event_system['major_events'],
                    'stage_name': writing_data.get('stage_name', '全书'),
                    'chapter_range': writing_data.get('chapter_range', '')
                }
            else:
                # 备用方案：尝试其他数据源
                storyline_data = (
                    writing_data.get('overall_stage_plans', {}) or
                    writing_data.get('global_growth_plan', {})
                )
            
            if storyline_data:
                products['storyline']['content'] = json.dumps(storyline_data, ensure_ascii=False, indent=2)
                products['storyline']['complete'] = True
                products['storyline']['file_path'] = products['writing']['file_path']
                self.logger.info(f"从写作计划提取storyline数据")
        except Exception as e:
            self.logger.error(f"提取storyline失败: {e}")
    
    def _load_from_legacy_structure(self, products):
        products_dir = self.legacy_phase_one_dir / "产物"
        if not products_dir.exists():
            return
        
        # 🔥 修复：使用original_title而不是safe_title，因为实际文件名保留了中文标点
        product_files = {
            'worldview': f"{self.original_title}_世界观设定.json",
            'characters': f"{self.original_title}_角色设计.json",
            'growth': f"{self.original_title}_成长路线.json",
            'writing': f"{self.original_title}_写作计划.json",
            'storyline': f"{self.original_title}_阶段计划.json",  # 这个作为备用
            'market': f"{self.original_title}_市场分析.json"
        }
        
        for category, filename in product_files.items():
            if products[category]['complete']:
                continue
                
            file_path = products_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    
                    # 特殊处理：storyline 应该从写作计划中提取 major_events
                    if category == 'storyline':
                        # 优先从 plans 目录加载完整的故事线
                        plans_dir = self.project_dir / "plans"
                        if plans_dir.exists():
                            stage_files = list(plans_dir.glob("*_writing_plan.json"))
                            if stage_files:
                                try:
                                    # 先收集所有文件和对应的阶段名称
                                    file_stage_pairs = []
                                    
                                    for stage_file in stage_files:
                                        # 从文件名提取阶段名称
                                        # 文件名格式: 吞噬万界：从一把生锈铁剑开始_climax_stage_writing_plan.json
                                        import re
                                        match = re.search(r'_([^_]+_stage)_writing_plan$', stage_file.name)
                                        if match:
                                            stage_name = match.group(1)
                                        else:
                                            # 备用方案：尝试从 stem 中提取
                                            stem = stage_file.stem
                                            parts = stem.split('_')
                                            stage_name = None
                                            for i, part in enumerate(parts):
                                                if 'stage' in part and i > 0:
                                                    stage_parts = []
                                                    for j in range(1, i + 1):
                                                        stage_parts.append(parts[j])
                                                    stage_name = '_'.join(stage_parts)
                                                    break
                                            
                                            if not stage_name:
                                                continue
                                        
                                        # 只处理标准阶段
                                        if stage_name not in STAGE_ORDER_MAP:
                                            continue
                                        
                                        with open(stage_file, 'r', encoding='utf-8') as f:
                                            stage_data = json.load(f)
                                        
                                        file_stage_pairs.append((stage_name, stage_file))
                                    
                                    # 按照标准阶段顺序排序文件
                                    sorted_pairs = sorted(file_stage_pairs, key=lambda x: STAGE_ORDER_MAP.get(x[0], 999))
                                    
                                    # 从所有阶段提取重大事件
                                    stage_name_to_events = {}  # 存储每个阶段的事件
                                    stage_name_to_info = {}  # 存储阶段信息
                                    all_expectation_maps = {}  # 🔥 新增：收集所有阶段的期待感映射
                                    
                                    for stage_name, stage_file in sorted_pairs:
                                        with open(stage_file, 'r', encoding='utf-8') as f:
                                            stage_data = json.load(f)
                                        
                                        stage_plan = stage_data.get('stage_writing_plan', {})
                                        
                                        # 🔥 新增：优先检查stage_plan中是否已经有expectation_map
                                        expectation_map = stage_plan.get('expectation_map')
                                        if expectation_map:
                                            all_expectation_maps[stage_name] = expectation_map
                                            total_exp = len(expectation_map.get('expectations', {}))
                                            self.logger.info(f"[STORYLINE] 从{stage_name}加载已有的期待感映射: {total_exp} 个期待")
                                        
                                        major_events = stage_plan.get('event_system', {}).get('major_events', [])
                                        # 🔥 修复：也提取特殊情感事件
                                        special_emotional_events = stage_plan.get('event_system', {}).get('special_emotional_events', [])
                                        
                                        if major_events:
                                            # 为每个事件添加阶段信息和中级事件
                                            for event in major_events:
                                                event['_stage'] = stage_name
                                                event['_chapter_range'] = stage_plan.get('chapter_range', '')
                                                # 确保 composition 中的中级事件也添加到事件对象中
                                                # 保留所有原始字段，包括 special_events
                                                if 'composition' in event:
                                                    for phase_name, phase_events in event['composition'].items():
                                                        if isinstance(phase_events, list):
                                                            if '_medium_events' not in event:
                                                                event['_medium_events'] = []
                                                            # 保留完整的原始数据，只添加 phase 标记
                                                            for me in phase_events:
                                                                # 创建副本以避免修改原始数据
                                                                me_copy = dict(me)
                                                                me_copy['phase'] = phase_name
                                                                me_copy['_phase_name'] = phase_name  # 用于前端显示
                                                                # 标准化章节范围格式
                                                                if 'chapter_range' in me_copy:
                                                                    me_copy['_chapter_range_normalized'] = normalize_chapter_range(me_copy['chapter_range'])
                                                                event['_medium_events'].append(me_copy)
                                                
                                                # 🔥 修复：为每个重大事件添加特殊情感事件
                                                if special_emotional_events and 'special_emotional_events' not in event:
                                                    event['special_emotional_events'] = special_emotional_events
                                            
                                            # 存储该阶段的事件
                                            stage_name_to_events[stage_name] = major_events
                                            
                                            # 存储阶段信息
                                            stage_name_to_info[stage_name] = {
                                                'stage_name': stage_name,
                                                'chapter_range': stage_plan.get('chapter_range', ''),
                                                'major_event_count': len(major_events)
                                            }
                                    
                                    # 按照标准阶段顺序排序并合并事件
                                    all_major_events = []
                                    stage_info = []
                                    
                                    sorted_stage_names = get_sorted_stages(list(stage_name_to_events.keys()))
                                    for stage_name in sorted_stage_names:
                                        if stage_name in stage_name_to_events:
                                            all_major_events.extend(stage_name_to_events[stage_name])
                                            stage_info.append(stage_name_to_info[stage_name])
                                    
                                    if all_major_events:
                                        storyline_data = {
                                            'stage_info': stage_info,
                                            'total_major_events': len(all_major_events),
                                            'major_events': all_major_events
                                        }
                                        
                                        # 🔥 新增：添加期待感映射到故事线数据
                                        if all_expectation_maps:
                                            storyline_data['expectation_maps'] = all_expectation_maps
                                            total_expectations = sum(len(em.get('expectations', {})) for em in all_expectation_maps.values())
                                            self.logger.info(f"[EXPECTATION_MAP] 添加期待感映射到故事线(旧格式): {len(all_expectation_maps)} 个阶段, 共 {total_expectations} 个期待")
                                        
                                        products[category]['content'] = json.dumps(storyline_data, ensure_ascii=False, indent=2)
                                        products[category]['complete'] = True
                                        products[category]['file_path'] = str(plans_dir)
                                        self.logger.info(f"已加载产物(旧格式): {category} (从 {len(stage_info)} 个阶段提取)")
                                        continue
                                except Exception as e:
                                    self.logger.info(f"从 plans 目录提取storyline失败: {e}")
                            
                            # 备用方案：尝试从写作计划中提取重大事件
                            writing_file = products_dir / product_files['writing']
                            if writing_file.exists():
                                try:
                                    with open(writing_file, 'r', encoding='utf-8') as wf:
                                        writing_data = json.load(wf)
                                    
                                    # 从所有阶段的写作计划中提取 major_events
                                    all_major_events = []
                                    stage_info = []
                                    
                                    for stage_key in STAGE_ORDER:
                                        if stage_key in writing_data:
                                            stage_plan = writing_data[stage_key].get('stage_writing_plan', {})
                                            events = stage_plan.get('event_system', {}).get('major_events', [])
                                            # 🔥 修复：也提取特殊情感事件
                                            special_emotional_events = stage_plan.get('event_system', {}).get('special_emotional_events', [])
                                            
                                            if events:
                                                    # 为每个事件添加阶段信息和中级事件
                                                    for event in events:
                                                        event['_stage'] = stage_key
                                                        event['_chapter_range'] = stage_plan.get('chapter_range', '')
                                                        # 确保 composition 中的中级事件也添加到事件对象中
                                                        # 保留所有原始字段，包括 special_events
                                                        if 'composition' in event:
                                                            for phase_name, phase_events in event['composition'].items():
                                                                if isinstance(phase_events, list):
                                                                    if '_medium_events' not in event:
                                                                        event['_medium_events'] = []
                                                                    # 保留完整的原始数据，只添加 phase 标记
                                                                    for me in phase_events:
                                                                        # 创建副本以避免修改原始数据
                                                                        me_copy = dict(me)
                                                                        me_copy['phase'] = phase_name
                                                                        me_copy['_phase_name'] = phase_name  # 用于前端显示
                                                                        # 标准化章节范围格式
                                                                        if 'chapter_range' in me_copy:
                                                                            me_copy['_chapter_range_normalized'] = normalize_chapter_range(me_copy['chapter_range'])
                                                                        event['_medium_events'].append(me_copy)
                                                        
                                                        # 🔥 修复：为每个重大事件添加特殊情感事件
                                                        if special_emotional_events and 'special_emotional_events' not in event:
                                                            event['special_emotional_events'] = special_emotional_events
                                                    
                                                    all_major_events.extend(events)
                                    
                                    stage_info.append({
                                                    'stage_name': stage_key,
                                                    'chapter_range': stage_plan.get('chapter_range', ''),
                                                    'major_event_count': len(events)
                                                })
                                    
                                    if all_major_events:
                                        storyline_data = {
                                            'stage_info': stage_info,
                                            'total_major_events': len(all_major_events),
                                            'major_events': all_major_events,
                                            'source': 'writing_plan'
                                        }
                                        products[category]['content'] = json.dumps(storyline_data, ensure_ascii=False, indent=2)
                                        products[category]['complete'] = True
                                        products[category]['file_path'] = str(writing_file)
                                        self.logger.info(f"已加载产物(旧格式): {category} (从 {len(stage_info)} 个阶段提取)")
                                        continue
                                except Exception as e:
                                    self.logger.info(f"从写作计划提取storyline失败: {e}")
                            
                            # 如果写作计划提取失败，使用阶段计划文件
                            products[category]['content'] = json.dumps(content, ensure_ascii=False, indent=2)
                            products[category]['complete'] = True
                            products[category]['file_path'] = str(file_path)
                            self.logger.info(f"已加载产物(旧格式): {category} (从阶段计划)")
                        else:
                            products[category]['content'] = json.dumps(content, ensure_ascii=False, indent=2)
                            products[category]['complete'] = True
                            products[category]['file_path'] = str(file_path)
                            self.logger.info(f"已加载产物(旧格式): {category}")
                    else:
                        products[category]['content'] = json.dumps(content, ensure_ascii=False, indent=2)
                        products[category]['complete'] = True
                        products[category]['file_path'] = str(file_path)
                        self.logger.info(f"已加载产物(旧格式): {category}")
                except Exception as e:
                    self.logger.info(f"读取产物文件失败(旧格式): {category}, {e}")
    
    def _load_from_phase_one_file(self, products):
        possible_files = [
            self.legacy_phase_one_dir / f"{self.original_title}_第一阶段设定.json",
            self.legacy_phase_one_dir / f"{self.safe_title}_第一阶段设定.json",
        ]
        
        for phase_one_file in possible_files:
            if not phase_one_file.exists():
                continue
                
            try:
                with open(phase_one_file, 'r', encoding='utf-8') as f:
                    phase_one_data = json.load(f)
                
                if 'core_worldview' in phase_one_data:
                    worldview_data = phase_one_data.get('core_worldview', {})
                    products['worldview']['content'] = json.dumps(worldview_data, ensure_ascii=False, indent=2)
                    products['worldview']['complete'] = True
                    products['worldview']['file_path'] = str(phase_one_file)
                    self.logger.info(f"从第一阶段设定文件加载世界观")
                
                if 'character_design' in phase_one_data:
                    character_data = phase_one_data.get('character_design', {})
                    products['characters']['content'] = json.dumps(character_data, ensure_ascii=False, indent=2)
                    products['characters']['complete'] = True
                    products['characters']['file_path'] = str(phase_one_file)
                    self.logger.info(f"从第一阶段设定文件加载角色设计")
                
                if 'stage_writing_plans' in phase_one_data:
                    writing_data = phase_one_data.get('stage_writing_plans', {})
                    products['writing']['content'] = json.dumps(writing_data, ensure_ascii=False, indent=2)
                    products['writing']['complete'] = True
                    products['writing']['file_path'] = str(phase_one_file)
                    self.logger.info(f"从第一阶段设定文件加载写作计划")
                
                return
            except Exception as e:
                self.logger.info(f"读取第一阶段设定文件失败: {e}")


# ==================== API路由 ====================

@phase_api.route('/phase-one/start-generation', methods=['POST'])
@login_required
def start_phase_one_generation():
    """启动第一阶段生成任务（兼容旧接口）"""
    return start_phase_one_generate()


@phase_api.route('/phase-one/generate', methods=['POST'])
@login_required
def start_phase_one_generate():
    """启动第一阶段生成任务（带点数扣除）"""
    logger.info("🚀 [PHASE_ONE_API] 收到生成请求")
    try:
        data = request.json or {}
        
        # 提取参数
        title = data.get('title')
        synopsis = data.get('synopsis')
        core_setting = data.get('core_setting')
        core_selling_points = data.get('core_selling_points')
        total_chapters = data.get('total_chapters', 200)
        generation_mode = data.get('generation_mode', 'phase_one_only')
        creative_seed = data.get('creative_seed')
        
        # 🔥 新增：支持目标平台参数
        target_platform = data.get('target_platform', 'fanqie')  # 默认番茄小说
        
        # 🔥 新增：支持 start_new 参数，用户选择"从新开始"时传递
        start_new = data.get('start_new', False)
        
        # 参数验证
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        if not synopsis:
            return jsonify({"success": False, "error": "小说简介不能为空"}), 400
        
        if not core_setting:
            return jsonify({"success": False, "error": "核心设定不能为空"}), 400
        
        logger.info(f"🚀 [PHASE_ONE] 开始生成第一阶段设定: {title}")
        logger.info(f"📋 [PHASE_ONE] 参数: total_chapters={total_chapters}, mode={generation_mode}")
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # ===== 创造点扣除逻辑 =====
        from web.models.point_model import point_model
        from flask import session
        
        # 计算第一阶段消耗（固定消耗）
        cost_breakdown = point_model.calculate_phase1_cost(total_chapters)
        total_cost = cost_breakdown['total']
        
        user_id = session.get('user_id')
        logger.info(f"💰 [PHASE_ONE] 需要消耗创造点: {total_cost}")
        
        # 检查余额
        user_points = point_model.get_user_points(user_id)
        if user_points['balance'] < total_cost:
            return jsonify({
                "success": False, 
                "error": f"创造点不足，需要{total_cost}点，当前余额{user_points['balance']}点",
                "required": total_cost,
                "balance": user_points['balance']
            }), 402  # Payment Required
        
        # 扣除点数
        spend_result = point_model.spend_points(
            user_id=user_id,
            amount=total_cost,
            source='phase1_generation',
            description=f'第一阶段生成小说设定: {title}',
            related_id=title
        )
        
        if not spend_result['success']:
            logger.error(f"❌ [PHASE_ONE] 扣除创造点失败: {spend_result.get('error')}")
            return jsonify({
                "success": False, 
                "error": f"扣除创造点失败: {spend_result.get('error')}"
            }), 500
        
        logger.info(f"✅ [PHASE_ONE] 已扣除创造点: {total_cost}，剩余: {spend_result['balance']}")
        # ===== 创造点扣除结束 =====
        
        # 构建创意种子（如果没有提供的话）
        if not creative_seed:
            creative_seed = {
                "novelTitle": title,
                "storySynopsis": synopsis,
                "coreSetting": core_setting,
                "coreSellingPoints": core_selling_points if isinstance(core_selling_points, list) else [core_selling_points] if core_selling_points else []
            }
        
        # 获取当前用户名
        username = get_current_username()
        logger.info(f"👤 [PHASE_ONE_API] 当前用户名: {username}")
        
        # 构建生成参数
        generation_params = {
            'title': title,
            'synopsis': synopsis,
            'core_setting': core_setting,
            'core_selling_points': core_selling_points,
            'total_chapters': total_chapters,
            'generation_mode': generation_mode,
            'creative_seed': creative_seed,
            'target_platform': target_platform,  # 🔥 新增：传递目标平台参数
            'start_new': start_new,  # 🔥 新增：传递 start_new 参数
            'user_id': user_id,  # 🔥 新增：传递用户ID用于API调用扣费
            'username': username,  # 🔥 新增：传递用户名用于目录结构
            'estimated_points': total_cost  # 🔥 新增：预估消耗点数
        }
        
        logger.info(f"📱 [PLATFORM] 目标平台: {target_platform}")
        
        # 调用管理器启动实际的第一阶段生成任务
        logger.info(f"🚀 [PHASE_ONE] 调用管理器启动生成任务...")
        task_id = manager.start_generation(generation_params)
        
        logger.info(f"✅ [PHASE_ONE] 任务已启动: {task_id}")
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"第一阶段生成任务已启动，已预扣{total_cost}创造点",
            "status": "initializing",
            "points_spent": total_cost,
            "points_estimated": total_cost,  # 预估点数（预扣费金额）
            "balance_after": spend_result['balance']
        })
        
    except Exception as e:
        logger.error(f"❌ [PHASE_ONE] 启动生成失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@phase_api.route('/phase-one/task/<task_id>/status', methods=['GET'])
@login_required
def get_phase_one_task_status(task_id):
    """获取第一阶段任务状态"""
    try:
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 从管理器获取任务状态
        task_status = manager.get_task_status(task_id)
        
        if "error" in task_status:
            return jsonify({"success": False, "error": task_status["error"]}), 404
        
        # 构建 data 对象
        data = {
            "task_id": task_id,
            "status": task_status.get("status", "unknown"),
            "progress": task_status.get("progress", 0),
            "message": task_status.get("status_message") or task_status.get("current_step") or "生成中...",
            "current_step": task_status.get("current_step", ""),
            "created_at": task_status.get("created_at", ""),
            "updated_at": task_status.get("updated_at", ""),
            "points_consumed": task_status.get("points_consumed", 0),
            "points_estimated": task_status.get("config", {}).get("estimated_points", 400),
            "points_total": task_status.get("points_total", 400)
        }
        
        # 添加详细的步骤状态（如果存在）
        if "step_status" in task_status:
            data["step_status"] = task_status["step_status"]
        
        # 如果任务完成，包含结果
        if task_status.get("status") == "completed" and "result" in task_status:
            data["result"] = task_status["result"]
        
        # 如果任务失败，包含错误信息
        if task_status.get("status") == "failed" and "error" in task_status:
            data["error"] = task_status["error"]
        
        return jsonify({
            "success": True,
            "data": data
        })
        
    except Exception as e:
        logger.error(f"❌ [PHASE_ONE] 获取任务状态失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@phase_api.route('/phase-one/products/<title>', methods=['GET'])
@login_required
def get_phase_one_products(title):
    """获取第一阶段的所有产物"""
    try:
        # 🔥 防御性检查：验证项目标题
        if not title or title == 'undefined' or not title.strip():
            logger.error(f"[PRODUCTS_DEBUG] ❌ 无效的项目标题: '{title}'")
            return jsonify({
                "success": False,
                "error": "项目标题无效",
                "hint": "请从正常入口访问，不要直接在URL中输入undefined"
            }), 400
        
        logger.info(f"[PRODUCTS_DEBUG] 📋 开始加载项目产物: {title}")
        
        loader = ProductLoader(title, logger)
        products = loader.load_all_products()
        
        completed = sum(1 for p in products.values() if p['complete'])
        total = len(products)
        
        # 🔥 新增：详细列出每个产物的状态
        product_status_list = []
        for category, product in products.items():
            status = "✅ 已完成" if product['complete'] else "❌ 未生成"
            product_status_list.append(f"{category}: {status}")
        
        logger.info(f"[PRODUCTS_DEBUG] 📊 产物加载完成: {completed}/{total} 个产物已加载")
        logger.info(f"[PRODUCTS_DEBUG] 📋 产物详情:\n  " + "\n  ".join(product_status_list))
        
        if completed == 0:
            logger.error(f"[PRODUCTS_DEBUG] ❌ 未找到任何产物文件")
            logger.info(f"[PRODUCTS_DEBUG] 📁 检查的目录:")
            logger.info(f"  - 标准项目目录: {loader.project_dir}")
            logger.info(f"  - 旧第一阶段目录: {loader.legacy_phase_one_dir}")
            return jsonify({
                "success": False,
                "error": "第一阶段产物不存在",
                "checked_paths": [
                    str(loader.project_dir),
                    str(loader.legacy_phase_one_dir)
                ]
            }), 404
        
        return jsonify({
            "success": True,
            "products": products,
            "summary": {
                "total": total,
                "completed": completed,
                "rate": f"{completed/total*100:.1f}%"
            }
        })
        
    except Exception as e:
        logger.error(f"获取第一阶段产物失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@phase_api.route('/phase-one/products/<title>/<category>', methods=['PUT'])
@login_required
def update_phase_one_product(title, category):
    """更新第一阶段的单个产物"""
    try:
        # 🔥 防御性检查：验证项目标题
        if not title or title == 'undefined' or not title.strip():
            logger.error(f"[PRODUCT_UPDATE_DEBUG] ❌ 无效的项目标题: '{title}'")
            return jsonify({
                "success": False,
                "error": "项目标题无效",
                "hint": "请从正常入口访问，不要直接在URL中输入undefined"
            }), 400
        
        data = request.json or {}
        product_title = data.get('title', '')
        product_content = data.get('content', '')
        
        if not product_title or not product_content:
            return jsonify({"success": False, "error": "标题和内容不能为空"}), 400
        
        loader = ProductLoader(title, logger)
        
        save_paths = {
            'worldview': loader.project_dir / "worldview" / f"{loader.original_title}_世界观.json",
            'characters': loader.project_dir / "characters" / f"{loader.original_title}_角色设计.json",
            'writing': loader.project_dir / "planning" / f"{loader.original_title}_写作计划.json",
            'storyline': loader.project_dir / "planning" / f"{loader.original_title}_故事线.json",
            'market': loader.project_dir / "market_analysis" / "市场分析.json",
            'growth': loader.project_dir / "planning" / f"{loader.original_title}_成长路线.json"
        }
        
        if category not in save_paths:
            return jsonify({"success": False, "error": f"未知的产物类别: {category}"}), 400
        
        file_path = save_paths[category]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'title': product_title,
                'content': product_content,
                'updated_at': datetime.now().isoformat(),
                'category': category
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"第一阶段产物已更新: {title} - {category}")
        
        return jsonify({
            "success": True,
            "message": f"{product_title} 已更新",
            "file_path": str(file_path)
        })
        
    except Exception as e:
        logger.error(f"更新第一阶段产物失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@phase_api.route('/phase-one/continue-to-phase-two/<title>', methods=['POST'])
@login_required
def continue_to_phase_two(title):
    """从第一阶段继续到第二阶段"""
    try:
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        logger.info(f"🔄 [PHASE_TRANSITION] 准备从第一阶段跳转到第二阶段: {title}")
        
        # 验证项目存在且第一阶段已完成
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "项目不存在"}), 404
        
        # 检查第一阶段产物
        quality_data = novel_detail.get("quality_data", {})
        has_phase_one_products = bool(quality_data) or bool(novel_detail.get("core_worldview"))
        
        if not has_phase_one_products:
            return jsonify({
                "success": False,
                "error": "第一阶段尚未完成，请先完成设定生成"
            }), 400
        
        logger.info(f"✅ [PHASE_TRANSITION] 第一阶段验证通过，准备跳转到第二阶段")
        
        return jsonify({
            "success": True,
            "message": "可以继续第二阶段生成",
            "project_title": title
        })
        
    except Exception as e:
        logger.error(f"❌ [PHASE_TRANSITION] 跳转失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== 路由注册函数 ====================

def register_phase_routes(app, manager_instance=None):
    """注册两阶段生成API路由"""
    app.register_blueprint(phase_api, url_prefix='/api')
    
    if manager_instance:
        global manager
        manager = manager_instance
    
    # 注册额外的路由
    register_additional_routes(app)
    
    logger.debug("=" * 60)
    logger.debug("📋 已注册的两阶段生成API路由:")
    for rule in app.url_map.iter_rules():
        if 'phase' in rule.rule or 'projects/with-phase-status' in rule.rule or 'storyline' in rule.rule:
            logger.debug(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.debug("=" * 60)
    
    logger.debug("两阶段生成API路由注册完成")


def register_additional_routes(app):
    """注册额外的路由（与项目管理相关）"""
    
    @app.route('/api/projects/with-phase-status', methods=['GET'])
    def get_projectsWithPhaseStatus():
        """获取所有项目及其两阶段状态"""
        try:
            if not manager:
                return jsonify({"success": False, "error": "Manager not initialized"}), 500
            
            # 获取所有小说项目
            all_projects = manager.get_novel_projects()
            
            # 🔥 改进：使用与前端相同的ProductLoader来检查产物
            from pathlib import Path
            
            # 为每个项目添加阶段状态信息
            projects_with_status = []
            for project in all_projects:
                project_title = project.get('title', project.get('novel_title', ''))
                if not project_title:
                    continue
                
                # 🔥 改进：使用ProductLoader直接检查产物，与前端逻辑完全一致
                # 这样可以确保前后端判断逻辑一致
                loader = ProductLoader(project_title, logger)
                products = loader.load_all_products()
                
                # 统计已完成的产物数量
                completed_count = sum(1 for p in products.values() if p['complete'])
                total_count = len(products)
                
                logger.info(f"📊 项目 {project_title}: ProductLoader检测到 {completed_count}/{total_count} 个产物已完成")
                
                # 详细日志：显示每个产物的状态
                for category, product in products.items():
                    status = "✅" if product['complete'] else "❌"
                    logger.info(f"  {status} {category}")
                
                # 🔥 新的判断标准：使用与前端完全一致的标准
                # 必须完成所有7个产物（世界观、势力、角色、成长、写作、故事线、市场分析）
                required_categories = ['worldview', 'factions', 'characters', 'growth', 'writing', 'storyline', 'market']
                completed_required = 7  # 必须完成所有7个产物
                
                # 计算关键产物的完成数量
                key_products_count = 0
                for category in required_categories:
                    if products.get(category, {}).get('complete', False):
                        key_products_count += 1
                
                has_phase_one_products = key_products_count >= completed_required
                
                # 🔥 修复：确保 phase_one_status 和 phase_one_completed_at 总是被赋值
                phase_one_status = 'not_started'
                phase_one_completed_at = None
                
                if has_phase_one_products:
                    phase_one_status = 'completed'
                    phase_one_completed_at = project.get('created_at', project.get('last_updated'))
                    logger.info(f"✅ 项目 {project_title} 第一阶段判定为完成")
                else:
                    logger.info(f"⚠️ 项目 {project_title} 第一阶段未完成，仅完成 {key_products_count}/{completed_required} 个产物")
                
                # 确定第二阶段状态
                phase_two_status = 'not_started'
                phase_two_completed_at = None
                # 🔥 修复：确保转换为整数
                try:
                    total_chapters = int(project.get('total_chapters', 0) or 0)
                except (ValueError, TypeError):
                    total_chapters = 0
                try:
                    completed_chapters = int(project.get('completed_chapters', 0) or 0)
                except (ValueError, TypeError):
                    completed_chapters = 0
                
                if completed_chapters > 0:
                    if completed_chapters >= total_chapters and total_chapters > 0:
                        phase_two_status = 'completed'
                        phase_two_completed_at = project.get('last_updated')
                    else:
                        phase_two_status = 'generating'
                
                # 确定整体项目状态
                overall_status = 'designing'
                if phase_one_status == 'completed' and phase_two_status == 'completed':
                    overall_status = 'completed'
                elif phase_one_status == 'completed' and phase_two_status in ['generating', 'completed']:
                    overall_status = 'phase_two_in_progress'
                elif phase_one_status == 'completed':
                    overall_status = 'phase_one_completed'
                
                project_with_status = {
                    **project,
                    'phase_one': {
                        'status': phase_one_status,
                        'completed_at': phase_one_completed_at
                    },
                    'phase_two': {
                        'status': phase_two_status,
                        'completed_at': phase_two_completed_at
                    },
                    'status': overall_status,
                    'total_chapters': total_chapters if total_chapters and total_chapters > 0 else 50,  # 只有当total_chapters为0或None时才使用默认值50
                    'completed_chapters': completed_chapters
                }
                
                projects_with_status.append(project_with_status)
            
            logger.info(f"✅ 获取项目列表及阶段状态成功: {len(projects_with_status)} 个项目")
            
            return jsonify({
                "success": True,
                "projects": projects_with_status,
                "total": len(projects_with_status)
            })
            
        except Exception as e:
            logger.error(f"❌ 获取项目列表及阶段状态失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/project/<title>/with-phase-info', methods=['GET'])
    def get_projectWithPhaseInfo(title):
        """获取项目详情及阶段信息"""
        try:
            # 🔥 防御性检查：验证项目标题
            if not title or title == 'undefined' or not title.strip():
                logger.error(f"[PROJECT_INFO_DEBUG] ❌ 无效的项目标题: '{title}'")
                return jsonify({
                    "success": False,
                    "error": "项目标题无效",
                    "hint": "请从正常入口访问，不要直接在URL中输入undefined"
                }), 400
            
            if not manager:
                return jsonify({"success": False, "error": "Manager not initialized"}), 500
            
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                return jsonify({"success": False, "error": "项目不存在"}), 404
            
            # 🔥 修复：正确获取总章节数，优先级从高到低
            total_chapters = (
                novel_detail.get('current_progress', {}).get('total_chapters', 0) if
                novel_detail.get('current_progress', {}).get('total_chapters', 0) > 0 else
                novel_detail.get('total_chapters', 0) if
                novel_detail.get('total_chapters', 0) > 0 else
                novel_detail.get('progress', {}).get('total_chapters', 0) if
                novel_detail.get('progress', {}).get('total_chapters', 0) > 0 else
                novel_detail.get('novel_info', {}).get('total_chapters', 0) if
                novel_detail.get('novel_info', {}).get('total_chapters', 0) > 0 else
                200  # 默认值
            )
            
            completed_chapters = len(novel_detail.get('generated_chapters', {}))
            
            # 🔥 改进：使用与get_projectsWithPhaseStatus相同的详细检查逻辑
            # 使用ProductLoader来检查所有7个产物
            loader = ProductLoader(title, logger)
            products = loader.load_all_products()
            
            # 统计已完成的产物数量
            completed_count = sum(1 for p in products.values() if p['complete'])
            total_count = len(products)
            
            logger.info(f"📊 项目 {title}: ProductLoader检测到 {completed_count}/{total_count} 个产物已完成")
            
            # 详细日志：显示每个产物的状态
            for category, product in products.items():
                status = "✅" if product['complete'] else "❌"
                logger.info(f"  {status} {category}")
            
            # 🔥 新的判断标准：必须完成所有7个产物
            required_categories = ['worldview', 'factions', 'characters', 'growth', 'writing', 'storyline', 'market']
            completed_required = 7  # 必须完成所有7个产物
            
            # 计算关键产物的完成数量
            key_products_count = 0
            for category in required_categories:
                if products.get(category, {}).get('complete', False):
                    key_products_count += 1
            
            has_phase_one = key_products_count >= completed_required
            
            logger.info(f"📊 项目 {title}: 关键产物计数={key_products_count}/{completed_required}, 一阶段完成={has_phase_one}")
            
            phase_info = {
                'phase_one': {
                    'status': 'completed' if has_phase_one else 'not_started',
                    'completed_at': novel_detail.get('created_at')
                },
                'phase_two': {
                    'status': 'completed' if completed_chapters >= total_chapters else ('generating' if completed_chapters > 0 else 'not_started'),
                    'completed_at': novel_detail.get('last_updated') if completed_chapters >= total_chapters else None
                },
                'total_chapters': total_chapters,
                'completed_chapters': completed_chapters,
                'generated_chapters': novel_detail.get('generated_chapters', {})
            }
            
            # 合并信息
            result = {
                **novel_detail,
                **phase_info
            }
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"❌ 获取项目详情失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/novel-project/<title>', methods=['DELETE'])
    def delete_novel_project(title):
        """删除小说项目
        
        通过标题删除小说项目及其所有相关数据
        """
        try:
            from urllib.parse import unquote
            title = unquote(title)
            
            logger.info(f"🗑️ 请求删除小说项目: {title}")
            
            if not manager:
                return jsonify({"success": False, "error": "Manager not initialized"}), 500
            
            # 检查项目是否存在
            if title not in manager.novel_projects:
                logger.warning(f"⚠️ 项目不存在: {title}")
                return jsonify({"success": False, "error": "项目不存在"}), 404
            
            # 从内存中删除项目
            del manager.novel_projects[title]
            
            # 注意：NovelGenerationManager 没有 _save_projects 方法
            # 项目数据是动态从文件系统加载的，删除目录后下次加载会自动更新
            
            # 删除项目目录
            import shutil
            from pathlib import Path
            from web.utils.path_utils import get_novel_project_dir, get_current_username
            
            # 获取当前用户名（用于构建正确的用户隔离路径）
            username = get_current_username()
            
            # 小说项目目录
            novel_project_dir = get_novel_project_dir(title, username, create=False)
            if novel_project_dir and novel_project_dir.exists():
                shutil.rmtree(novel_project_dir)
                logger.info(f"✅ 已删除小说项目目录: {novel_project_dir}")
            
            # 如果存在视频项目目录，也一并删除
            video_project_dir = VIDEO_PROJECTS_DIR / title
            if video_project_dir.exists():
                shutil.rmtree(video_project_dir)
                logger.info(f"✅ 已删除视频项目目录: {video_project_dir}")
            
            logger.info(f"✅ 成功删除小说项目: {title}")
            return jsonify({
                "success": True,
                "message": f"项目 '{title}' 已删除"
            })
            
        except Exception as e:
            logger.error(f"❌ 删除小说项目失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/templates/components/<component_name>', methods=['GET'])
    def get_template_component(component_name):
        """提供模板组件文件（用于前端动态加载）"""
        try:
            from flask import Response
            
            # 安全检查：只允许.html文件
            if not component_name.endswith('.html'):
                return jsonify({"error": "Only HTML files are allowed"}), 400
            
            # 构建组件文件路径
            components_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'components')
            component_path = os.path.join(components_dir, component_name)
            
            # 检查文件是否存在
            if not os.path.exists(component_path):
                logger.info(f"⚠️ 组件文件不存在: {component_path}")
                return jsonify({"error": "Component not found"}), 404
            
            # 读取并返回组件内容
            with open(component_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"✅ 提供组件文件: {component_name}")
            
            # 返回HTML内容
            return Response(content, mimetype='text/html')
            
        except Exception as e:
            logger.error(f"❌ 提供组件文件失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/storyline/<title>', methods=['GET'])
    @login_required
    def get_storyline(title):
        """获取项目的故事线数据（集成期待感管理）"""
        try:
            if not manager:
                return jsonify({"success": False, "error": "Manager not initialized"}), 500
            
            logger.info(f"[STORYLINE] 获取故事线数据: {title}")
            
            # 获取项目详情
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                return jsonify({"success": False, "error": "项目不存在"}), 404
            
            storyline_data = None
            expectation_map = None
            
            logger.info(f"[STORYLINE_DEBUG] 开始提取故事线数据")
            
            # ========== 第一步：尝试从产物文件加载storyline产物 ==========
            loader = ProductLoader(title, logger)
            products = loader.load_all_products()
            
            # 优先使用storyline产物（已包含完整的storyline数据）
            if products['storyline']['complete']:
                try:
                    storyline_content = json.loads(products['storyline']['content'])
                    logger.info(f"[STORYLINE_DEBUG] 从storyline产物解析数据，类型: {type(storyline_content)}")
                    
                    # 检查是否包含 stage_info（多阶段数据）
                    if 'stage_info' in storyline_content and 'major_events' in storyline_content:
                        storyline_data = storyline_content
                        logger.info(f"[STORYLINE] 使用storyline产物数据: {len(storyline_content.get('stage_info', []))} 个阶段, {len(storyline_content.get('major_events', []))} 个重大事件")
                        # 🔥 新增：打印所有阶段名称
                        stage_names = [s.get('stage_name', 'unknown') for s in storyline_content.get('stage_info', [])]
                        logger.info(f"[STORYLINE] 包含的阶段: {stage_names}")
                        
                        # 🔥 修复：提取期待感映射
                        if 'expectation_maps' in storyline_content:
                            expectation_map = storyline_content['expectation_maps']
                            total_expectations = sum(len(em.get('expectations', {})) for em in expectation_map.values())
                            logger.info(f"[EXPECTATION_MAP] 使用已有的期待感映射: {len(expectation_map)} 个阶段, 共 {total_expectations} 个期待")
                    else:
                        storyline_data = storyline_content
                        logger.info(f"[STORYLINE] 使用storyline产物数据（单阶段或其他格式）")
                except Exception as e:
                    logger.error(f"[STORYLINE] 解析storyline产物失败: {e}")
            
            # 如果storyline产物没有，尝试从写作计划产物中提取
            if not storyline_data and products['writing']['complete']:
                try:
                    writing_content = json.loads(products['writing']['content'])
                    logger.info(f"[STORYLINE_DEBUG] 从写作计划产物解析数据")
                    
                    # 检查是否是多阶段数据结构
                    if 'stages' in writing_content and 'stage_names' in writing_content:
                        logger.info(f"[STORYLINE] 检测到多阶段写作计划，开始提取重大事件")
                        all_major_events = []
                        stage_info = []
                        
                        # 按照标准阶段顺序排序
                        sorted_stage_names = get_sorted_stages(writing_content['stage_names'])
                        logger.info(f"[STORYLINE] 阶段顺序: {sorted_stage_names}")
                        
                        for stage_name in sorted_stage_names:
                            if stage_name in writing_content['stages']:
                                stage_data = writing_content['stages'][stage_name]
                                stage_plan = stage_data.get('stage_writing_plan', {})
                                
                                major_events = stage_plan.get('event_system', {}).get('major_events', [])
                                logger.info(f"[STORYLINE] 阶段 {stage_name} 的重大事件数量: {len(major_events)}")
                                
                                if major_events:
                                    # 为每个事件添加阶段信息和中级事件
                                    for event in major_events:
                                        event['_stage'] = stage_name
                                        event['_chapter_range'] = stage_plan.get('chapter_range', '')
                                        # 确保 composition 中的中级事件也添加到事件对象中
                                        if 'composition' in event:
                                            for phase_name, phase_events in event['composition'].items():
                                                if isinstance(phase_events, list):
                                                    if '_medium_events' not in event:
                                                        event['_medium_events'] = []
                                                    for me in phase_events:
                                                        me_copy = dict(me)
                                                        me_copy['phase'] = phase_name
                                                        me_copy['_phase_name'] = phase_name
                                                        if 'chapter_range' in me_copy:
                                                            me_copy['_chapter_range_normalized'] = normalize_chapter_range(me_copy['chapter_range'])
                                                        event['_medium_events'].append(me_copy)
                                
                                all_major_events.extend(major_events)
                                
                                stage_info.append({
                                    'stage_name': stage_name,
                                    'chapter_range': stage_plan.get('chapter_range', ''),
                                    'major_event_count': len(major_events)
                                })
                        
                        if all_major_events:
                            storyline_data = {
                                'stage_info': stage_info,
                                'total_major_events': len(all_major_events),
                                'major_events': all_major_events,
                                'stage_name': '全书',
                                'chapter_range': '1-200'
                            }
                            logger.info(f"[STORYLINE] 从写作计划产物提取到故事线: {len(stage_info)} 个阶段, {len(all_major_events)} 个重大事件")
                        else:
                            logger.error(f"[STORYLINE] 写作计划产物存在但没有 stages 或 stage_names 字段")
                    else:
                        logger.error(f"[STORYLINE] 写作计划产物数据结构不符合预期")
                except Exception as e:
                    logger.error(f"[STORYLINE] 解析写作计划产物失败: {e}")
                
                # ========== 新增：如果没有期待感映射且有故事线，则自动生成 ==========
                if storyline_data and storyline_data.get('major_events') and not expectation_map:
                    logger.info(f"[STORYLINE] 未找到期待感映射，开始自动生成...")
                    
                    # 导入期待感管理器
                    try:
                        from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator
                        expectation_manager = ExpectationManager()
                        expectation_integrator = ExpectationIntegrator(expectation_manager)
                        
                        major_events = storyline_data.get('major_events', [])
                        total_tagged = 0
                        
                        # 为每个重大事件添加期待感标签
                        for event in major_events:
                            # 🔥 修复：优先使用事件的id字段，如果没有id才使用name
                            # 确保与PhaseGenerator中的逻辑一致（event.get("id", f"event_{event_name}")）
                            event_id = event.get('id') or f"event_{event.get('name', '未命名事件')}"
                            event_name = event.get('name', '未命名事件')
                            
                            # 自动选择期待类型
                            exp_type = select_expectation_type(event)
                            
                            # 计算种植和目标章节
                            chapter_range = event.get('chapter_range', '1-10')
                            try:
                                from src.managers.StagePlanUtils import parse_chapter_range
                                start_ch, end_ch = parse_chapter_range(chapter_range)
                                target_ch = max(start_ch + 3, end_ch)  # 目标章节至少3章后
                            except:
                                target_ch = end_ch
                            
                            # 种植期待
                            exp_id = expectation_manager.tag_event_with_expectation(
                                event_id=event_id,  # 🔥 修复：使用event_id而不是event_name
                                expectation_type=exp_type,
                                planting_chapter=start_ch,
                                description=f"{event_name}: {event.get('main_goal', '')[:80]}...",
                                target_chapter=target_ch
                            )
                            
                            total_tagged += 1
                        
                        # 生成期待感映射
                        expectation_map = expectation_manager.export_expectation_map()
                        
                        logger.info(f"[STORYLINE] 成功为 {total_tagged} 个事件生成期待感标签")
                        
                    except Exception as e:
                        logger.info(f"[STORYLINE] 生成期待感标签失败: {e}")
            
            # 如果没有从 quality_data 找到，尝试从产物文件加载
            if not storyline_data:
                loader = ProductLoader(title, logger)
                products = loader.load_all_products()
                
                # 优先从storyline产物中提取（已经包含了所有阶段）
                if products['storyline']['complete']:
                    try:
                        storyline_content = json.loads(products['storyline']['content'])
                        # 检查是否包含 stage_info（多阶段数据）
                        if 'stage_info' in storyline_content and 'major_events' in storyline_content:
                            storyline_data = storyline_content
                            logger.info(f"[STORYLINE] 从storyline产物提取到故事线: {len(storyline_content.get('stage_info', []))} 个阶段, {len(storyline_content.get('major_events', []))} 个重大事件")
                        else:
                            storyline_data = storyline_content
                            logger.info(f"[STORYLINE] 从storyline产物提取到故事线")
                    except Exception as e:
                        logger.error(f"[STORYLINE] 从storyline产物提取失败: {e}")
                
                # 如果storyline产物没有，尝试从写作计划产物中提取
                if not storyline_data and products['writing']['complete']:
                    try:
                        writing_content = json.loads(products['writing']['content'])
                    except Exception as e:
                        logger.error(f"[STORYLINE] 解析写作计划内容失败: {e}")
                    else:
                        
                        # 检查是否是新格式的多阶段写作计划（包含 stages 和 stage_names）
                        if 'stages' in writing_content and 'stage_names' in writing_content:
                            all_major_events = []
                            stage_info = []
                            
                            # 按照标准阶段顺序排序
                            sorted_stage_names = get_sorted_stages(writing_content['stage_names'])
                            
                            for stage_name in sorted_stage_names:
                                if stage_name in writing_content['stages']:
                                    stage_data = writing_content['stages'][stage_name]
                                    stage_plan = stage_data.get('stage_writing_plan', {})
                                    
                                    major_events = stage_plan.get('event_system', {}).get('major_events', [])
                                    # 🔥 修复：也提取特殊情感事件
                                    special_emotional_events = stage_plan.get('event_system', {}).get('special_emotional_events', [])
                                    
                                    if major_events:
                                        # 为每个事件添加阶段信息
                                        for event in major_events:
                                            event['_stage'] = stage_name
                                            event['_chapter_range'] = stage_plan.get('chapter_range', '')
                                            # 确保 composition 中的中级事件也添加到事件对象中
                                            # 保留所有原始字段，包括 special_events
                                            if 'composition' in event:
                                                for phase_name, phase_events in event['composition'].items():
                                                    if isinstance(phase_events, list):
                                                        if '_medium_events' not in event:
                                                            event['_medium_events'] = []
                                                        # 保留完整的原始数据，只添加 phase 标记
                                                        for me in phase_events:
                                                            # 创建副本以避免修改原始数据
                                                            me_copy = dict(me)
                                                            me_copy['phase'] = phase_name
                                                            me_copy['_phase_name'] = phase_name  # 用于前端显示
                                                            # 标准化章节范围格式
                                                            if 'chapter_range' in me_copy:
                                                                me_copy['_chapter_range_normalized'] = normalize_chapter_range(me_copy['chapter_range'])
                                                            event['_medium_events'].append(me_copy)
                                            
                                            # 🔥 修复：为每个重大事件添加特殊情感事件
                                            if special_emotional_events and 'special_emotional_events' not in event:
                                                event['special_emotional_events'] = special_emotional_events
                                                
                                        all_major_events.extend(major_events)
                                        
                                        stage_info.append({
                                            'stage_name': stage_name,
                                            'chapter_range': stage_plan.get('chapter_range', ''),
                                            'major_event_count': len(major_events)
                                        })
                            
                            if all_major_events:
                                storyline_data = {
                                    'stage_info': stage_info,
                                    'total_major_events': len(all_major_events),
                                    'major_events': all_major_events,
                                    'stage_name': '全书',
                                    'chapter_range': '1-200'
                                }
                                logger.info(f"[STORYLINE] 从产物文件提取到故事线: {len(stage_info)} 个阶段, {len(all_major_events)} 个重大事件")
                        else:
                            # 检查是否是旧格式的多阶段写作计划（直接包含 opening_stage 等键）
                            all_major_events = []
                            all_stage_info = []
                            
                            for stage_key in STAGE_ORDER:
                                if stage_key in writing_content:
                                    stage_plan = writing_content[stage_key].get('stage_writing_plan', {})
                                    events = stage_plan.get('event_system', {}).get('major_events', [])
                                    if events:
                                        # 为每个事件添加阶段信息
                                        for event in events:
                                            event['_stage'] = stage_key
                                            event['_chapter_range'] = stage_plan.get('chapter_range', '')
                                        all_major_events.extend(events)
                                        
                                        all_stage_info.append({
                                            'stage_name': stage_key,
                                            'chapter_range': stage_plan.get('chapter_range', ''),
                                            'major_event_count': len(events)
                                        })
                            
                            if all_major_events:
                                storyline_data = {
                                    'stage_info': all_stage_info,
                                    'total_major_events': len(all_major_events),
                                    'major_events': all_major_events,
                                    'stage_name': '全书',
                                    'chapter_range': '1-200'
                                }
                                logger.info(f"[STORYLINE] 从产物文件提取到故事线: {len(all_stage_info)} 个阶段, {len(all_major_events)} 个重大事件")
                            else:
                                # 如果多阶段没找到，尝试直接提取
                                major_events = (
                                    writing_content.get('stage_writing_plan', {}).get('event_system', {}).get('major_events', []) or
                                    writing_content.get('major_events', [])
                                )
                                
                                if major_events:
                                    storyline_data = {
                                        'stage_name': '全书',
                                        'chapter_range': writing_content.get('chapter_range', ''),
                                        'major_events': major_events
                                    }
                                    logger.info(f"[STORYLINE] 从产物文件提取到故事线: 全书, {len(major_events)} 个重大事件")
            
            # ========== 统一的期待感映射处理逻辑 ==========
            # 🔥 修复：优先使用已有的期待感映射
            if storyline_data and not expectation_map:
                # 检查storyline_data中是否已经包含expectation_maps
                if 'expectation_maps' in storyline_data and storyline_data['expectation_maps']:
                    expectation_map = storyline_data['expectation_maps']
                    total_expectations = sum(len(em.get('expectations', {})) for em in expectation_map.values())
                    logger.info(f"[EXPECTATION_MAP] 使用故事线中已有的期待感映射: {len(expectation_map)} 个阶段, 共 {total_expectations} 个期待")
                elif storyline_data.get('major_events'):
                    # 只有在完全没有期待感映射时才生成
                    logger.info(f"[STORYLINE] 故事线数据已加载，但未找到期待感映射，开始自动生成...")
                    
                    try:
                        from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator
                        expectation_manager = ExpectationManager()
                        expectation_integrator = ExpectationIntegrator(expectation_manager)
                        
                        major_events = storyline_data.get('major_events', [])
                        total_tagged = 0
                        
                        # 为每个重大事件添加期待感标签
                        for event in major_events:
                            # 🔥 修复：优先使用事件的id字段，确保与PhaseGenerator中的逻辑一致
                            event_id = event.get('id') or f"event_{event.get('name', '未命名事件')}"
                            event_name = event.get('name', '未命名事件')
                            exp_type = select_expectation_type(event)
                            
                            chapter_range = event.get('chapter_range', '1-10')
                            try:
                                from src.managers.StagePlanUtils import parse_chapter_range
                                start_ch, end_ch = parse_chapter_range(chapter_range)
                                target_ch = max(start_ch + 3, end_ch)
                            except:
                                target_ch = end_ch
                            
                            exp_id = expectation_manager.tag_event_with_expectation(
                                event_id=event_id,  # 🔥 修复：使用event_id而不是event_name
                                expectation_type=exp_type,
                                planting_chapter=start_ch,
                                description=f"{event_name}: {event.get('main_goal', '')[:80]}...",
                                target_chapter=target_ch
                            )
                            
                            total_tagged += 1
                        
                        # 生成期待感映射
                        expectation_map = expectation_manager.export_expectation_map()
                        logger.info(f"[STORYLINE] 成功为 {total_tagged} 个事件生成期待感标签")
                        
                    except Exception as e:
                        logger.info(f"[STORYLINE] 生成期待感标签失败: {e}")
            
            # ========== 最后：将期待感映射添加到故事线数据中 ==========
            if storyline_data and expectation_map:
                storyline_data['expectation_maps'] = expectation_map  # 🔥 修复：使用复数形式 expectation_maps
                
                # 🔥 新增：详细的调试日志
                if isinstance(expectation_map, dict):
                    if 'expectations' in expectation_map:
                        total_count = len(expectation_map.get('expectations', {}))
                        logger.info(f"[STORYLINE] 已添加期待感映射到故事线数据 (单阶段格式, 共 {total_count} 个期待)")
                    elif 'expectation_maps' in expectation_map or isinstance(list(expectation_map.values())[0] if expectation_map else {}, dict):
                        # 多阶段格式
                        total_stages = len(expectation_map)
                        total_exp = sum(len(em.get('expectations', {})) for em in expectation_map.values())
                        logger.info(f"[STORYLINE] 已添加期待感映射到故事线数据 (多阶段格式, {total_stages} 个阶段, 共 {total_exp} 个期待)")
                
                logger.info(f"[STORYLINE_DEBUG] expectation_map结构: {list(expectation_map.keys()) if isinstance(expectation_map, dict) else type(expectation_map)}")
            elif storyline_data and not expectation_map:
                logger.info(f"[STORYLINE] ⚠️ 故事线数据存在但没有期待感映射，前端将不会显示期待感标签")
                logger.info(f"[STORYLINE_DEBUG] storyline_data键: {list(storyline_data.keys())}")
            
            if not storyline_data:
                return jsonify({
                    "success": False,
                    "error": "未找到故事线数据",
                    "hint": "请先完成第一阶段设定生成，确保包含故事线/事件系统数据"
                }), 404
            
            return jsonify({
                "success": True,
                "storyline": storyline_data,
                "project_title": title
            })
            
        except Exception as e:
            logger.error(f"[STORYLINE] 获取故事线失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/platforms/supported', methods=['GET'])
    def get_supported_platforms():
        """获取支持的平台列表"""
        try:
            from config.platform_adapters import PlatformAdapterFactory
            
            platforms = PlatformAdapterFactory.get_supported_platforms()
            
            return jsonify({
                "success": True,
                "platforms": platforms
            })
            
        except Exception as e:
            logger.error(f"❌ 获取平台列表失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/factions/<title>', methods=['GET'])
    @login_required
    def get_faction_system(title):
        """获取项目的势力系统数据"""
        try:
            # 🔥 防御性检查：验证项目标题
            if not title or title == 'undefined' or not title.strip():
                logger.error(f"[FACTIONS_DEBUG] ❌ 无效的项目标题: '{title}'")
                return jsonify({
                    "success": False,
                    "error": "项目标题无效",
                    "hint": "请从正常入口访问，不要直接在URL中输入undefined"
                }), 400
            
            logger.info(f"[FACTIONS] 获取势力系统数据: {title}")
            
            loader = ProductLoader(title, logger)
            # 使用内部加载方法
            products = loader.load_all_products()
            faction_data = None
            if products['factions']['complete']:
                try:
                    faction_data = json.loads(products['factions']['content'])
                except:
                    faction_data = None
            
            if not faction_data:
                return jsonify({
                    "success": False,
                    "error": "势力系统数据不存在",
                    "hint": "请先完成第一阶段设定生成"
                }), 404
            
            return jsonify({
                "success": True,
                "faction_system": faction_data,
                "project_title": title
            })
            
        except Exception as e:
            logger.error(f"[FACTIONS] 获取势力系统失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/storyline/<title>/update', methods=['POST'])
    @login_required
    def update_storyline(title):
        """更新项目的故事线数据"""
        try:
            data = request.json or {}
            storyline = data.get('storyline')
            
            if not storyline:
                return jsonify({"success": False, "error": "故事线数据不能为空"}), 400
            
            if not manager:
                return jsonify({"success": False, "error": "Manager not initialized"}), 500
            
            logger.info(f"[STORYLINE] 更新故事线数据: {title}")
            
            # 保存到产物文件
            loader = ProductLoader(title, logger)
            
            # 确定保存路径
            planning_dir = loader.project_dir / "planning"
            planning_dir.mkdir(parents=True, exist_ok=True)
            
            storyline_file = planning_dir / f"{loader.original_title}_故事线.json"
            
            # 读取现有的写作计划（如果存在）
            existing_plan = {}
            existing_plan_file = planning_dir / f"{loader.original_title}_写作计划.json"
            if existing_plan_file.exists():
                try:
                    with open(existing_plan_file, 'r', encoding='utf-8') as f:
                        existing_plan = json.load(f)
                except Exception as e:
                    logger.info(f"读取现有写作计划失败: {e}")
            
            # 更新故事线数据
            if 'stage_writing_plan' not in existing_plan:
                existing_plan['stage_writing_plan'] = {}
            if 'event_system' not in existing_plan['stage_writing_plan']:
                existing_plan['stage_writing_plan']['event_system'] = {}
            
            existing_plan['stage_writing_plan']['event_system']['major_events'] = storyline.get('major_events', [])
            existing_plan['stage_name'] = storyline.get('stage_name', existing_plan.get('stage_name', '全书'))
            existing_plan['chapter_range'] = storyline.get('chapter_range', existing_plan.get('chapter_range', ''))
            
            # 保存更新后的写作计划
            with open(existing_plan_file, 'w', encoding='utf-8') as f:
                json.dump(existing_plan, f, ensure_ascii=False, indent=2)
            
            # 同时保存单独的故事线文件
            with open(storyline_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'title': title,
                    'stage_name': storyline.get('stage_name', '全书'),
                    'chapter_range': storyline.get('chapter_range', ''),
                    'major_events': storyline.get('major_events', []),
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 故事线数据已保存: {storyline_file}")
            
            return jsonify({
                "success": True,
                "message": "故事线更新成功",
                "file_path": str(storyline_file)
            })
            
        except Exception as e:
            logger.error(f"[STORYLINE] 更新故事线失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    # ==================== 第二阶段生成API路由 ====================
    
    @app.route('/api/phase-two/start-generation', methods=['POST'])
    @login_required
    def start_phase_two_generation():
        """启动第二阶段章节生成任务（带点数扣除）"""
        try:
            data = request.json or {}
            
            # 提取参数
            novel_title = data.get('novel_title')
            from_chapter = data.get('from_chapter')
            chapters_to_generate = data.get('chapters_to_generate')
            chapters_per_batch = data.get('chapters_per_batch', 1)
            generation_notes = data.get('generation_notes', '')
            
            # 参数验证
            if not novel_title:
                return jsonify({"success": False, "error": "小说标题不能为空"}), 400
            
            if from_chapter is None or chapters_to_generate is None:
                return jsonify({"success": False, "error": "章节参数不完整"}), 400
            
            logger.info(f"🚀 [PHASE_TWO] 开始第二阶段生成: {novel_title}")
            logger.info(f"📋 [PHASE_TWO] 从第{from_chapter}章开始，生成{chapters_to_generate}章")
            
            if not manager:
                return jsonify({"success": False, "error": "管理器未初始化"}), 500
            
            # ===== 创造点扣除逻辑 =====
            from web.models.point_model import point_model
            
            # 计算消耗点数（批量模式：每章2点 = 生成1点 + 质量检查1点）
            cost_per_chapter = point_model.get_config('phase2_chapter_batch', 2)
            total_cost = chapters_to_generate * cost_per_chapter
            
            user_id = session.get('user_id')
            logger.info(f"💰 [PHASE_TWO] 需要消耗创造点: {total_cost} (每章{cost_per_chapter}点 × {chapters_to_generate}章)")
            
            # 检查余额
            user_points = point_model.get_user_points(user_id)
            if user_points['balance'] < total_cost:
                return jsonify({
                    "success": False, 
                    "error": f"创造点不足，需要{total_cost}点，当前余额{user_points['balance']}点",
                    "required": total_cost,
                    "balance": user_points['balance']
                }), 402  # Payment Required
            
            # 扣除点数
            spend_result = point_model.spend_points(
                user_id=user_id,
                amount=total_cost,
                source='phase2_generation',
                description=f'第二阶段生成{chapters_to_generate}章小说内容',
                related_id=f"{novel_title}_{from_chapter}"
            )
            
            if not spend_result['success']:
                logger.error(f"❌ [PHASE_TWO] 扣除创造点失败: {spend_result.get('error')}")
                return jsonify({
                    "success": False, 
                    "error": f"扣除创造点失败: {spend_result.get('error')}"
                }), 500
            
            logger.info(f"✅ [PHASE_TWO] 已扣除创造点: {total_cost}，剩余: {spend_result['balance']}")
            # ===== 创造点扣除结束 =====
            
            # 调用管理器启动第二阶段生成任务
            user_id = session.get('user_id')
            username = session.get('username')
            
            generation_config = {
                "novel_title": novel_title,
                "from_chapter": from_chapter,
                "chapters_to_generate": chapters_to_generate,
                "chapters_per_batch": chapters_per_batch,
                "generation_notes": generation_notes,
                "user_id": user_id,
                "username": username
            }
            
            try:
                task_id = manager.start_phase_two_generation(generation_config)
                
                logger.info(f"✅ [PHASE_TWO] 任务已启动: {task_id}")
                
                return jsonify({
                    "success": True,
                    "task_id": task_id,
                    "message": f"第二阶段生成任务已启动，已消耗{total_cost}创造点",
                    "status": "initializing",
                    "points_spent": total_cost,
                    "balance_after": spend_result['balance']
                })
            except AttributeError as e:
                # 如果管理器还没有实现该方法，回滚点数并返回错误
                logger.error(f"❌ [PHASE_TWO] 管理器方法调用失败: {e}")
                
                # 回滚点数
                rollback_result = point_model.rollback_transaction(
                    user_id=user_id,
                    related_id=f"{novel_title}_{from_chapter}"
                )
                if rollback_result['success']:
                    logger.info(f"✅ [PHASE_TWO] 已回滚创造点: {total_cost}")
                
                import traceback
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                return jsonify({
                    "success": False,
                    "error": "第二阶段生成功能尚未实现，已退还创造点"
                }), 501
            
        except Exception as e:
            logger.error(f"❌ [PHASE_TWO] 启动生成失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/phase-two/task/<task_id>/status', methods=['GET'])
    @login_required
    def get_phase_two_task_status(task_id):
        """获取第二阶段任务状态"""
        try:
            if not manager:
                return jsonify({"success": False, "error": "管理器未初始化"}), 500
            
            # 使用通用的 get_task_status 方法获取任务状态
            task_status = manager.get_task_status(task_id)
            
            if "error" in task_status:
                return jsonify({"success": False, "error": task_status["error"]}), 404
            
            # 从 task_progress 获取更详细的进度信息
            task_progress = manager.get_task_progress(task_id)
            
            # 返回任务状态
            response = {
                "success": True,
                "task_id": task_id,
                "status": task_status.get("status", "unknown"),
                "progress": task_status.get("progress", 0),
                "status_message": task_status.get("status", ""),
                "current_chapter": task_progress.get("current_chapter"),
                "chapter_progress": task_progress.get("chapter_progress", []),
                "total_chapters": task_progress.get("total_chapters", 0),
                "created_at": task_status.get("created_at", ""),
                "updated_at": task_status.get("updated_at", "")
            }
            
            # 如果任务完成，包含结果
            if task_status.get("status") == "completed" and "result" in task_status:
                response["result"] = task_status["result"]
                response["generated_chapters"] = task_status.get("result", {}).get("generated_chapters", [])
            
            # 如果任务失败，包含错误信息
            if task_status.get("status") == "failed" and "error" in task_status:
                response["error"] = task_status["error"]
            
            return jsonify(response)
            
        except Exception as e:
            logger.error(f"❌ [PHASE_TWO] 获取任务状态失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    # ==================== 停止生成和恢复生成API路由 ====================
    
    @app.route('/api/phase-one/task/<task_id>/stop', methods=['POST'])
    @login_required
    def stop_phase_one_generation(task_id):
        """停止第一阶段生成任务，返还剩余点数并保存检查点"""
        from flask import session
        try:
            user_id = session.get('user_id')
            logger.info(f"🛑 [STOP] 用户 {user_id} 请求停止任务: {task_id}")
            
            if not manager:
                return jsonify({"success": False, "error": "管理器未初始化"}), 500
            
            # 获取任务状态
            task_status = manager.get_task_status(task_id)
            if "error" in task_status:
                return jsonify({"success": False, "error": "任务不存在"}), 404
            
            # 检查任务是否还在运行
            if task_status.get("status") not in ["generating", "initializing"]:
                return jsonify({
                    "success": False, 
                    "error": f"任务当前状态为 {task_status.get('status')}，无法停止"
                }), 400
            
            # 获取任务配置
            config = task_status.get("config", {})
            title = config.get("title", "未命名")
            estimated_points = config.get("estimated_points", 0)
            
            # 获取实际消耗点数
            points_consumed = task_status.get("points_consumed", 0)
            points_to_refund = max(0, estimated_points - points_consumed)
            
            logger.info(f"💰 [STOP] 预估点数: {estimated_points}, 已消耗: {points_consumed}, 应返还: {points_to_refund}")
            
            # 返还剩余点数
            refund_result = None
            if points_to_refund > 0:
                from web.models.point_model import point_model
                refund_result = point_model.add_points(
                    user_id=user_id,
                    amount=points_to_refund,
                    source='generation_stop_refund',
                    description=f'停止生成任务返还: {title}',
                    related_id=task_id
                )
                if refund_result.get('success'):
                    logger.info(f"✅ [STOP] 已返还 {points_to_refund} 创造点给用户 {user_id}")
                else:
                    logger.error(f"❌ [STOP] 返还点数失败: {refund_result.get('error')}")
            
            # 更新检查点，记录停止状态
            checkpoint_info = None
            if manager.checkpoint_enabled:
                current_step = task_status.get("current_step", "unknown")
                manager._update_checkpoint(
                    title=title,
                    phase="phase_one",
                    step=current_step,
                    data={
                        "stopped_at": datetime.now().isoformat(),
                        "stopped_by": user_id,
                        "points_consumed": points_consumed,
                        "points_refunded": points_to_refund,
                        "progress": task_status.get("progress", 0)
                    },
                    step_status="stopped"
                )
                
                # 加载检查点信息用于返回
                from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
                from pathlib import Path
                checkpoint_mgr = GenerationCheckpoint(title, Path.cwd())
                checkpoint_info = checkpoint_mgr.get_resume_info()
                logger.info(f"✅ [STOP] 检查点已更新，当前步骤: {current_step}")
            
            # 🔥 设置停止标志，通知生成线程停止
            manager.stop_task(task_id)
            
            # 等待一段时间让生成线程检测到停止标志并退出
            import time
            time.sleep(1)
            
            # 标记任务为已停止
            manager._update_task_status(task_id, "stopped", task_status.get("progress", 0))
            
            return jsonify({
                "success": True,
                "message": "生成任务已停止",
                "task_id": task_id,
                "points_consumed": points_consumed,
                "points_refunded": points_to_refund,
                "refund_success": refund_result.get('success', True) if refund_result else True,
                "checkpoint_info": checkpoint_info
            })
            
        except Exception as e:
            logger.error(f"❌ [STOP] 停止生成任务失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/phase-one/resume', methods=['POST'])
    @login_required
    def resume_phase_one_generation():
        """从检查点恢复第一阶段生成"""
        try:
            data = request.json or {}
            novel_title = data.get('novel_title')
            user_id = session.get('user_id')
            
            if not novel_title:
                return jsonify({"success": False, "error": "小说标题不能为空"}), 400
            
            logger.info(f"🔄 [RESUME] 用户 {user_id} 请求恢复生成: {novel_title}")
            
            # 加载检查点
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
            checkpoint_mgr = GenerationCheckpoint(novel_title, Path.cwd())
            checkpoint = checkpoint_mgr.load_checkpoint()
            
            if not checkpoint:
                return jsonify({
                    "success": False, 
                    "error": "没有找到可恢复的检查点",
                    "hint": "请重新开始生成"
                }), 404
            
            # 检查检查点数据
            checkpoint_data = checkpoint.get('data', {})
            generation_params = checkpoint_data.get('generation_params', {})
            
            if not generation_params:
                return jsonify({
                    "success": False, 
                    "error": "检查点数据不完整",
                    "hint": "请重新开始生成"
                }), 400
            
            # 计算预估点数（重新生成剩余步骤）
            from web.models.point_model import point_model
            current_step = checkpoint.get('current_step', 'initialization')
            phase_steps = GenerationCheckpoint.PHASES.get('phase_one', {}).get('steps', [])
            
            # 计算剩余步骤数
            current_index = phase_steps.index(current_step) if current_step in phase_steps else 0
            remaining_steps = len(phase_steps) - current_index
            total_steps = len(phase_steps)
            
            # 预估剩余所需点数（简化计算）
            original_estimate = generation_params.get('estimated_points', 0)
            progress_percent = (current_index / total_steps) if total_steps > 0 else 0
            remaining_estimate = int(original_estimate * (1 - progress_percent))
            
            # 检查余额
            user_points = point_model.get_user_points(user_id)
            if user_points['balance'] < remaining_estimate:
                return jsonify({
                    "success": False, 
                    "error": f"创造点不足，恢复生成需要约{remaining_estimate}点，当前余额{user_points['balance']}点",
                    "required": remaining_estimate,
                    "balance": user_points['balance']
                }), 402
            
            # 扣除预估点数
            spend_result = point_model.spend_points(
                user_id=user_id,
                amount=remaining_estimate,
                source='phase1_resume',
                description=f'恢复生成第一阶段设定: {novel_title}',
                related_id=novel_title
            )
            
            if not spend_result['success']:
                return jsonify({
                    "success": False, 
                    "error": f"扣除创造点失败: {spend_result.get('error')}"
                }), 500
            
            # 添加恢复标记
            generation_params['is_resume_mode'] = True
            generation_params['user_id'] = user_id
            generation_params['estimated_points'] = remaining_estimate
            generation_params['checkpoint_step'] = current_step
            
            # 启动生成任务
            task_id = manager.start_generation(generation_params)
            
            logger.info(f"✅ [RESUME] 任务已恢复启动: {task_id}, 从步骤: {current_step}")
            
            return jsonify({
                "success": True,
                "task_id": task_id,
                "message": f"已从检查点恢复生成，当前步骤: {current_step}",
                "resumed_from_step": current_step,
                "progress": checkpoint_data.get('progress', 0),
                "estimated_points": remaining_estimate,
                "balance_after": spend_result['balance']
            })
            
        except Exception as e:
            logger.error(f"❌ [RESUME] 恢复生成失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    # ==================== 第二阶段内容审核API路由 ====================
    
    @app.route('/api/phase-two/content-review/<title>', methods=['GET'])
    @login_required
    def get_content_review_chapters(title):
        """获取项目的章节列表（用于内容审核）"""
        try:
            if not manager:
                return jsonify({"success": False, "error": "管理器未初始化"}), 500
            
            logger.info(f"[CONTENT_REVIEW] 获取章节列表: {title}")
            
            # 获取项目详情
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                return jsonify({"success": False, "error": "项目不存在"}), 404
            
            # 获取已生成的章节
            generated_chapters = novel_detail.get('generated_chapters', {})
            
            if not generated_chapters:
                return jsonify({
                    "success": True,
                    "chapters": [],
                    "message": "该项目尚未生成任何章节"
                })
            
            # 转换为前端需要的格式
            chapters_list = []
            for chapter_num_str, chapter_data in generated_chapters.items():
                try:
                    chapter_num = int(chapter_num_str)
                    chapters_list.append({
                        'chapter_number': chapter_num,
                        'title': chapter_data.get('title', f'第{chapter_num}章'),
                        'file_name': chapter_data.get('file_name', f'第{chapter_num}章.txt'),
                        'word_count': chapter_data.get('word_count', 0),
                        'generated_at': chapter_data.get('generated_at', '')
                    })
                except (ValueError, TypeError):
                    continue
            
            # 按章节号排序
            chapters_list.sort(key=lambda x: x['chapter_number'])
            
            logger.info(f"[CONTENT_REVIEW] 找到 {len(chapters_list)} 个章节")
            
            return jsonify({
                "success": True,
                "chapters": chapters_list
            })
            
        except Exception as e:
            logger.error(f"[CONTENT_REVIEW] 获取章节列表失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/phase-two/content-review/<title>/chapter/<int:chapter_num>/files', methods=['GET'])
    @login_required
    def get_chapter_raw_files(title, chapter_num):
        """获取指定章节的原始文件信息"""
        try:
            if not manager:
                return jsonify({"success": False, "error": "管理器未初始化"}), 500
            
            logger.info(f"[CONTENT_REVIEW] 获取章节文件: {title} - 第{chapter_num}章")
            
            # 🔥 关键修复：在获取章节详情前，先重新加载项目数据
            # 这样可以确保获取到最新的章节信息
            manager.load_existing_novels()
            logger.info(f"[CONTENT_REVIEW] 已重新加载项目数据")
            
            # 🔥 新增：重新加载后，打印调试信息
            novel_detail = manager.get_novel_detail(title)
            if novel_detail:
                generated_chapters = novel_detail.get('generated_chapters', {})
                logger.info(f"[CONTENT_REVIEW] 重新加载后章节数: {len(generated_chapters)}")
                logger.info(f"[CONTENT_REVIEW] 章节键列表: {list(generated_chapters.keys())[:10]}")
            
            # 获取项目详情
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                return jsonify({"success": False, "error": "项目不存在"}), 404
            
            # 获取指定章节数据
            generated_chapters = novel_detail.get('generated_chapters', {})
            
            logger.info(f"[CONTENT_REVIEW] generated_chapters键类型: {type(list(generated_chapters.keys()) if generated_chapters else 'None')}")
            logger.info(f"[CONTENT_REVIEW] generated_chapters键: {list(generated_chapters.keys())}")
            logger.info(f"[CONTENT_REVIEW] chapter_num类型: {type(chapter_num)}, 值: {chapter_num}")
            
            # 检查是否有任何生成的章节
            if not generated_chapters:
                return jsonify({
                    "success": False,
                    "error": "该项目尚未生成任何章节",
                    "hint": "请先在第二阶段生成生成章节内容"
                }), 404
            
            # 🔥 关键修复：generated_chapters的键可能是整数或字符串，需要处理两种情况
            # 尝试整数键
            if chapter_num in generated_chapters:
                chapter_key = chapter_num
            # 尝试字符串键
            elif str(chapter_num) in generated_chapters:
                chapter_key = str(chapter_num)
            else:
                logger.info(f"[CONTENT_REVIEW] 章节{chapter_num}不存在，可用章节: {list(generated_chapters.keys())}")
                return jsonify({
                    "success": False,
                    "error": f"第{chapter_num}章不存在",
                    "available_chapters": list(generated_chapters.keys()),
                    "hint": f"该项目只有 {len(generated_chapters)} 个章节"
                }), 404
            
            chapter_data = generated_chapters[chapter_key]
            
            # 构建文件信息
            raw_files = {
                'input_files': [],
                'output_files': [],
                'quality_files': [],
                'character_files': []
            }
            
            # 添加输出文件（章节内容）
            chapter_file_path = chapter_data.get('file_path', '')
            word_count = chapter_data.get('word_count', 0)  # 🔥 获取word_count
            
            logger.info(f"[CONTENT_REVIEW] 章节数据 - file_path: {chapter_file_path}, word_count: {word_count}")
            
            if chapter_file_path:
                try:
                    from pathlib import Path
                    file_path = Path(chapter_file_path)
                    if file_path.exists():
                        # 🔥 修复：如果word_count为0，尝试从文件重新计算
                        if word_count == 0:
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # 尝试解析JSON
                                    try:
                                        chapter_json = json.loads(content)
                                        word_count = len(chapter_json.get('content', ''))
                                    except:
                                        word_count = len(content)
                                logger.info(f"[CONTENT_REVIEW] 重新计算字数: {word_count}")
                            except Exception as e:
                                logger.error(f"[CONTENT_REVIEW] 重新计算字数失败: {e}")
                        
                        raw_files['output_files'].append({
                            'name': file_path.name,
                            'type': '章节内容',
                            'file_path': str(file_path),
                            'file_size': file_path.stat().st_size,
                            'extension': file_path.suffix,
                            'word_count': word_count  # 🔥 添加字数字段
                        })
                        logger.info(f"[CONTENT_REVIEW] 找到章节文件: {file_path.name}, 字数: {word_count}")
                except Exception as e:
                    logger.info(f"无法访问章节文件: {e}")
            
            # 如果没有找到文件，尝试从生成的目录中查找
            if not raw_files['output_files']:
                from pathlib import Path
                # 🔥 使用用户隔离路径
                try:
                    from web.utils.path_utils import get_user_novel_dir
                    base_dir = get_user_novel_dir(create=False)
                except Exception:
                    base_dir = Path("小说项目")
                project_dir = base_dir / title
                chapter_files = []
                
                # 搜索可能的章节文件位置
                search_paths = [
                    project_dir / "generated_chapters",
                    project_dir / "chapters",
                    project_dir / "output"
                ]
                
                for search_path in search_paths:
                    if search_path.exists():
                        # 查找包含章节号的文件
                        for file_path in search_path.glob(f"*{chapter_num}*"):
                            if file_path.is_file():
                                chapter_files.append(file_path)
                
                # 添加找到的文件
                for file_path in chapter_files:
                    raw_files['output_files'].append({
                        'name': file_path.name,
                        'type': '章节内容',
                        'file_path': str(file_path),
                        'file_size': file_path.stat().st_size,
                        'extension': file_path.suffix
                    })
                    logger.info(f"[CONTENT_REVIEW] 找到章节文件: {file_path.name}")
            
            # 添加输入文件（写作计划等）
            try:
                from web.utils.path_utils import get_user_novel_dir
                base_dir = get_user_novel_dir(create=False)
            except Exception:
                base_dir = Path("小说项目")
            planning_dir = base_dir / title / "planning"
            if planning_dir.exists():
                for file_path in planning_dir.glob("*写作计划*.json"):
                    raw_files['input_files'].append({
                        'name': file_path.name,
                        'type': '写作计划',
                        'file_path': str(file_path),
                        'file_size': file_path.stat().st_size,
                        'extension': file_path.suffix
                    })
            
            # 添加其他可能的质量评价文件
            quality_dir = base_dir / title / "quality_reports"
            if quality_dir.exists():
                for file_path in quality_dir.glob(f"*{chapter_num}*.json"):
                    raw_files['quality_files'].append({
                        'name': file_path.name,
                        'type': '质量评价',
                        'file_path': str(file_path),
                        'file_size': file_path.stat().st_size,
                        'extension': file_path.suffix
                    })
            
            # 🔥 修复：添加字数统计到日志
            total_words = sum(f.get('word_count', 0) for f in raw_files['output_files'])
            logger.info(f"[CONTENT_REVIEW] 返回文件信息: 输入{len(raw_files['input_files'])}, 输出{len(raw_files['output_files'])}, 质量{len(raw_files['quality_files'])}, 总字数: {total_words}")
            
            return jsonify({
                "success": True,
                "raw_files": raw_files
            })
            
        except Exception as e:
            logger.error(f"[CONTENT_REVIEW] 获取章节文件失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    # ==================== 文件内容读取API路由 ====================
    
    @app.route('/api/file-content', methods=['GET'])
    @login_required
    def get_file_content():
        """读取文件内容（用于章节内容显示）"""
        try:
            from pathlib import Path
            
            # 获取文件路径参数
            file_path = request.args.get('path', '')
            
            if not file_path:
                return jsonify({"success": False, "error": "文件路径参数缺失"}), 400
            
            logger.info(f"[FILE_CONTENT] 读取文件内容: {file_path}")
            
            # 安全检查：确保文件路径在允许的目录内
            # 只允许读取项目目录下的文件
            allowed_dirs = ['小说项目', 'quality_data']
            is_allowed = False
            
            file_path_obj = Path(file_path).resolve()
            
            for allowed_dir in allowed_dirs:
                allowed_path = Path(allowed_dir).resolve()
                try:
                    file_path_obj.relative_to(allowed_path)
                    is_allowed = True
                    break
                except ValueError:
                    continue
            
            if not is_allowed:
                logger.error(f"[FILE_CONTENT] 文件路径不在允许的目录内: {file_path}")
                return jsonify({"success": False, "error": "无权访问该文件"}), 403
            
            # 检查文件是否存在
            if not file_path_obj.exists():
                logger.error(f"[FILE_CONTENT] 文件不存在: {file_path}")
                return jsonify({"success": False, "error": f"文件不存在: {file_path}"}), 404
            
            # 读取文件内容
            try:
                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                logger.info(f"[FILE_CONTENT] 成功读取文件: {file_path}, 长度: {len(content)}")
                
                # 如果是JSON文件，尝试提取content字段
                if file_path_obj.suffix == '.json':
                    try:
                        json_data = json.loads(content)
                        # 如果有content字段，返回它
                        if 'content' in json_data:
                            content = json_data['content']
                            logger.info(f"[FILE_CONTENT] 从JSON中提取content字段，长度: {len(content)}")
                    except json.JSONDecodeError:
                        # 不是有效的JSON，使用原始内容
                        logger.info(f"[FILE_CONTENT] 文件不是有效JSON，使用原始内容")
                
                return jsonify({
                    "success": True,
                    "content": content,
                    "file_path": file_path,
                    "length": len(content)
                })
                
            except UnicodeDecodeError as e:
                logger.error(f"[FILE_CONTENT] 文件编码错误: {e}")
                return jsonify({"success": False, "error": f"文件编码错误: {str(e)}"}), 500
                
        except Exception as e:
            logger.error(f"[FILE_CONTENT] 读取文件内容失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500


    # ==================== 质量评估API路由 ====================

    @app.route('/api/quality-assessment/<path:novel_title>', methods=['GET'])
    @login_required
    def get_quality_assessment(novel_title):
        """获取小说的质量评估报告"""
        try:
            from pathlib import Path
            import re

            # URL解码
            novel_title = re.sub(r'_|\+', ' ', novel_title)

            logger.info(f"[QUALITY_ASSESSMENT] 获取质量评估: {novel_title}")

            # 构建评估报告路径
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            report_path = Path(f"小说项目/{safe_title}/plans/{safe_title}_opening_stage_writing_plan_quality_report.json")

            if not report_path.exists():
                # 尝试从materials目录查找
                alt_report_path = Path(f"小说项目/{safe_title}/materials/phase_one_products/{safe_title}_quality_assessment.json")
                if alt_report_path.exists():
                    report_path = alt_report_path
                else:
                    return jsonify({
                        "success": False,
                        "error": "评估报告不存在",
                        "hint": "请先生成第一阶段设定"
                    }), 404

            # 读取评估报告
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)

            logger.info(f"[QUALITY_ASSESSMENT] 返回评估报告: {report.get('overall_score', 0)}/100")

            return jsonify({
                "success": True,
                "report": report
            })

        except Exception as e:
            logger.error(f"[QUALITY_ASSESSMENT] 获取评估报告失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500


    @app.route('/api/quality-assessment/trigger/<path:novel_title>', methods=['POST'])
    @login_required
    def trigger_quality_assessment(novel_title):
        """手动触发质量评估"""
        try:
            from pathlib import Path
            import re
            from src.core.PlanQualityAssessor import PlanQualityAssessor

            # URL解码
            novel_title = re.sub(r'_|\+', ' ', novel_title)

            logger.info(f"[QUALITY_ASSESSMENT] 触发质量评估: {novel_title}")

            # 构建写作计划路径
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            plan_path = Path(f"小说项目/{safe_title}/plans/{safe_title}_opening_stage_writing_plan.json")

            if not plan_path.exists():
                return jsonify({
                    "success": False,
                    "error": "写作计划文件不存在"
                }), 404

            # 获取API密钥（用于AI评估）
            api_key = request.json.get('api_key') if request.json else None
            use_deep_analysis = request.json.get('deep_analysis', True) if request.json else True

            # 创建评估器并执行评估
            assessor = PlanQualityAssessor(api_key=api_key)
            result = assessor.assess(plan_path, use_deep_analysis=use_deep_analysis)

            # 转换为字典格式
            report = {
                "overall_score": result.overall_score,
                "readiness": result.readiness,
                "strengths": result.strengths,
                "issues": [
                    {
                        "category": i.category,
                        "severity": i.severity.value,
                        "location": i.location,
                        "description": i.description,
                        "suggestion": i.suggestion,
                        "auto_fixable": i.auto_fixable
                    }
                    for i in result.issues
                ],
                "summary": result.summary,
                "token_saved": result.token_saved,
                "assessment_time": datetime.now().isoformat()
            }

            logger.info(f"[QUALITY_ASSESSMENT] 评估完成: {report['overall_score']}/100")

            return jsonify({
                "success": True,
                "report": report
            })

        except Exception as e:
            logger.error(f"[QUALITY_ASSESSMENT] 触发评估失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500


    @app.route('/api/quality-assessment/fix/<path:novel_title>', methods=['POST'])
    @login_required
    def fix_quality_issues(novel_title):
        """修复质量问题（基于AI建议）"""
        try:
            from pathlib import Path
            import re

            # URL解码
            novel_title = re.sub(r'_|\+', ' ', novel_title)

            logger.info(f"[QUALITY_ASSESSMENT] 修复质量问题: {novel_title}")

            # 获取要修复的问题列表
            fix_data = request.json or {}
            issues_to_fix = fix_data.get('issues', [])
            auto_fix_only = fix_data.get('auto_fix_only', False)

            if not issues_to_fix:
                return jsonify({
                    "success": False,
                    "error": "未指定要修复的问题"
                }), 400

            # 构建路径
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            plan_path = Path(f"小说项目/{safe_title}/plans/{safe_title}_opening_stage_writing_plan.json")

            if not plan_path.exists():
                return jsonify({
                    "success": False,
                    "error": "写作计划文件不存在"
                }), 404

            # 读取当前计划
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)

            # 执行修复
            fixed_count = 0
            skipped_count = 0
            fix_results = []

            for issue in issues_to_fix:
                issue_id = issue.get('id') or f"{issue.get('category')}_{issue.get('location')}"
                location = issue.get('location', '')
                category = issue.get('category', '')
                suggestion = issue.get('suggestion', '')

                try:
                    # 根据问题类别执行不同的修复策略
                    if category == 'commercial' and 'expectation_tags' in suggestion:
                        # 添加缺失的情感标签
                        fixed = _add_missing_expectation_tags(plan_data, location)
                        if fixed:
                            fixed_count += 1
                            fix_results.append({"id": issue_id, "status": "fixed", "action": "添加情感标签"})
                        else:
                            skipped_count += 1
                            fix_results.append({"id": issue_id, "status": "skipped", "reason": "无法自动修复"})

                    elif category == 'pacing' and '章节' in suggestion:
                        # 章节分配问题 - 记录建议，需要手动调整
                        skipped_count += 1
                        fix_results.append({"id": issue_id, "status": "manual_required", "suggestion": suggestion})

                    elif category == 'structure' and '事件' in suggestion:
                        # 结构问题 - 记录建议，需要手动调整
                        skipped_count += 1
                        fix_results.append({"id": issue_id, "status": "manual_required", "suggestion": suggestion})

                    else:
                        # 其他问题，如果标记为可自动修复则尝试
                        if issue.get('auto_fixable', False) and not auto_fix_only:
                            # 这里可以扩展更多的自动修复逻辑
                            skipped_count += 1
                            fix_results.append({"id": issue_id, "status": "not_implemented", "reason": "该类型修复尚未实现"})
                        else:
                            skipped_count += 1
                            fix_results.append({"id": issue_id, "status": "manual_required", "suggestion": suggestion})

                except Exception as e:
                    logger.error(f"修复问题失败 {issue_id}: {e}")
                    fix_results.append({"id": issue_id, "status": "error", "error": str(e)})

            # 如果有修复，保存更新后的计划
            if fixed_count > 0:
                # 创建备份
                backup_path = plan_path.with_suffix('.json.backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.load(open(plan_path, 'r', encoding='utf-8'))  # 先读取原始内容
                    with open(plan_path, 'r', encoding='utf-8') as original:
                        f.write(original.read())
                logger.info(f"已创建备份: {backup_path}")

                # 保存修复后的计划
                with open(plan_path, 'w', encoding='utf-8') as f:
                    json.dump(plan_data, f, ensure_ascii=False, indent=2)

            return jsonify({
                "success": True,
                "fixed_count": fixed_count,
                "skipped_count": skipped_count,
                "fix_results": fix_results,
                "backup_created": fixed_count > 0
            })

        except Exception as e:
            logger.error(f"[QUALITY_ASSESSMENT] 修复失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500


    def _add_missing_expectation_tags(plan_data: dict, location: str) -> bool:
        """为缺失情感标签的事件添加标签"""
        try:
            # 解析location，如 "major_events" 意味着所有major_events
            # 或 "major_event[0]" 表示特定事件

            stage_plan = plan_data.get('stage_writing_plan', {})
            event_system = stage_plan.get('event_system', {})
            major_events = event_system.get('major_events', [])

            if not major_events:
                return False

            # 为所有大型事件添加默认的情感标签
            for event in major_events:
                if not event.get('expectation_tags'):
                    event['expectation_tags'] = ['期待', '紧张', '反转']

            return True
        except Exception as e:
            logger.error(f"添加情感标签失败: {e}")
            return False