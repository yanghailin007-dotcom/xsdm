# -*- coding: utf-8 -*-
"""
Dialog Polish Manager
对话打磨管理器

管理市场导向模式的多轮对话打磨流程，让用户参与创意差异化设计
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# 全局配置缓存
_dialog_polish_config = None

def _load_dialog_polish_config() -> Dict:
    """加载对话打磨配置"""
    global _dialog_polish_config
    if _dialog_polish_config is not None:
        return _dialog_polish_config
    
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        'config', 'dialog_polish_config.json'
    )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            _dialog_polish_config = json.load(f)
            logger.info(f"[DialogPolishManager] 配置加载成功: {config_path}")
            return _dialog_polish_config
    except Exception as e:
        logger.error(f"[DialogPolishManager] 配置加载失败: {e}")
        _dialog_polish_config = {}
        return _dialog_polish_config


class DialogRoundType(Enum):
    """对话轮次类型"""
    INIT = "init"                    # 初始化，展示套路框架
    DIFFERENTIATION = "differentiation"  # 选择差异化方向
    PROTAGONIST = "protagonist"      # 主角性格
    GOLDEN_FINGER = "golden_finger"  # 金手指设定
    PLOT_DETAILS = "plot_details"    # 剧情细节
    EMOTION_LINE = "emotion_line"    # 情感线
    CONFIRM = "confirm"              # 确认最终方案


@dataclass
class DialogRound:
    """对话轮次"""
    round_num: int
    round_type: DialogRoundType
    ai_message: str
    options: List[Dict]              # 选项列表
    allow_custom: bool = True        # 是否允许自定义输入
    user_choice: Optional[str] = None
    user_custom_input: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CreativeDraft:
    """创意草案"""
    title: str = ""
    protagonist: str = ""
    protagonist_type: str = ""
    golden_finger: str = ""                    # 用户选择的金手指描述（简短）
    golden_finger_type: str = ""               # 金手指类型ID
    golden_finger_design: Dict = field(default_factory=dict)  # 🔥 新增：AI生成的完整金手指设定
    unique_points: str = ""
    emotion_pacing: str = ""
    opening_design: str = ""
    emotion_line: str = ""
    risk_mitigation: str = ""
    ai_evaluation: Dict = field(default_factory=dict)  # AI自评结果
    dialog_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "protagonist": self.protagonist,
            "protagonist_type": self.protagonist_type,
            "golden_finger": self.golden_finger,
            "golden_finger_type": self.golden_finger_type,
            "golden_finger_design": self.golden_finger_design,  # 🔥 新增
            "unique_points": self.unique_points,
            "emotion_pacing": self.emotion_pacing,
            "opening_design": self.opening_design,
            "emotion_line": self.emotion_line,
            "risk_mitigation": self.risk_mitigation,
            "ai_evaluation": self.ai_evaluation
        }


class DialogPolishManager:
    """
    对话打磨管理器
    
    管理完整的对话打磨流程：
    1. 展示套路框架（让用户了解市场规律）
    2. 引导用户选择差异化方向
    3. 多轮对话细化设定
    4. 生成创意草案
    5. 准备数据供AI评估
    """
    
    # 类级别的AI生成配置缓存，避免重复调用AI
    _genre_config_cache: Dict[str, Dict] = {}
    
    def __init__(self, genre: str, tropes: Dict, api_client=None):
        self.session_id = f"DPM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.genre = genre
        self.tropes = tropes
        self.api_client = api_client
        
        self.rounds: List[DialogRound] = []
        self.current_round = 0
        self.creative_draft = CreativeDraft()
        
        # 套路框架数据（从tropes提取）
        self.trope_framework = self._extract_trope_framework()
        
        logger.info(f"[对话打磨 {self.session_id}] 初始化 | 题材: {genre}")
    
    def _generate_genre_config_with_ai(self, genre: str) -> Dict:
        """
        使用AI为未知题材生成配置
        
        Args:
            genre: 题材名称，如 "读心术-吐槽反差类"
            
        Returns:
            包含 protagonist_options, golden_finger_options, plot_details 的配置字典
        """
        if not self.api_client:
            logger.warning(f"[对话打磨 {self.session_id}] API客户端未初始化，无法为题材 '{genre}' 生成AI配置")
            return {}
        
        # 检查缓存
        if genre in DialogPolishManager._genre_config_cache:
            logger.info(f"[对话打磨 {self.session_id}] 命中题材配置缓存: '{genre}'")
            return DialogPolishManager._genre_config_cache[genre]
        
        logger.info(f"[对话打磨 {self.session_id}] 使用AI为题材 '{genre}' 生成配置")
        
        prompt = f"""你是一位资深网文编辑，擅长分析小说题材和创作套路。

请为以下题材生成创作配置：

**题材名称：** {genre}

请根据该题材的特点，生成以下内容：

1. **主角性格选项**（5个选项）：
   - 每个选项需要包含：id, label（带emoji）, market_score（0-100）, risk（低/中/高）
   - 选项要体现该题材的差异化方向

2. **题材特定描述**（对应5个主角性格）：
   - 每个性格在该题材下的具体表现描述

3. **金手指选项**（5个选项）：
   - 每个选项需要包含：id, label（带emoji）, description, market_score
   - 要有该题材特色的限制条件或代价

4. **开局设计选项**（4个选项）：
   - 经典开局、意外入局、复仇归来、被迫参加
   - 每个选项需要包含：id, label（带emoji）, description, hook_strength, familiarity

请输出标准JSON格式：
{{
    "protagonist_descriptions": {{
        "calm": "冷静理智型在该题材的表现...",
        "talkative": "话痨吐槽型在该题材的表现...",
        "lazy": "佛系摆烂型在该题材的表现...",
        "crazy": "疯批乐子型在该题材的表现...",
        "antihero": "反英雄型在该题材的表现..."
    }},
    "golden_finger_options": [
        {{
            "id": "unique_option_1",
            "label": "🎯 选项名称",
            "description": "详细描述该金手指的特点和限制",
            "combo_effect": "与主角性格的联动效果",
            "market_score": 75
        }},
        ...（共5个）
    ],
    "plot_details": [
        {{
            "id": "classic",
            "label": "📖 经典开局",
            "description": "该题材经典开局的具体描述",
            "hook_strength": "★★★☆☆",
            "familiarity": "高（读者容易接受）"
        }},
        ...（共4个：classic, unexpected, revenge, forced）
    ]
}}

