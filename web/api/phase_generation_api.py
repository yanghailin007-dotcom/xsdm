"""
两阶段小说生成API接口 - 完整版本
"""

from flask import Blueprint, request, jsonify
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
        self.project_dir = Path("小说项目") / self.original_title
        if not self.project_dir.exists():
            self.project_dir = Path("小说项目") / self.safe_title
        self.legacy_phase_one_dir = Path("小说项目") / f"{self.safe_title}_第一阶段设定"
    
    def load_all_products(self):
        products = {
            'worldview': self._create_empty_product('世界观设定'),
            'characters': self._create_empty_product('角色设计'),
            'growth': self._create_empty_product('成长路线'),
            'writing': self._create_empty_product('写作计划'),
            'storyline': self._create_empty_product('故事线'),
            'market': self._create_empty_product('市场分析')
        }
        
        self._load_from_quality_data(products)
        self._load_from_standard_structure(products)
        self._load_from_legacy_structure(products)
        self._load_from_phase_one_file(products)
        
        return products
    
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
            for stage_name, plan_data in writing_plans.items():
                if plan_data and isinstance(plan_data, dict):
                    products['writing']['content'] = json.dumps(plan_data, ensure_ascii=False, indent=2)
                    products['writing']['complete'] = True
                    products['writing']['file_path'] = f"quality_data/writing_plans/{stage_name}"
                    self.logger.info(f"从quality_data加载写作计划: {stage_name}")
                    break
    
    def _load_from_standard_structure(self, products):
        if not products['worldview']['complete']:
            self._load_worldview(products)
        
        if not products['characters']['complete']:
            self._load_characters(products)
        
        if not products['writing']['complete']:
            self._load_writing_plans(products)
        
        if not products['market']['complete']:
            self._load_market_analysis(products)
        
        if not products['storyline']['complete'] and products['writing']['complete']:
            self._extract_storyline_from_writing(products)
    
    def _load_worldview(self, products):
        worldview_dir = self.project_dir / "worldview"
        if not worldview_dir.exists():
            worldview_dir = self.project_dir / "materials" / "worldview"
        
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
            patterns = [
                f"{self.original_title}_*_writing_plan*.json",
                f"{self.safe_title}_*_writing_plan*.json",
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
                
                # 按照标准阶段顺序排序
                sorted_stage_names = get_sorted_stages(writing_data['stage_names'])
                
                for stage_name in sorted_stage_names:
                    if stage_name in writing_data['stages']:
                        stage_data = writing_data['stages'][stage_name]
                        stage_plan = stage_data.get('stage_writing_plan', {})
                        
                        # 提取该阶段的重大事件
                        major_events = stage_plan.get('event_system', {}).get('major_events', [])
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
                        'major_events': all_major_events
                    }
                    products['storyline']['content'] = json.dumps(storyline_data, ensure_ascii=False, indent=2)
                    products['storyline']['complete'] = True
                    products['storyline']['file_path'] = products['writing']['file_path']
                    self.logger.info(f"从写作计划提取storyline数据: {len(stage_info)} 个阶段, {len(all_major_events)} 个重大事件")
                    return
            
            # 检查是否是单阶段写作计划（旧格式）
            storyline_data = (
                writing_data.get('stage_writing_plan', {}).get('event_system', {}).get('major_events', []) or
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
        
        product_files = {
            'worldview': f"{self.safe_title}_世界观设定.json",
            'characters': f"{self.safe_title}_角色设计.json",
            'growth': f"{self.safe_title}_成长路线.json",
            'writing': f"{self.safe_title}_写作计划.json",
            'storyline': f"{self.safe_title}_阶段计划.json",  # 这个作为备用
            'market': f"{self.safe_title}_市场分析.json"
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
                                    
                                    for stage_name, stage_file in sorted_pairs:
                                        with open(stage_file, 'r', encoding='utf-8') as f:
                                            stage_data = json.load(f)
                                        
                                        stage_plan = stage_data.get('stage_writing_plan', {})
                                        major_events = stage_plan.get('event_system', {}).get('major_events', [])
                                        
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
    """启动第一阶段生成任务"""
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
        
        # 构建创意种子（如果没有提供的话）
        if not creative_seed:
            creative_seed = {
                "novelTitle": title,
                "storySynopsis": synopsis,
                "coreSetting": core_setting,
                "coreSellingPoints": core_selling_points if isinstance(core_selling_points, list) else [core_selling_points] if core_selling_points else []
            }
        
        # 构建生成参数
        generation_params = {
            'title': title,
            'synopsis': synopsis,
            'core_setting': core_setting,
            'core_selling_points': core_selling_points,
            'total_chapters': total_chapters,
            'generation_mode': generation_mode,
            'creative_seed': creative_seed
        }
        
        # 调用管理器启动实际的第一阶段生成任务
        logger.info(f"🚀 [PHASE_ONE] 调用管理器启动生成任务...")
        task_id = manager.start_generation(generation_params)
        
        logger.info(f"✅ [PHASE_ONE] 任务已启动: {task_id}")
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "第一阶段生成任务已启动",
            "status": "initializing"
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
        
        # 返回任务状态
        response = {
            "success": True,
            "task_id": task_id,
            "status": task_status.get("status", "unknown"),
            "progress": task_status.get("progress", 0),
            "current_step": task_status.get("current_step", ""),
            "created_at": task_status.get("created_at", ""),
            "updated_at": task_status.get("updated_at", "")
        }
        
        # 如果任务完成，包含结果
        if task_status.get("status") == "completed" and "result" in task_status:
            response["result"] = task_status["result"]
        
        # 如果任务失败，包含错误信息
        if task_status.get("status") == "failed" and "error" in task_status:
            response["error"] = task_status["error"]
        
        return jsonify(response)
        
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
        logger.info(f"[PRODUCTS_DEBUG] 开始加载项目产物: {title}")
        
        loader = ProductLoader(title, logger)
        products = loader.load_all_products()
        
        completed = sum(1 for p in products.values() if p['complete'])
        total = len(products)
        
        logger.info(f"[PRODUCTS_DEBUG] 产物加载完成: {completed}/{total} 个产物已加载")
        
        if completed == 0:
            logger.error(f"[PRODUCTS_DEBUG] 未找到任何产物文件")
            logger.info(f"[PRODUCTS_DEBUG] 检查的目录:")
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


# ==================== 路由注册函数 ====================

def register_phase_routes(app, manager_instance=None):
    """注册两阶段生成API路由"""
    app.register_blueprint(phase_api, url_prefix='/api')
    
    if manager_instance:
        global manager
        manager = manager_instance
    
    # 注册额外的路由
    register_additional_routes(app)
    
    logger.info("=" * 60)
    logger.info("📋 已注册的两阶段生成API路由:")
    for rule in app.url_map.iter_rules():
        if 'phase' in rule.rule or 'projects/with-phase-status' in rule.rule or 'storyline' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("=" * 60)
    
    logger.info("两阶段生成API路由注册完成")


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
            
            # 为每个项目添加阶段状态信息
            projects_with_status = []
            for project in all_projects:
                project_title = project.get('title', project.get('novel_title', ''))
                if not project_title:
                    continue
                
                # 获取项目详情以确定阶段状态
                novel_detail = manager.get_novel_detail(project_title)
                
                # 确定第一阶段状态
                phase_one_status = 'not_started'
                phase_one_completed_at = None
                
                # 检查第一阶段产物是否存在
                has_phase_one_products = False
                if novel_detail:
                    # 检查是否有世界观设定、角色设计等第一阶段产物
                    quality_data = novel_detail.get("quality_data", {})
                    has_phase_one_products = bool(quality_data) or bool(novel_detail.get("core_worldview"))
                
                if has_phase_one_products:
                    phase_one_status = 'completed'
                    phase_one_completed_at = project.get('created_at', project.get('last_updated'))
                
                # 确定第二阶段状态
                phase_two_status = 'not_started'
                phase_two_completed_at = None
                total_chapters = project.get('total_chapters', 0)
                completed_chapters = project.get('completed_chapters', 0)
                
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
                    'total_chapters': total_chapters or 50,  # 默认50章
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
            if not manager:
                return jsonify({"success": False, "error": "Manager not initialized"}), 500
            
            novel_detail = manager.get_novel_detail(title)
            if not novel_detail:
                return jsonify({"success": False, "error": "项目不存在"}), 404
            
            # 添加阶段信息
            total_chapters = novel_detail.get('current_progress', {}).get('total_chapters', 50)
            completed_chapters = len(novel_detail.get('generated_chapters', {}))
            
            # 检查第一阶段产物
            quality_data = novel_detail.get("quality_data", {})
            has_phase_one = bool(quality_data) or bool(novel_detail.get("core_worldview"))
            
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
            
            # ========== 新增：首先尝试从项目目录加载已保存的期待感映射 ==========
            try:
                loader = ProductLoader(title, logger)
                expectation_map_file = loader.project_dir / "expectation_map.json"
                
                if expectation_map_file.exists():
                    with open(expectation_map_file, 'r', encoding='utf-8') as f:
                        expectation_data = json.load(f)
                        expectation_map = expectation_data.get('expectation_map', expectation_data)
                        logger.info(f"[STORYLINE] 从项目目录加载期待感映射: {expectation_map_file.name}")
            except Exception as e:
                logger.info(f"[STORYLINE] 从项目目录加载期待感映射失败: {e}")
            
            # 从 quality_data 中提取故事线数据
            quality_data = novel_detail.get("quality_data", {})
            
            if quality_data:
                writing_plans = quality_data.get("writing_plans", {})
                if writing_plans:
                    # 遍历写作计划，提取故事线相关数据
                    for stage_name, plan_data in writing_plans.items():
                        if isinstance(plan_data, dict):
                            # 尝试从不同可能的位置提取重大事件数据
                            major_events = (
                                plan_data.get('stage_writing_plan', {}).get('event_system', {}).get('major_events', []) or
                                plan_data.get('event_system', {}).get('major_events', []) or
                                plan_data.get('major_events', [])
                            )
                            
                            if major_events:
                                storyline_data = {
                                    'stage_name': stage_name,
                                    'chapter_range': plan_data.get('chapter_range', ''),
                                    'major_events': major_events
                                }
                                logger.info(f"[STORYLINE] 从写作计划提取到故事线: {stage_name}, {len(major_events)} 个重大事件")
                                break
                    
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
                                    event_id=event_name,
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
            
            # ========== 统一的期待感映射生成逻辑 ==========
            if storyline_data and storyline_data.get('major_events') and not expectation_map:
                logger.info(f"[STORYLINE] 故事线数据已加载，但未找到期待感映射，开始自动生成...")
                
                try:
                    from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator
                    expectation_manager = ExpectationManager()
                    expectation_integrator = ExpectationIntegrator(expectation_manager)
                    
                    major_events = storyline_data.get('major_events', [])
                    total_tagged = 0
                    
                    # 为每个重大事件添加期待感标签
                    for event in major_events:
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
                            event_id=event_name,
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
                storyline_data['expectation_map'] = expectation_map
                logger.info(f"[STORYLINE] 已添加期待感映射到故事线数据 (共 {len(expectation_map.get('expectations', {}))} 个期待)")
            elif storyline_data and not expectation_map:
                logger.info(f"[STORYLINE] ⚠️ 故事线数据存在但没有期待感映射，前端将不会显示期待感标签")
            
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