要求：
1. 所有内容必须贴合题材 '{genre}' 的特点
2. 主角性格和金手指要有联动效果
3. 选项要有差异化，避免同质化
4. 返回的JSON必须有效且完整"""

        try:
            response = self.api_client.generate_content_with_retry(
                content_type="genre_config_generation",
                user_prompt=prompt,
                temperature=0.8
            )
            
            if response:
                import json
                import re
                # 提取JSON部分
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    result = json.loads(json_match.group())
                    # 验证必要字段
                    if all(k in result for k in ["protagonist_descriptions", "golden_finger_options", "plot_details"]):
                        # 缓存结果
                        DialogPolishManager._genre_config_cache[genre] = result
                        logger.info(f"[对话打磨 {self.session_id}] AI成功为题材 '{genre}' 生成配置")
                        return result
                    else:
                        logger.warning(f"[对话打磨 {self.session_id}] AI生成的配置缺少必要字段")
        except Exception as e:
            logger.error(f"[对话打磨 {self.session_id}] AI生成题材配置失败: {e}")
        
        return {}
    
    def _is_config_incomplete(self, config: Dict, step: str) -> bool:
        """
        检查配置是否不完整
        
        Args:
            config: 配置字典
            step: 步骤名称 (protagonist, golden_finger, plot_details)
            
        Returns:
            如果配置为空或不完整返回True
        """
        if not config:
            return True
            
        if step == "protagonist":
            # 检查是否有有效的descriptions
            descriptions = config.get("descriptions", {})
            return not descriptions or len(descriptions) < 3
            
        elif step == "golden_finger":
            # 检查是否有有效的options列表
            options = config.get("options", [])
            return not options or len(options) < 2
            
        elif step == "plot_details":
            # 检查是否有有效的options列表
            options = config.get("options", [])
            return not options or len(options) < 2
            
        return False
    
    def _extract_trope_framework(self) -> Dict:
        """从爆款分析中提取框架信息"""
        return {
            "core_formula": self.tropes.get("core_formula", ""),
            "typical_arcs": self.tropes.get("typical_arcs", []),
            "protagonist_types": self.tropes.get("protagonist", {}).get("types", []),
            "golden_finger_types": self.tropes.get("golden_finger", {}).get("types", []),
            "common_tropes": self.tropes.get("common_tropes", []),
            "emotion_curve": self.tropes.get("emotion_curve", {}),
            "market_saturation": "高"  # 默认假设同质化严重
        }
    
    def _get_genre_protagonist_data(self) -> str:
        """
        根据题材返回常见人设描述
        不同题材有不同的主流主角性格
        优先从JSON配置加载，失败则使用内置映射
        """
        # 🔥 清理 genre，去除前后空格
        raw_genre = self.genre.strip() if self.genre else ""
        genre_lower = raw_genre.lower()
        
        # 🔥 调试日志
        logger.info(f"[_get_genre_protagonist_data] 原始题材: '{self.genre}' -> 清理后: '{raw_genre}'")
        
        # 从JSON配置加载
        config = _load_dialog_polish_config()
        genre_mappings = config.get("genre_mappings", {})
        protagonist_data = genre_mappings.get("protagonist_data", {})
        
        # 首先尝试从配置完整匹配
        if raw_genre in protagonist_data:
            result = protagonist_data[raw_genre]
            logger.info(f"[_get_genre_protagonist_data] 配置完整匹配成功: '{raw_genre}' -> {result}")
            return result
        
        # 内置映射作为后备（与UI上的题材列表匹配）
        protagonist_data_map = {
            # 神豪类
            "神豪文-花钱返利类": "张扬霸气型（市场占比40%，完读率15%）",
            "神豪文-签到奖励类": "稳健务实型（市场占比35%，完读率14%）",
            "神豪": "张扬霸气型（市场占比40%，完读率15%）",
            
            # 国运类
            "国运文-直播类": "冷静理智型（市场占比35%，完读率12%）",
            "国运文-禁地探险类": "坚韧执着型（市场占比33%，完读率11%）",
            "国运": "冷静理智型（市场占比35%，完读率12%）",
            
            # 签到类
            "签到文-日常签到类": "佛系随和型（市场占比38%，完读率13%）",
            "签到": "佛系随和型（市场占比38%，完读率13%）",
            
            # 奶爸类
            "奶爸文-萌宝类": "温柔奶爸型（市场占比42%，完读率18%）",
            "奶爸文-修炼类": "坚毅守护型（市场占比36%，完读率15%）",
            "奶爸": "温柔奶爸型（市场占比42%，完读率18%）",
            
            # 神选类
            "神选文-神明选拔类": "自信张扬型（市场占比37%，完读率13%）",
            "神选": "自信张扬型（市场占比37%，完读率13%）",
            
            # 模拟器类
            "模拟器文-人生模拟类": "谨慎谋虑型（市场占比34%，完读率15%）",
            "模拟器": "谨慎谋虑型（市场占比34%，完读率15%）",
            
            # 灵气复苏类
            "灵气复苏-觉醒类": "坚韧逆袭型（市场占比39%，完读率14%）",
            "灵气复苏": "坚韧逆袭型（市场占比39%，完读率14%）",
            
            # 末日类
            "末日求生-囤货类": "谨慎务实型（市场占比41%，完读率16%）",
            "末日": "杀伐果断型（市场占比38%，完读率15%）",
            
            # 四合院类
            "四合院-日常类": "圆滑世故型（市场占比43%，完读率17%）",
            "四合院": "圆滑世故型（市场占比43%，完读率17%）",
            
            # 诡异类
            "诡异复苏-规则怪谈类": "冷静观察型（市场占比36%，完读率18%）",
            "诡异": "冷静观察型（市场占比36%，完读率18%）",
            
            # 游戏异界类
            "游戏异界-虚拟现实类": "热血进取型（市场占比38%，完读率14%）",
            "游戏异界": "热血进取型（市场占比38%，完读率14%）",
            "虚拟现实": "热血进取型（市场占比38%，完读率14%）",
            
            # 美食类
            "美食文-系统烹饪类": "专注执着型（市场占比40%，完读率16%）",
            "美食": "专注执着型（市场占比40%，完读率16%）",
            
            # 宠物/御兽类
            "宠物文-御兽进化类": "温柔耐心型（市场占比37%，完读率17%）",
            "宠物": "温柔耐心型（市场占比37%，完读率17%）",
            "御兽": "温柔耐心型（市场占比37%，完读率17%）",
            
            # 历史架空类
            "历史架空-权谋争霸类": "深谋远虑型（市场占比35%，完读率15%）",
            "历史架空": "深谋远虑型（市场占比35%，完读率15%）",
            "权谋": "深谋远虑型（市场占比35%，完读率15%）",
            
            # 文娱类
            "文娱文-文抄公类": "自信张扬型（市场占比39%，完读率15%）",
            "文娱": "自信张扬型（市场占比39%，完读率15%）",
            
            # 盗墓类
            "盗墓文-探险寻宝类": "谨慎果敢型（市场占比38%，完读率16%）",
            "盗墓": "谨慎果敢型（市场占比38%，完读率16%）",
            
            # 综漫/无限流类
            "综漫文-无限流类": "冷静适应型（市场占比36%，完读率14%）",
            "综漫": "冷静适应型（市场占比36%，完读率14%）",
            "无限流": "冷静适应型（市场占比36%，完读率14%）",
        }
        
        # 首先尝试完整匹配（使用清理后的 genre）
        if raw_genre in protagonist_data_map:
            result = protagonist_data_map[raw_genre]
            logger.info(f"[_get_genre_protagonist_data] 内置完整匹配成功: '{raw_genre}' -> {result}")
            return result
        
        # 🔥 尝试匹配题材关键词（按优先级排序，优先匹配更具体的）
        priority_keywords = [
            # 神豪类（高优先级）
            "神豪文-花钱返利类", "神豪文-签到奖励类", "神豪文", "神豪",
            # 国运类
            "国运文-直播类", "国运文-禁地探险类", "国运文", "国运",
            # 其他类别...
            "奶爸文-萌宝类", "奶爸文-修炼类", "奶爸",
            "签到文-日常签到类", "签到",
            "末日求生-囤货类", "末日",
            "诡异复苏-规则怪谈类", "诡异",
            "游戏异界-虚拟现实类", "游戏异界", "虚拟现实",
            "宠物文-御兽进化类", "宠物", "御兽",
            "历史架空-权谋争霸类", "历史架空", "权谋",
            "灵气复苏-觉醒类", "灵气复苏",
            "模拟器文-人生模拟类", "模拟器",
            "神选文-神明选拔类", "神选",
            "四合院-日常类", "四合院",
            "美食文-系统烹饪类", "美食",
            "文娱文-文抄公类", "文娱",
            "盗墓文-探险寻宝类", "盗墓",
            "综漫文-无限流类", "综漫", "无限流",
            "多子多福", "多子",
        ]
        
        for key in priority_keywords:
            if key in genre_lower:
                value = protagonist_data_map.get(key)
                if value:
                    logger.info(f"[_get_genre_protagonist_data] 内置优先级匹配成功: {key} -> {value}")
                    return value
        
        # 兜底：遍历所有关键词
        for key, value in protagonist_data_map.items():
            if key in genre_lower:
                logger.info(f"[_get_genre_protagonist_data] 内置兜底匹配成功: {key} -> {value}")
                return value
        
        # 使用配置的默认描述或内置默认
        default = protagonist_data.get("default", "冷静理智型（市场占比约35%，完读率约13%）")
        logger.info(f"[_get_genre_protagonist_data] 使用默认描述: {default}")
        return default
    
    def _get_genre_golden_finger_data(self) -> str:
        """
        根据题材返回常见金手指描述
        不同题材有不同的主流金手指类型
        优先从JSON配置加载，失败则使用内置映射
        """
        # 🔥 清理 genre，去除前后空格
        raw_genre = self.genre.strip() if self.genre else ""
        genre_lower = raw_genre.lower()
        
        # 从JSON配置加载
        config = _load_dialog_polish_config()
        genre_mappings = config.get("genre_mappings", {})
        gf_data = genre_mappings.get("golden_finger_data", {})
        
        # 首先尝试从配置完整匹配
        if raw_genre in gf_data:
            result = gf_data[raw_genre]
            logger.info(f"[_get_genre_golden_finger_data] 配置完整匹配成功: '{raw_genre}'")
            return result
        
        # 内置映射作为后备
        gf_data_map = {
            "神豪文-花钱返利类": "该题材常见金手指：花钱返利系统，消费越多赚得越多（市场占比50%，已略显套路化）",
            "神豪文-签到奖励类": "该题材常见金手指：每日签到获得随机奖励，积少成多（市场占比45%，发展成熟）",
            "神豪": "该题材常见金手指：花钱返利系统，消费越多赚得越多（市场占比50%，已略显套路化）",
            "国运文-直播类": "该题材常见金手指：绑定国运，代表国家参赛获得神级能力（市场占比45%，同质化严重）",
            "国运文-禁地探险类": "该题材常见金手指：获得探险能力或禁地地图，为国争光（市场占比42%，竞争激烈）",
            "国运": "该题材常见金手指：绑定国运，代表国家参赛获得神级能力（市场占比45%，同质化严重）",
            "签到文-日常签到类": "该题材常见金手指：日常签到获得各种奖励，轻松变强（市场占比40%，经典套路）",
            "签到": "该题材常见金手指：日常签到获得各种奖励，轻松变强（市场占比40%，经典套路）",
            "奶爸文-萌宝类": "该题材常见金手指：萌宝自带特殊能力或系统，辅助主角（市场占比38%，蓝海市场）",
            "奶爸": "该题材常见金手指：萌宝自带特殊能力或系统，辅助主角（市场占比38%，蓝海市场）",
            "末日求生-囤货类": "该题材常见金手指：重生或预知末日，提前大量囤货（市场占比44%，实用主义）",
            "末日": "该题材常见金手指：重生或空间能力，提前囤货或收集资源（市场占比44%，实用主义）",
            "诡异复苏-规则怪谈类": "该题材常见金手指：可以看到规则漏洞或免疫诡异污染（市场占比46%，恐怖求生）",
            "诡异": "该题材常见金手指：可以看到规则漏洞或免疫诡异污染（市场占比46%，恐怖求生）",
        }
        
        # 首先尝试完整匹配（使用清理后的 genre）
        if raw_genre in gf_data_map:
            result = gf_data_map[raw_genre]
            logger.info(f"[_get_genre_golden_finger_data] 内置完整匹配成功: '{raw_genre}'")
            return result
        
        # 🔥 尝试匹配题材关键词
        priority_keywords = [
            "神豪文-花钱返利类", "神豪文-签到奖励类", "神豪",
            "国运文-直播类", "国运文-禁地探险类", "国运",
            "签到", "奶爸", "末日", "诡异",
        ]
        
        for key in priority_keywords:
            if key in genre_lower:
                value = gf_data_map.get(key)
                if value:
                    logger.info(f"[_get_genre_golden_finger_data] 内置优先级匹配成功: {key}")
                    return value
        
        # 兜底：遍历所有关键词
        for key, value in gf_data_map.items():
            if key in genre_lower:
                logger.info(f"[_get_genre_golden_finger_data] 内置兜底匹配成功: {key}")
                return value
        
        # 使用配置的默认描述或内置默认
        default = gf_data.get("default", "该题材常见金手指：直接获得能力，无副作用（市场占比40%，但同质化严重）")
        logger.info(f"[_get_genre_golden_finger_data] 使用默认描述")
        return default
    
    def start_dialog(self) -> Dict:
        """
        开始对话打磨流程
        返回第一轮：套路框架展示 + 差异化方向选择
        """
        logger.info(f"[对话打磨 {self.session_id}] 开始第一轮")
        
        # 构建AI消息
        ai_message = self._build_init_message()
        
        # 构建差异化选项
        options = [
            {
                "id": "protagonist",
                "label": "🎭 主角性格",
                "description": "改变主角性格类型，如话痨、佛系、疯批等",
                "market_risk": "中",
                "examples": ["话痨吐槽型", "佛系摆烂型", "疯批乐子型"]
            },
            {
                "id": "golden_finger",
                "label": "⚡ 金手指设定",
                "description": "给金手指添加独特限制或代价",
                "market_risk": "低",
                "examples": ["有副作用的能力", "需要付出代价", "能力来自他人"]
            },
            {
                "id": "plot_twist",
                "label": "🔄 剧情反转",
                "description": "在经典套路中加入意外转折",
                "market_risk": "高",
                "examples": ["反派才是好人", "主角被误解", "能力反向作用"]
            },
            {
                "id": "emotion_line",
                "label": "💕 情感副线",
                "description": "增加独特的情感羁绊或关系",
                "market_risk": "低",
                "examples": ["妹妹是唯一记得他的人", "宿敌变挚友", "宠物有特殊能力"]
            },
            {
                "id": "narrative",
                "label": "📖 叙事视角",
                "description": "改变讲故事的方式",
                "market_risk": "高",
                "examples": ["群像视角", "反派视角", "多线并进"]
            },
            {
                "id": "multiple",
                "label": "🔥 多维度组合",
                "description": "同时改变2-3个维度，创造独特组合",
                "market_risk": "中",
                "examples": ["话痨+副作用+妹妹羁绊"]
            }
        ]
        
        round_data = DialogRound(
            round_num=1,
            round_type=DialogRoundType.INIT,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 1
        
        return self._format_round_response(round_data)
    
    def _build_init_message(self) -> str:
        """构建初始化消息"""
        genre = self.genre
        
        # 提取套路要点
        core_formula = self.trope_framework.get("core_formula", "")
        typical_arcs = self.trope_framework.get("typical_arcs", [])
        common_tropes = self.trope_framework.get("common_tropes", [])
        
        arcs_text = "\n".join([f"  • {arc}" for arc in typical_arcs[:3]]) if typical_arcs else "  • 经典逆袭打脸路线"
        tropes_text = "、".join(common_tropes[:5]) if common_tropes else "系统流、无敌流、震惊流"
        
        message = f"""🎯 **【{genre}】套路框架分析**

基于番茄小说Top100作品数据，该题材的**爆款公式**如下：

**📊 核心套路：**
{core_formula or '主角获得特殊能力→展现实力→震惊众人→不断升级打脸'}

**📈 经典剧情链：**
{arcs_text}

**🎭 常见元素：**
{tropes_text}

---

⚠️ **同质化风险警告：**
该题材市场饱和度高，直接套用上述套路容易导致：
• 首秀通过率 < 50%
• 完读率低于题材平均
• 难以获得算法推荐量

💡 **建议策略：**
在保留核心爽点框架的基础上，选择1-2个维度进行**差异化设计**。

**想在哪个角度做出不同？（可多选）**"""
        
        return message
    
    def process_user_input(self, user_input: str, custom_text: str = None) -> Dict:
        """
        处理用户输入，返回下一轮对话
        
        Args:
            user_input: 用户选择的选项ID
            custom_text: 用户自定义输入（可选）
        """
        # 保存当前轮次的用户选择
        if self.rounds:
            current = self.rounds[-1]
            current.user_choice = user_input
            current.user_custom_input = custom_text
        
        # 根据当前轮次决定下一步
        if self.current_round == 1:
            # 第一轮：差异化方向 → 主角性格
            return self._round_protagonist_type(user_input, custom_text)
        elif self.current_round == 2:
            # 第二轮：主角性格 → 金手指
            return self._round_golden_finger(user_input, custom_text)
        elif self.current_round == 3:
            # 第三轮：金手指 → 剧情细节
            return self._round_plot_details(user_input, custom_text)
        elif self.current_round == 4:
            # 第四轮：剧情细节 → 情感线
            return self._round_emotion_line(user_input, custom_text)
        elif self.current_round == 5:
            # 第五轮：情感线 → 生成完整方案
            return self._round_generate_full_plan(user_input, custom_text)
        elif self.current_round == 6:
            # 第六轮：确认最终方案
            return self._round_final_confirm(user_input, custom_text)
        else:
            # 结束对话
            return self._finish_dialog()
    
    def _get_protagonist_options(self) -> List[Dict]:
        """
        根据题材返回差异化的主角性格选项
        不同题材有不同的特色描述
        从JSON配置加载，如果不完整则使用AI生成
        """
        genre = self.genre.strip() if self.genre else ""
        
        # 加载JSON配置
        config = _load_dialog_polish_config()
        step_config = config.get("steps", {}).get("step_2_protagonist", {})
        
        # 获取基础选项
        base_options = step_config.get("base_options", {})
        
        # 获取题材特定描述或默认描述
        genre_specific = step_config.get("genre_specific", {})
        descriptions = None
        genre_config = None
        
        # 首先尝试精确匹配
        if genre in genre_specific:
            genre_config = genre_specific[genre]
            descriptions = genre_config.get("descriptions", {})
        else:
            # 尝试关键词匹配
            for genre_key, genre_data in genre_specific.items():
                if genre_key in genre:
                    genre_config = genre_data
                    descriptions = genre_data.get("descriptions", {})
                    break
        
        # 如果配置不完整，尝试使用AI生成
        if self._is_config_incomplete({"descriptions": descriptions}, "protagonist"):
            ai_config = self._generate_genre_config_with_ai(genre)
            if ai_config and "protagonist_descriptions" in ai_config:
                descriptions = ai_config["protagonist_descriptions"]
                logger.info(f"[对话打磨 {self.session_id}] 使用AI生成的 protagonist 描述")
        
        # 如果仍然没有描述，使用默认描述
        if not descriptions:
            descriptions = step_config.get("default_descriptions", {})
        
        # 构建选项列表
        result = []
        for option_id, base_option in base_options.items():
            option = dict(base_option)
            option["description"] = descriptions.get(option_id, "")
            result.append(option)
        
        return result
    
    def _round_protagonist_type(self, prev_choice: str, custom: str = None) -> Dict:
        """第二轮：主角性格选择"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第二轮：主角性格")
        
        # 记录选择
        self.creative_draft.protagonist_type = prev_choice
        
        # 🔥 记录主角性格到 protagonist 字段（包含自定义输入）
        protagonist_map = {
            "calm": "冷静理智型",
            "talkative": "话痨吐槽型",
            "lazy": "佛系摆烂型",
            "crazy": "疯批乐子型",
            "antihero": "反英雄型"
        }
        base_protagonist = protagonist_map.get(prev_choice, prev_choice)
        if custom:
            self.creative_draft.protagonist = f"{base_protagonist}（自定义：{custom}）"
        else:
            self.creative_draft.protagonist = base_protagonist
        
        # 🔥 根据题材动态获取选项
        options = self._get_protagonist_options()
        
        # 🔥 根据题材动态调整常见人设描述
        genre_protagonist_data = self._get_genre_protagonist_data()
        
        ai_message = f"""**🎭 第二步：主角性格设定**

主角性格决定了读者的代入方式和情感连接。

**该题材常见人设：** {genre_protagonist_data}

**差异化选项：**
（每个选项都标注了市场化评分和风险等级）

**你想让主角是什么性格？**"""
        
        round_data = DialogRound(
            round_num=2,
            round_type=DialogRoundType.PROTAGONIST,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 2
        
        return self._format_round_response(round_data)
    
    def _get_golden_finger_options(self, protagonist: str) -> List[Dict]:
        """
        根据题材返回差异化的金手指选项
        不同题材有不同的特色限制和代价
        从JSON配置加载，如果不完整则使用AI生成
        """
        genre = self.genre.strip() if self.genre else ""
        
        # 加载JSON配置
        config = _load_dialog_polish_config()
        step_config = config.get("steps", {}).get("step_3_golden_finger", {})
        
        # 获取基础选项
        base_options = step_config.get("base_options", [])
        
        # 处理combo_effect_template
        processed_base_options = []
        for option in base_options:
            processed_option = dict(option)
            if "combo_effect_template" in processed_option:
                processed_option["combo_effect"] = processed_option.pop("combo_effect_template").format(protagonist=protagonist)
            processed_base_options.append(processed_option)
        
        # 获取题材特定选项或默认选项
        genre_specific = step_config.get("genre_specific", {})
        specific_options = None
        
        # 首先尝试精确匹配
        if genre in genre_specific:
            specific_options = genre_specific[genre]
        else:
            # 尝试关键词匹配
            for genre_key, genre_data in genre_specific.items():
                if genre_key in genre:
                    specific_options = genre_data
                    break
        
        # 如果配置不完整，尝试使用AI生成
        if self._is_config_incomplete({"options": specific_options}, "golden_finger"):
            ai_config = self._generate_genre_config_with_ai(genre)
            if ai_config and "golden_finger_options" in ai_config:
                ai_options = ai_config["golden_finger_options"]
                # 处理combo_effect中的 protagonist 占位符
                processed_ai_options = []
                for option in ai_options:
                    processed_option = dict(option)
                    if "combo_effect" in processed_option:
                        processed_option["combo_effect"] = processed_option["combo_effect"].format(protagonist=protagonist)
                    processed_ai_options.append(processed_option)
                specific_options = processed_ai_options
                logger.info(f"[对话打磨 {self.session_id}] 使用AI生成的 golden_finger 选项")
        
        # 如果仍然没有匹配到，使用默认选项
        if not specific_options:
            specific_options = step_config.get("default_options", [])
        
        # 处理题材特定选项中的combo_effect_template
        processed_specific_options = []
        for option in specific_options:
            processed_option = dict(option)
            if "combo_effect_template" in processed_option:
                processed_option["combo_effect"] = processed_option.pop("combo_effect_template").format(protagonist=protagonist)
            processed_specific_options.append(processed_option)
        
        return processed_base_options + processed_specific_options
    
    def _round_golden_finger(self, prev_choice: str, custom: str = None) -> Dict:
        """第三轮：金手指设定"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第三轮：金手指")
        
        # 记录主角选择
        protagonist_map = {
            "calm": "冷静理智型",
            "talkative": "话痨吐槽型",
            "lazy": "佛系摆烂型",
            "crazy": "疯批乐子型",
            "antihero": "反英雄型"
        }
        self.creative_draft.protagonist = protagonist_map.get(prev_choice, prev_choice)
        if custom:
            self.creative_draft.protagonist += f"（自定义：{custom}）"
        
        # 🔥 根据题材动态获取选项
        options = self._get_golden_finger_options(self.creative_draft.protagonist)
        
        # 🔥 根据题材动态调整常见金手指描述
        genre_gf_data = self._get_genre_golden_finger_data()
        
        ai_message = f"""**⚡ 第三步：金手指设定**

当前选择的主角：**{self.creative_draft.protagonist}**

{genre_gf_data}

**差异化方向：** 给金手指添加**限制条件或代价**
（这样既能保留爽点，又能增加独特性和情感深度）

**你想设计什么样的金手指？**
（已智能推荐与主角性格和题材契合的选项）"""
        
        round_data = DialogRound(
            round_num=3,
            round_type=DialogRoundType.GOLDEN_FINGER,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 3
        
        return self._format_round_response(round_data)
    
    def _round_plot_details(self, prev_choice: str, custom: str = None) -> Dict:
        """第四轮：剧情细节"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第四轮：剧情细节")
        
        # 记录金手指选择（从JSON配置加载映射）
        config = _load_dialog_polish_config()
        step3_config = config.get("steps", {}).get("step_3_golden_finger", {})
        
        # 构建选项ID到标签的映射
        gf_map = {}
        for option in step3_config.get("base_options", []):
            gf_map[option["id"]] = option["label"]
        for genre_options in step3_config.get("genre_specific", {}).values():
            for option in genre_options:
                gf_map[option["id"]] = option["label"]
        for option in step3_config.get("default_options", []):
            gf_map[option["id"]] = option["label"]
        
        self.creative_draft.golden_finger = gf_map.get(prev_choice, prev_choice)
        self.creative_draft.golden_finger_type = prev_choice
        if custom:
            self.creative_draft.golden_finger += f"（自定义：{custom}）"
        
        # 加载step_4_plot_details配置
        step4_config = config.get("steps", {}).get("step_4_plot_details", {})
        
        # 获取题材特定选项或默认选项
        genre = self.genre.strip() if self.genre else ""
        genre_specific = step4_config.get("genre_specific", {})
        options = None
        
        # 首先尝试精确匹配
        if genre in genre_specific:
            options = genre_specific[genre]
        else:
            # 尝试关键词匹配
            for genre_key, genre_data in genre_specific.items():
                if genre_key in genre:
                    options = genre_data
                    break
        
        # 如果配置不完整，尝试使用AI生成
        if self._is_config_incomplete({"options": options}, "plot_details"):
            ai_config = self._generate_genre_config_with_ai(genre)
            if ai_config and "plot_details" in ai_config:
                options = ai_config["plot_details"]
                logger.info(f"[对话打磨 {self.session_id}] 使用AI生成的 plot_details 选项")
        
        # 如果仍然没有匹配到，使用默认选项
        if not options:
            options = step4_config.get("default_options", [])
        
        ai_message = f"""**🎬 第四步：开局设计**

当前设定汇总：
• 主角：**{self.creative_draft.protagonist}**
• 金手指：**{self.creative_draft.golden_finger}**

黄金三章（第1-3章）决定了读者是否会继续阅读。

**你想用什么开局吸引读者？**"""
        
        round_data = DialogRound(
            round_num=4,
            round_type=DialogRoundType.PLOT_DETAILS,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 4
        
        return self._format_round_response(round_data)
    
    def _get_emotion_line_options(self) -> List[Dict]:
        """
        根据题材返回差异化的情感线选项
        不同题材有不同的情感羁绊类型
        """
        genre = self.genre.strip() if self.genre else ""
        
        # 加载配置
        config = _load_dialog_polish_config()
        step_config = config.get("steps", {}).get("step_5_emotion_line", {})
        
        # 基础选项（所有题材都适用）
        base_options = step_config.get("base_options", [])
        
        # 题材特定选项
        genre_specific = step_config.get("genre_specific", {})
        
        # 默认选项
        default_options = step_config.get("default_options", [])
        
        # 尝试完整匹配
        if genre in genre_specific:
            return base_options + genre_specific[genre]
        
        # 尝试关键词匹配
        for key, options in genre_specific.items():
            if key in genre:
                return base_options + options
        
        # 兜底：返回基础选项 + 默认选项
        return base_options + default_options
    
    def _round_emotion_line(self, prev_choice: str, custom: str = None) -> Dict:
        """第五轮：情感线"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第五轮：情感线")
        
        # 记录开局设计
        self.creative_draft.opening_design = prev_choice
        if custom:
            self.creative_draft.opening_design += f"（自定义：{custom}）"
        
        # 🔥 根据题材动态获取情感线选项
        options = self._get_emotion_line_options()
        
        # 加载配置中的消息模板
        config = _load_dialog_polish_config()
        step_config = config.get("steps", {}).get("step_5_emotion_line", {})
        ai_message = step_config.get("ai_message_template", """**💕 第五步：情感副线（可选但推荐）**

情感线是增强读者粘性的重要手段，能让读者为角色的命运牵肠挂肚。

**你想添加什么样的情感羁绊？**
（建议选择与当前设定互补的选项）""")
        
        round_data = DialogRound(
            round_num=5,
            round_type=DialogRoundType.EMOTION_LINE,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 5
        
        return self._format_round_response(round_data)
    
    def _round_generate_full_plan(self, prev_choice: str, custom: str = None) -> Dict:
        """第六轮：AI生成完整方案（书名+大纲）"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第六轮：生成完整方案")
        
        # 记录情感线（包含所有题材特定选项）
        emotion_map = {
            # 基础选项
            "sister": "妹妹是唯一记得他的人，建立深层情感锚点",
            "rival": "宿敌变挚友，亦敌亦友的复杂关系",
            "pet": "特殊宠物伙伴，增加温馨元素",
            "mentor": "神秘导师引导，提供背景深度",
            "none": "专注事业线，无情感羁绊",
            # 神豪文选项
            "secretary": "漂亮能干的秘书/助理，事业伙伴也是红颜知己",
            "childhood_friend": "青梅竹马，不因贫穷或富贵而改变",
            "business_rival": "商业对手，最后变成最懂你的人",
            # 签到文选项
            "system_guide": "系统精灵/AI助手，亦师亦友",
            "fellow_signer": "签到伙伴，互相督促共同进步",
            # 国运文选项
            "national_fans": "全国人民都是后盾，家国情怀",
            "comrade": "为国征战的战友，生死与共",
            "live_stream_partner": "直播搭档，默契配合",
            # 国运-探险选项
            "teammate": "探险队友，禁地中的生死之交",
            "local_guide": "当地向导，熟悉禁地的神秘人",
            "family_legacy": "家族传承，先辈留下的足迹",
            # 奶爸文选项
            "cute_baby": "萌宝互动，最强助攻",
            "baby_mother": "妻子/前妻，复杂的感情纠葛",
            "other_parents": "家长群，互助交流",
            # 末日文选项
            "survival_team": "求生小队，末日中抱团取暖",
            "saved_stranger": "救下的幸存者，知恩图报",
            # 诡异文选项
            "fellow_survivor": "怪谈同伴，同病相怜",
            "mysterious_informant": "神秘线人，知道规则漏洞",
            # 御兽文选项
            "spirit_pet": "本命灵兽，共同成长",
            "beast_master_peer": "御兽师同行，切磋交流",
            # 灵气复苏选项
            "awakening_companion": "觉醒同伴，惺惺相惜",
            "ordinary_family": "普通家人，保护他们成为动力",
            # 其他
            "neighbor": "邻居日常，互帮互助"
        }
        self.creative_draft.emotion_line = emotion_map.get(prev_choice, prev_choice)
        if custom:
            self.creative_draft.emotion_line += f"（自定义：{custom}）"
        
        # 生成独特卖点和风险对冲
        self.creative_draft.unique_points = self._generate_unique_points()
        self.creative_draft.emotion_pacing = "快节奏，每3章一个小高潮"
        self.creative_draft.risk_mitigation = self._generate_risk_mitigation()
        
        # 🔥 调用AI生成金手指详细设定（新增）
        try:
            golden_finger_design = self._generate_golden_finger_detail_with_ai()
            self.creative_draft.golden_finger_design = golden_finger_design
            logger.info(f"[对话打磨 {self.session_id}] 金手指详细设定生成完成: {golden_finger_design.get('basic_info', {}).get('name', '未命名')}")
        except Exception as e:
            logger.warning(f"AI生成金手指详细设定失败: {e}")
            self.creative_draft.golden_finger_design = self._create_fallback_golden_finger()
        
        # 🔥 调用AI生成完整方案
        try:
            full_plan = self._generate_plan_with_ai()
            self.creative_draft.title = full_plan.get('title', '')
            self.creative_draft.opening_design = full_plan.get('opening', self.creative_draft.opening_design)
            # 将金手指详细设定加入full_plan
            full_plan['golden_finger'] = self.creative_draft.golden_finger_design
        except Exception as e:
            logger.warning(f"AI生成方案失败，使用默认: {e}")
            # 使用默认标题生成逻辑
            self.creative_draft.title = self._generate_default_title()
            full_plan = {
                'title': self.creative_draft.title,
                'golden_finger': self.creative_draft.golden_finger_design
            }
        
        # 🔥 调用AI进行自评
        try:
            ai_evaluation = self._generate_ai_evaluation()
            self.creative_draft.ai_evaluation = ai_evaluation
        except Exception as e:
            logger.warning(f"AI自评失败，使用默认: {e}")
            self.creative_draft.ai_evaluation = self._generate_default_evaluation()
        
        # 构建AI消息（包含方案和评估）
        eval_data = self.creative_draft.ai_evaluation
        ai_message = f"""🎉 **完整方案已生成！**

基于你的选择，AI为你生成了以下创作方案：

---

**📚 推荐书名：**
《{self.creative_draft.title}》

**👤 主角设定：**
{self.creative_draft.protagonist}

**⚡ 金手指：**
{self.creative_draft.golden_finger}

**🎬 开局设计：**
{self.creative_draft.opening_design}

**💕 情感线：**
{self.creative_draft.emotion_line}

**✨ 差异化亮点：**
{self.creative_draft.unique_points}

---

**📊 AI 市场化评估：**

• **预计完读率：** {eval_data.get('completion_rate', '15-18%')}
• **首秀通过率：** {eval_data.get('debut_pass_rate', '60-70%')}  
• **风险等级：** {eval_data.get('risk_level', '中等')}
• **差异化评分：** {eval_data.get('differentiation_score', '80')}/100

**💡 优势：**
{eval_data.get('strengths', '• 符合市场主流喜好')}

**⚠️ 风险提示：**
{eval_data.get('risks', '• 需要保持稳定更新')}

**🎯 建议：**
{eval_data.get('suggestions', '• 按此方案直接开始生成')}

---

💡 **下一步：**
你可以在表单中查看和修改这个方案，确认无误后即可开始生成。"""
        
        options = [
            {
                "id": "continue",
                "label": "✅ 查看并编辑方案",
                "description": "在表单中确认和微调方案",
                "style": "primary"
            },
            {
                "id": "back",
                "label": "🔄 返回修改",
                "description": "重新调整设定",
                "style": "secondary"
            }
        ]
        
        round_data = DialogRound(
            round_num=6,
            round_type=DialogRoundType.CONFIRM,
            ai_message=ai_message,
            options=options,
            allow_custom=False
        )
        self.rounds.append(round_data)
        self.current_round = 6
        
        # 生成对话历史
        self.creative_draft.dialog_history = self._generate_dialog_history()
        
        return self._format_round_response(round_data, is_final=True)
    
    def _round_final_confirm(self, prev_choice: str, custom: str = None) -> Dict:
        """第七轮：最终确认（用户点击"查看并编辑方案"后）"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第七轮：最终确认")
        
        # 这一轮只是标记结束，实际表单在前端显示
        return self._finish_dialog()
    
    def _generate_plan_with_ai(self) -> Dict:
        """调用AI生成完整方案"""
        if not self.api_client:
            return self._generate_default_plan()
        
        # 🔥 收集各轮次的自定义输入
        custom_inputs = []
        for round_data in self.rounds:
            if round_data.user_custom_input:
                round_name = {
                    1: "题材类型",
                    2: "主角性格", 
                    3: "金手指",
                    4: "开局设计",
                    5: "情感线"
                }.get(round_data.round_num, f"第{round_data.round_num}轮")
                custom_inputs.append(f"[{round_name}] {round_data.user_custom_input}")
        
        all_custom = "\n".join(custom_inputs) if custom_inputs else "无"
        
        prompt = f"""你是一位资深网文编辑，擅长为番茄小说平台创作爆款作品。

请基于以下设定，生成一个完整的创作方案：

**题材：** {self.genre}
**主角：** {self.creative_draft.protagonist}
**金手指：** {self.creative_draft.golden_finger}
**开局设计：** {self.creative_draft.opening_design}
**情感线：** {self.creative_draft.emotion_line}
**差异化：** {self.creative_draft.unique_points}

**🔥 用户创意修改要求（必须严格遵守）：**
{all_custom}

请根据上述用户的创意修改，生成符合要求的方案。如果用户指定了特殊设定（如"二哈宠物"、"毒舌"等），必须在设定中体现。

请生成（JSON格式）：
{{
    "title": "书名（6-14字，含数字或强烈对比）",
    "opening": "开局设计（100字以内，描述第1章核心冲突）",
    "first_climax": "第一个爽点（第3-5章）",
    "main_plot": "主线走向（50字）"
}}

要求：
1. 严格遵守用户的创意修改要求，不要偏离
2. 书名要符合番茄爆款风格
3. 开局要有强冲突和吸引力
4. 突出用户指定的差异化亮点"""
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="plan_generation",
                user_prompt=prompt,
                temperature=0.8
            )
            
            if response:
                # 尝试解析JSON
                import json
                import re
                # 提取JSON部分
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"AI生成方案失败: {e}")
        
        return self._generate_default_plan()
    
    def _generate_default_plan(self) -> Dict:
        """生成默认方案（AI失败时使用）"""
        protagonist = self.creative_draft.protagonist
        golden_finger = self.creative_draft.golden_finger
        genre_short = self.genre.split('-')[0] if '-' in self.genre else self.genre
        
        # 根据题材类型生成对应的开局场景
        opening_scenarios = {
            "国运": f"主角获得{golden_finger}，代表国家出战，震惊全球",
            "神豪": f"主角获得{golden_finger}，在奢侈品店一掷千金，打脸势利导购",
            "签到": f"主角获得{golden_finger}，在平凡日常中积累超凡实力",
            "奶爸": f"主角获得{golden_finger}，为了保护萌宝展现出超强实力",
            "末日": f"主角获得{golden_finger}，在末日危机中拯救幸存者",
            "诡异": f"主角获得{golden_finger}，在规则怪谈中破解生死谜题",
            "灵气": f"主角觉醒{golden_finger}，在灵气复苏时代引领潮流",
            "御兽": f"主角觉醒{golden_finger}，契约第一只灵兽踏上征途",
            "盗墓": f"主角获得{golden_finger}，下墓探险发现惊天秘密",
            "文娱": f"主角获得{golden_finger}，在娱乐圈一作封神",
        }
        
        # 匹配开局场景
        opening = f"主角获得{golden_finger}，开启逆袭之路"
        for key, scenario in opening_scenarios.items():
            if key in self.genre:
                opening = scenario
                break
        
        # 根据人设和金手指生成默认书名
        if "话痨" in protagonist or "吐槽" in protagonist:
            title = f"绑定吐槽系统后，我在{genre_short}无敌了"
        elif "佛系" in protagonist or "摆烂" in protagonist:
            title = f"摆烂后，我成了{genre_short}最强"
        elif "疯批" in protagonist or "疯狂" in protagonist:
            title = f"疯批主角：{genre_short}规则破坏者"
        elif "冷静" in protagonist or "理智" in protagonist:
            title = f"开局觉醒{golden_finger[:6]}，我靠智商无敌"
        else:
            title = f"开局觉醒{golden_finger[:6]}，我在{genre_short}无敌了"
        
        # 根据题材生成爽点和主线
        if "国运" in self.genre:
            first_climax = "第3章代表国家出战，碾压敌国选手"
            main_plot = "从无名小卒到国家英雄，为国争光"
        elif "神豪" in self.genre:
            first_climax = "第3章一掷千金，打脸曾经看不起自己的人"
            main_plot = "花钱如流水，从穷小子到顶级神豪"
        elif "末日" in self.genre:
            first_climax = "第3章建立安全据点，收留第一批幸存者"
            main_plot = "在末日中建立势力，拯救人类文明"
        elif "诡异" in self.genre:
            first_climax = "第3章破解诡异规则，成功生还"
            main_plot = "探索规则怪谈，揭开诡异真相"
        elif "奶爸" in self.genre:
            first_climax = "第3章为了保护萌宝，展现超强实力"
            main_plot = "带娃升级两不误，成为最强奶爸"
        else:
            first_climax = "第3章打脸反派，展现实力"
            main_plot = "从弱小到最强，一路碾压"
        
        return {
            "title": title,
            "opening": opening,
            "first_climax": first_climax,
            "main_plot": main_plot
        }
    
    def _generate_default_title(self) -> str:
        """生成默认书名"""
        plan = self._generate_default_plan()
        return plan.get("title", "未命名")
    
    def _generate_ai_evaluation(self) -> Dict:
        """调用AI进行自评"""
        if not self.api_client:
            return self._generate_default_evaluation()
        
        prompt = f"""你是一位严格的番茄小说市场评估专家。

请基于以下创意方案进行评估：

**题材：** {self.genre}
**书名：** {self.creative_draft.title}
**主角：** {self.creative_draft.protagonist}
**金手指：** {self.creative_draft.golden_finger}
**差异化：** {self.creative_draft.unique_points}

请输出评估结果（JSON格式）：
{{
    "completion_rate": "预计完读率（如：15-18%）",
    "debut_pass_rate": "首秀通过率（如：60-70%）",
    "risk_level": "风险等级（低/中/高）",
    "differentiation_score": "差异化评分（0-100的数字）",
    "strengths": "优势（3-5条，每条一行，以•开头）",
    "risks": "风险（2-3条，每条一行，以•开头）",
    "suggestions": "优化建议（2-3条，每条一行，以•开头）"
}}

评估标准：
- 完读率：参考同类题材平均水平
- 风险：创新度越高风险越大
- 差异化：与Top100的差异化程度"""
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="evaluation",
                user_prompt=prompt,
                temperature=0.5
            )
            
            if response:
                import json
                import re
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    result = json.loads(json_match.group())
                    # 确保所有字段存在
                    return {
                        "completion_rate": result.get("completion_rate", "15-18%"),
                        "debut_pass_rate": result.get("debut_pass_rate", "60-70%"),
                        "risk_level": result.get("risk_level", "中等"),
                        "differentiation_score": result.get("differentiation_score", 80),
                        "strengths": result.get("strengths", "• 符合市场主流喜好"),
                        "risks": result.get("risks", "• 需要保持稳定更新"),
                        "suggestions": result.get("suggestions", "• 按此方案直接开始生成")
                    }
        except Exception as e:
            logger.error(f"AI评估失败: {e}")
        
        return self._generate_default_evaluation()
    
    def _generate_default_evaluation(self) -> Dict:
        """生成默认评估"""
        return {
            "completion_rate": "15-18%",
            "debut_pass_rate": "60-70%",
            "risk_level": "中等",
            "differentiation_score": 80,
            "strengths": "• 符合市场主流喜好\n• 有明确的差异化定位\n• 情绪节奏设计合理",
            "risks": "• 需要保持稳定更新\n• 前期需要积累读者",
            "suggestions": "• 按此方案直接开始生成\n• 注意黄金三章的质量"
        }
    
    def _generate_unique_points(self) -> str:
        """生成差异化亮点描述"""
        points = []
        
        if "话痨" in self.creative_draft.protagonist:
            points.append("直播变单口相声，用吐槽缓解紧张氛围")
        elif "佛系" in self.creative_draft.protagonist:
            points.append("被迫营业的反差萌，越不想火越火")
        elif "疯批" in self.creative_draft.protagonist:
            points.append(" unpredictable的行为模式，让读者猜不到下一步")
        
        if "记忆" in self.creative_draft.golden_finger:
            points.append("记忆消失的悲剧感与直播时的喜剧效果形成反差")
        elif "身体" in self.creative_draft.golden_finger:
            points.append("英雄迟暮的紧迫感，每一场战斗都可能是最后一场")
        elif "观众" in self.creative_draft.golden_finger:
            points.append("观众互动创造不确定性，弹幕成为剧情变量")
        
        if "妹妹" in self.creative_draft.emotion_line:
            points.append("妹妹是唯一理解他的人，建立深层情感锚点")
        elif "宿敌" in self.creative_draft.emotion_line:
            points.append("亦敌亦友的复杂关系，增加人物关系张力")
        
        return "\n".join([f"• {p}" for p in points]) if points else "• 独特的设定组合"
    
    def _generate_risk_mitigation(self) -> str:
        """生成风险对冲建议"""
        mitigations = []
        
        if "记忆" in self.creative_draft.golden_finger or "身体" in self.creative_draft.golden_finger:
            mitigations.append("每5章安排1章轻松日常，缓解压抑感")
        
        if "话痨" in self.creative_draft.protagonist:
            mitigations.append("30章后减少纯吐槽，增加行动推进")
        
        if "妹妹" in self.creative_draft.emotion_line:
            mitigations.append("前10章快速建立妹妹羁绊，让读者有牵挂")
        
        return "；".join(mitigations) if mitigations else "按常规节奏推进"
    
    def _generate_dialog_history(self) -> List[Dict]:
        """生成对话历史（供AI评估使用）"""
        history = []
        for round_data in self.rounds:
            history.append({
                "role": "ai",
                "content": round_data.ai_message
            })
            if round_data.user_choice:
                user_content = round_data.user_choice
                if round_data.user_custom_input:
                    user_content += f"（自定义：{round_data.user_custom_input}）"
                history.append({
                    "role": "user",
                    "content": user_content
                })
        return history
    
    def _format_round_response(self, round_data: DialogRound, is_final: bool = False) -> Dict:
        """格式化轮次响应"""
        return {
            "session_id": self.session_id,
            "genre": self.genre,
            "round": round_data.round_num,
            "round_type": round_data.round_type.value,
            "ai_message": round_data.ai_message,
            "options": round_data.options,
            "allow_custom": round_data.allow_custom,
            "is_final": is_final,
            "creative_draft": self.creative_draft.to_dict() if is_final else None
        }
    
    def _finish_dialog(self) -> Dict:
        """结束对话，返回最终方案"""
        logger.info(f"[对话打磨 {self.session_id}] 对话结束，返回最终方案")
        
        # 创建结束轮次
        round_data = DialogRound(
            round_num=self.current_round,
            round_type=DialogRoundType.CONFIRM,
            ai_message="对话已结束，最终方案已生成。",
            options=[],
            allow_custom=False
        )
        self.rounds.append(round_data)
        
        return self._format_round_response(round_data, is_final=True)
    
    def go_back(self, target_round: int) -> Dict:
        """
        返回到指定轮次
        
        Args:
            target_round: 目标轮次（1-based）
        """
        if target_round < 1 or target_round >= len(self.rounds):
            return self._format_round_response(self.rounds[-1])
        
        # 截断到目标轮次
        self.rounds = self.rounds[:target_round]
        self.current_round = target_round
        
        # 清除后续的选择记录
        if target_round <= 1:
            self.creative_draft.protagonist_type = ""
        if target_round <= 2:
            self.creative_draft.protagonist = ""
        if target_round <= 3:
            self.creative_draft.golden_finger = ""
            self.creative_draft.golden_finger_type = ""
        if target_round <= 4:
            self.creative_draft.opening_design = ""
        if target_round <= 5:
            self.creative_draft.emotion_line = ""
        
        return self._format_round_response(self.rounds[-1])
    
    def get_creative_draft(self) -> CreativeDraft:
        """获取创意草案"""
        return self.creative_draft
    
    def get_dialog_summary(self) -> str:
        """获取对话摘要"""
        lines = [f"【{self.genre}】对话打磨摘要"]
        for round_data in self.rounds:
            if round_data.user_choice:
                lines.append(f"第{round_data.round_num}轮: {round_data.user_choice}")
        return "\n".join(lines)
    
    def _generate_golden_finger_detail_with_ai(self) -> Dict:
        """
        调用AI生成完整的金手指详细设定
        
        基于用户选择的类型和描述，AI自动生成完整的金手指结构
        """
        if not self.api_client:
            logger.warning(f"[对话打磨 {self.session_id}] API客户端未初始化，使用回退金手指")
            return self._create_fallback_golden_finger()
        
        # 构建基础信息
        base_info = {
            "genre": self.genre,
            "protagonist": self.creative_draft.protagonist,
            "protagonist_type": self.creative_draft.protagonist_type,
            "golden_finger_type": self.creative_draft.golden_finger_type,
            "golden_finger_desc": self.creative_draft.golden_finger,
            "opening_design": self.creative_draft.opening_design,
            "emotion_line": self.creative_draft.emotion_line,
        }
        
        prompt = f"""基于以下信息，生成完整的金手指详细设定。

【题材】{base_info['genre']}
【主角性格】{base_info['protagonist']}（{base_info['protagonist_type']}）
【金手指类型】{base_info['golden_finger_type']}
【用户描述】{base_info['golden_finger_desc']}
【开局设计】{base_info['opening_design']}
【情感线】{base_info['emotion_line']}

请生成完整的金手指设定（标准JSON格式）：
{{
    "basic_info": {{
        "name": "金手指名称（有创意，2-8字）",
        "type": "{base_info['golden_finger_type']}",
        "type_label": "类型标签（带emoji）",
        "concept": "核心概念（50字内，清晰说明机制）"
    }},
    "abilities": {{
        "initial": "初始能力（刚获得时，限制较多）",
        "growth": "成长曲线（前期1-30章/中期31-80章/后期81章+）",
        "max": "最终形态（后期解锁的终极能力）"
    }},
    "restrictions": {{
        "limitations": ["限制条件1", "限制条件2", "限制条件3"],
        "side_effects": ["副作用1", "副作用2"],
        "cooldown": "冷却规则"
    }},
    "applications": {{
        "combat": "战斗应用场景",
        "daily": "日常应用场景",
        "special": {{}}
    }},
    "protagonist_synergy": {{
        "compatibility": "与主角性格的契合度说明",
        "combo_effects": ["联动效果1", "联动效果2"]
    }},
    "plot_role": {{
        "hooks": [
            {{"chapter": 3, "title": "首次使用", "description": "第3章左右的关键剧情"}},
            {{"chapter": 15, "title": "进化/危机", "description": "第15章左右的进化或危机"}},
            {{"chapter": 30, "title": "秘密揭晓", "description": "第30章左右揭晓秘密"}}
        ],
        "twist_potential": "潜在反转（金手指背后可能隐藏的真相）"
    }}
}}

要求：
1. 必须与主角性格【{base_info['protagonist_type']}】形成联动
2. 必须有明确的成长空间（前期弱→后期强）
3. 必须有代价或限制，不能无敌
4. 必须包含3个剧情钩子，对应第3、15、30章"""

        try:
            response = self.api_client.generate_content_with_retry(
                content_type="golden_finger_design",
                user_prompt=prompt,
                temperature=0.8
            )
            
            if response:
                # 解析JSON
                import json
                import re
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    result = json.loads(json_match.group())
                    logger.info(f"[对话打磨 {self.session_id}] AI生成金手指成功: {result.get('basic_info', {}).get('name', '未命名')}")
                    return result
        except Exception as e:
            logger.error(f"[对话打磨 {self.session_id}] AI生成金手指失败: {e}")
        
        # 回退
        return self._create_fallback_golden_finger()
    
    def _create_fallback_golden_finger(self) -> Dict:
        """创建回退金手指设定（AI失败时使用）"""
        return {
            "basic_info": {
                "name": self.creative_draft.golden_finger or "待命名系统",
                "type": self.creative_draft.golden_finger_type or "unknown",
                "type_label": "❓ 待补充",
                "concept": self.creative_draft.golden_finger or "金手指详细设定待补充"
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
                "hooks": [
                    {"chapter": 3, "title": "首次使用", "description": "第3章首次使用金手指"},
                    {"chapter": 15, "title": "能力进化", "description": "第15章金手指进化"},
                    {"chapter": 30, "title": "秘密揭晓", "description": "第30章揭晓金手指秘密"}
                ],
                "twist_potential": "金手指背后的真相待补充"
            },
            "_source": "fallback",
            "_needs_completion": True
        }


# 会话管理器（内存存储，生产环境应使用Redis）
_dialog_sessions: Dict[str, DialogPolishManager] = {}


def create_dialog_session(session_id: str, genre: str, tropes: Dict, api_client=None) -> DialogPolishManager:
    """创建对话打磨会话"""
    manager = DialogPolishManager(genre, tropes, api_client)
    _dialog_sessions[manager.session_id] = manager
    return manager


def get_dialog_session(session_id: str) -> Optional[DialogPolishManager]:
    """获取对话打磨会话"""
    return _dialog_sessions.get(session_id)


def remove_dialog_session(session_id: str):
    """移除对话打磨会话"""
    if session_id in _dialog_sessions:
        del _dialog_sessions[session_id]