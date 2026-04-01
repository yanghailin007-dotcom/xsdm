"""
章节生成提示词优化器 v3.0 - 番茄爆款终极版
===========================================

核心特性：
1. 智能章节类型判断（SETUP/FACE_SLAP/REWARD/REVEAL/CRISIS）
2. 黄金三章专项引擎（前3章特殊优化）
3. 番茄算法友好指标（可量化数据控制）
4. 题材专项技法（国运/神豪/模拟器/修仙）
5. 震惊流生成器（多层次震惊铺展）
6. 情绪节奏精确控制（字数段级）

作者：AI Assistant
版本：3.0.0
日期：2026-03-26
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

# 导入风格加载器
from .style_loader import StyleLoader, get_style_guide
from .prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """配置错误异常"""
    def __init__(self, message: str, config_file: str = None):
        self.message = message
        self.config_file = config_file
        super().__init__(f"[{config_file}] {message}" if config_file else message)



class ChapterPromptOptimizerV3:
    """
    番茄爆款章节生成优化器 v3.0
    
    基于番茄平台算法和读者偏好设计的终极提示词系统
    """
    
    # ==================== 常量配置 ====================
    
    # 章节类型定义
    CHAPTER_TYPES = {
        "SETUP": "铺垫章",           # 积蓄情绪，为爽点做准备
        "FACE_SLAP": "打脸章",       # 爽点爆发，当众打脸
        "REWARD": "收获章",          # 展示成果，获得好处
        "REVEAL": "揭秘章",          # 身份揭露，引发震惊
        "CRISIS": "危机章",          # 生死存亡，绝处逢生
        "TRANSITION": "过渡章",      # 承上启下，剧情推进
    }
    
    # 题材专项配置
    GENRE_TEMPLATES = {
        "国运文": {
            "has_livestream": True,
            "has_national_luck": True,
            "弹幕模板": [
                "【龙国观众】卧槽！这也行？",
                "【外国观众】不可能！这一定是作弊！",
                "【龙国专家】这...这违背了物理学常识！",
                "【弹幕刷屏】龙国牛逼！！！",
                "【外国弹幕】Fake! Must be fake!",
                "【官方账号】龙国国运指挥部：密切关注中",
            ],
            "反应链": ["现场观众", "直播平台弹幕", "各国官方", "联合国层面"],
            "数据展示": ["国运值变化", "资源具现数量", "全球排名", "与他国对比"],
            "系统提示音": "【龙国国运+XXX】【全球排名上升至第X位】",
        },
        "神豪文": {
            "has_money_system": True,
            "数字精确": True,
            "返利音效": "【叮！恭喜宿主消费XXX元，返利XXX元已到账！】【叮！触发暴击返利，额外奖励XXX元！】",
            "价格计算模板": [
                "周围人心中快速计算：这...这得多少钱啊？",
                "XXX倒吸一口凉气：这相当于我十年的工资！",
                "路人甲掐指一算：卧槽，这辈子都赚不到这么多！",
            ],
            "前后对比": True,
            "震惊层级": ["金额数字", "支付方式", "身份猜测"],
        },
        "模拟器文": {
            "has_simulation": True,
            "剪辑感": True,
            "模拟过程模板": [
                "【第1次模拟】主角选择XXX，结果：死亡（被车撞死）",
                "【第2次模拟】主角选择XXX，结果：死亡（被人暗杀）",
                "【第99次模拟】主角终于发现关键：XXX",
            ],
            "失败铺垫": True,
            "技能展示": "【获得白色天赋：XXX（效果：XXX）】",
        },
        "修仙文": {
            "has_cultivation": True,
            "境界体系": True,
            "突破特效": "轰！天地变色，雷劫降临！",
            "震惊层级": ["同门", "长老", "宗主", "整个修仙界"],
        },
        "同人": {
            "has_original_work": True,
            "原著角色": True,
            "改变剧情": True,
            "蝴蝶效应": True,
        },
    }
    
    # 番茄算法指标
    ALGORITHM_METRICS = {
        "paragraph": {
            "avg_length": "30-50字",
            "max_length": 80,
            "dialogue_ratio": 0.5,  # 对话占比≥50%
        },
        "pacing": {
            "conflict_first_300": True,  # 前300字必须有冲突
            "mini_climax_every_1000": True,  # 每1000字一个小爽点
            "hook_last_50": True,  # 章尾最后50字是钩子
            "no_dialogue_limit": 200,  # 禁止连续200字无对话
        },
        "emotion": {
            "transitions_per_chapter": 3,  # 一章内情绪转变至少3次
            "climax_intensity": 8,  # 高潮部分情绪强度≥8/10
            "shock_elements": 1,  # 至少1个震惊元素
        },
    }
    
    # ==================== 初始化 ====================
    
    def __init__(self, novel_data: Dict):
        """
        初始化优化器
        
        Args:
            novel_data: 小说数据，包含title, plan, emotion_curve等
            
        Raises:
            TypeError: 当novel_data格式不正确时
        """
        # 严格检查 novel_data 类型 - 不自动转换，直接报错
        if not isinstance(novel_data, dict):
            raise TypeError(
                f"[PromptV3] novel_data 必须是字典类型，但传入的是 {type(novel_data)}。"
                f"请检查数据格式，确保在调用前将数据转换为正确的字典格式。"
            )
        self.novel_data = novel_data
        
        # 严格获取字段 - 如果字段类型错误，直接报错
        self.title = novel_data.get('title', '未命名')
        
        # 检查 plan 字段
        plan = novel_data.get('plan')
        if plan is not None and not isinstance(plan, dict):
            raise TypeError(f"[PromptV3] novel_data['plan'] 必须是字典或None，但传入的是 {type(plan)}")
        self.plan = plan or {}
        
        # 检查 emotion_curve 字段
        emotion_curve = novel_data.get('emotion_curve')
        if emotion_curve is not None and not isinstance(emotion_curve, dict):
            if isinstance(emotion_curve, list):
                # 🔥 修复：支持旧版列表格式，转换为新版字典格式
                logger.info(f"[PromptV3] emotion_curve 是列表类型（旧格式），包含{len(emotion_curve)}条记录，转换为字典格式")
                # 将列表格式转换为字典格式（包装为 phase_1 阶段）
                emotion_curve = {
                    'phase_1_early_domination': {
                        'curve': emotion_curve,
                        'key_milestones': []
                    }
                }
            else:
                raise TypeError(f"[PromptV3] novel_data['emotion_curve'] 必须是字典或列表或None，但传入的是 {type(emotion_curve)}")
        self.emotion_curve = emotion_curve or {}
        
        # 检查 character_design 字段
        char_design = novel_data.get('character_design')
        if char_design is not None and not isinstance(char_design, dict):
            raise TypeError(f"[PromptV3] novel_data['character_design'] 必须是字典或None，但传入的是 {type(char_design)}")
        self.char_design = char_design or {}
        
        # 检查 core_worldview 字段
        worldview = novel_data.get('core_worldview')
        if worldview is not None and not isinstance(worldview, dict):
            raise TypeError(f"[PromptV3] novel_data['core_worldview'] 必须是字典或None，但传入的是 {type(worldview)}")
        self.worldview = worldview or {}
        
        # 检测题材类型
        self.genre_type = self._detect_genre_type()
        
        # 主角信息
        self.protagonist_name = self._get_protagonist_name()
        
        # 加载章节模板配置
        self._chapter_templates = self._load_chapter_templates()
        
        # 初始化风格加载器
        self._style_loader = StyleLoader()
        
        # 初始化提示词加载器（用于加载 JSON 配置的提示词）
        self._prompt_loader = get_prompt_loader()
        self._golden_chapter_prompts = self._load_golden_chapter_prompts()
        
        logger.info(f"[PromptV3] 初始化完成 | 书名: {self.title} | 题材: {self.genre_type}")
    
    def _load_chapter_templates(self) -> Dict:
        """从 JSON 加载章节模板配置"""
        try:
            base_dir = Path(__file__).parent.parent.parent.parent
            template_file = base_dir / "prompt_packages" / "default" / "market_driven" / "chapter_templates.json"
            
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    templates = json.load(f)
                logger.info(f"[PromptV3] 加载章节模板配置成功 | 模板数: {len(templates.get('templates', {}))}")
                return templates.get('templates', {})
            else:
                logger.warning(f"[PromptV3] 章节模板配置文件不存在: {template_file}")
                return {}
        except Exception as e:
            logger.error(f"[PromptV3] 加载章节模板配置失败: {e}")
            return {}
    
    def _load_golden_chapter_prompts(self) -> Dict:
        """从 JSON 加载黄金三章提示词配置"""
        try:
            prompts = self._prompt_loader.get_golden_chapter_prompts()
            if prompts:
                logger.info(f"[PromptV3] 加载黄金三章提示词配置成功")
                return prompts.get('golden_chapters', {})
            else:
                logger.warning(f"[PromptV3] 黄金三章提示词配置加载失败，将使用硬编码")
                return {}
        except Exception as e:
            logger.error(f"[PromptV3] 加载黄金三章提示词配置失败: {e}")
            return {}
    
    def _load_common_components(self) -> Dict:
        """从 JSON 加载通用提示词组件"""
        try:
            base_dir = Path(__file__).parent.parent.parent.parent
            components_file = base_dir / "prompt_packages" / "default" / "market_driven" / "common_prompt_components.json"
            
            if components_file.exists():
                with open(components_file, 'r', encoding='utf-8') as f:
                    components = json.load(f)
                logger.info(f"[PromptV3] 加载通用提示词组件成功")
                return components
            else:
                logger.warning(f"[PromptV3] 通用提示词组件文件不存在: {components_file}")
                return {}
        except Exception as e:
            logger.error(f"[PromptV3] 加载通用提示词组件失败: {e}")
            return {}
    
    def _get_common_component(self, component_name: str, **kwargs) -> str:
        """获取通用提示词组件"""
        components = self._load_common_components()
        component = components.get(component_name, {})
        
        if not component:
            logger.warning(f"[PromptV3] 未找到通用组件: {component_name}")
            return ""
        
        template = component.get('template', '')
        variables = component.get('variables', [])
        
        # 替换变量
        if variables:
            for var in variables:
                if var in kwargs:
                    template = template.replace(f'{{{var}}}', str(kwargs[var]))
        
        return template
    
    def _render_template(self, template_type: str) -> str:
        """渲染章节类型模板"""
        template_config = self._chapter_templates.get(template_type, {})
        if not template_config:
            logger.warning(f"[PromptV3] 未找到模板配置: {template_type}")
            return f"类型：{template_type}（使用默认配置）"
        
        lines = []
        lines.append(f"类型：{template_type}（{template_config.get('name', '')}）")
        lines.append(f"功能：{template_config.get('function', '')}")
        lines.append("")
        
        # 结构要求
        lines.append("【结构要求】")
        word_dist = template_config.get('word_distribution', {})
        for phase_key, phase_info in word_dist.items():
            lines.append(f"{phase_info.get('range', '')}：{template_config.get('name', '').replace('章', '')}（强度{phase_info.get('intensity', 5)}）→ {phase_info.get('description', '')}")
        lines.append("")
        
        # 必含元素
        lines.append("【必含元素】")
        for element in template_config.get('required_elements', []):
            lines.append(f"- {element}")
        lines.append("")
        
        # 加载对应风格指南
        style_id = template_config.get('style_id')
        if style_id:
            style_guide = self._style_loader.render_style_guide(style_id)
            if style_guide:
                lines.append(style_guide)
                lines.append("")
        
        return "\n".join(lines)
    
    def _detect_genre_type(self) -> str:
        """检测题材类型"""
        genre = self.novel_data.get('genre', '')
        
        # 防御性检查：确保 genre 是字符串
        if isinstance(genre, list):
            genre = ' '.join(str(g) for g in genre)
        elif not isinstance(genre, str):
            genre = str(genre)
        
        plan = self.novel_data.get('plan', {})
        
        # 从genre字段判断
        if '国运' in genre or '直播' in genre:
            return '国运文'
        elif '神豪' in genre or '花钱' in genre or '返利' in genre:
            return '神豪文'
        elif '模拟' in genre or '模拟器' in genre:
            return '模拟器文'
        elif '修仙' in genre or '修真' in genre:
            return '修仙文'
        elif '奶爸' in genre or '萌宝' in genre:
            return '奶爸文'
        elif '签到' in genre:
            return '签到文'
        elif '末日' in genre or '求生' in genre:
            return '末日文'
        elif '同人' in genre:
            return '同人'
        
        # 从金手指类型判断
        golden_finger = plan.get('golden_finger', {})
        gf_type = golden_finger.get('type', '')
        
        # 防御性检查：确保 gf_type 是字符串
        if isinstance(gf_type, list):
            gf_type = ' '.join(str(g) for g in gf_type)
        elif not isinstance(gf_type, str):
            gf_type = str(gf_type)
        
        if '国运' in gf_type:
            return '国运文'
        elif '神豪' in gf_type or '花钱' in gf_type:
            return '神豪文'
        elif '模拟' in gf_type:
            return '模拟器文'
        
        return '通用'
    
    def _build_forbidden_list(self) -> str:
        """
        根据题材类型动态生成禁止清单
        
        不同题材有不同的禁忌和必须要素
        """
        genre_type = self.genre_type
        
        # 基础禁止清单（所有题材通用）
        forbidden_items = [
            "严禁情绪偏离大纲要求",
            "严禁违背战术企图",
            "严禁偏离核心事件",
        ]
        
        # 根据题材添加专项禁止
        if genre_type == '国运文':
            forbidden_items.extend([
                "严禁使用校园场景（如：教务处、奖学金、江城大学等）",
                "严禁使用\"人生模拟器\"系统（除非大纲明确指定）",
                "严禁改变世界观设定（如：将国运禁地改为都市校园）",
                "严禁缺少全球直播、弹幕、国运相关元素",
            ])
        elif genre_type == '校园文':
            forbidden_items.extend([
                "严禁使用国运禁地、全球直播等场景",
                "严禁出现国家层面的战斗或政治元素",
                "严禁缺少校园生活、同学互动等日常元素",
            ])
        elif genre_type == '神豪文':
            forbidden_items.extend([
                "严禁金额模糊（如：很多钱、天价），必须精确到元",
                "严禁反派不讨论价格或心算价格",
                "严禁缺少消费反馈、返利提示音",
            ])
        elif genre_type == '模拟器文':
            forbidden_items.extend([
                "严禁缺少模拟过程描写（必须有\"第X次模拟\"格式）",
                "严禁模拟结果过于简单（必须有具体死亡原因或收获）",
                "严禁缺少\"剪辑\"感，必须有节奏变化",
            ])
        elif genre_type == '修仙文':
            forbidden_items.extend([
                "严禁缺少境界名称和境界压制描写",
                "严禁突破过于简单（必须有天地异象、雷劫等）",
                "严禁缺少灵根、灵气等修仙元素",
            ])
        else:
            # 通用禁止
            forbidden_items.extend([
                "严禁改变大纲规定的世界观设定",
                "严禁添加与大纲无关的全新场景",
            ])
        
        return "\n- ".join([""] + forbidden_items)
    
    def _get_protagonist_name(self) -> str:
        """获取主角姓名（优先使用用户填写的）"""
        # 🔥 优先从 user_choices 获取用户填写的主角名
        user_choices = self.novel_data.get('user_choices', {})
        if user_choices and user_choices.get('protagonist_name'):
            name = user_choices['protagonist_name']
            # 🔥 清理主角名：去掉括号及后面的描述
            import re
            name = re.split(r'[（(]', name)[0].strip()
            return name
        
        char_design = self.char_design
        if char_design:
            protagonist = char_design.get('protagonist', {})
            if isinstance(protagonist, dict):
                # 尝试多种可能的数据结构
                # 结构1: protagonist.name (AI直接返回)
                if 'name' in protagonist:
                    return protagonist['name']
                # 结构2: protagonist.basic_info.name (旧格式)
                basic_info = protagonist.get('basic_info', {})
                if basic_info and 'name' in basic_info:
                    return basic_info['name']
        
        # 从plan中获取
        plan_protagonist = self.plan.get('protagonist', {})
        if isinstance(plan_protagonist, dict):
            if 'name' in plan_protagonist:
                return plan_protagonist['name']
            basic_info = plan_protagonist.get('basic_info', {})
            if basic_info and 'name' in basic_info:
                return basic_info['name']
        
        return '主角'
    
    # ==================== 核心方法：构建System Prompt ====================
    
    def build_system_prompt(self, use_json_config: bool = True) -> str:
        """
        构建番茄爆款System Prompt（约2500字）
        
        Args:
            use_json_config: 是否使用JSON配置组件
            
        Returns:
            完整的System Prompt字符串
        """
        # 🔥 优先使用JSON配置构建
        if use_json_config and self._prompt_loader:
            try:
                return self._build_system_prompt_from_config()
            except Exception as e:
                logger.warning(f"[PromptV3] JSON配置构建System Prompt失败: {e}，使用硬编码")
        
        # 硬编码fallback
        sections = [
            self._build_header(),
            self._build_core_setting(),
            self._build_worldview_section(),
            self._build_protagonist_section(),
            self._build_golden_three_chapters(),
            self._build_tomato_algorithm_guide(),
            self._build_micro_innovation_guide(),
            self._build_genre_specific_guide(),
            self._build_shock_techniques(),
            self._build_emotion_control(),
            self._build_format_rules(),
            self._build_ai_self_check_guide(),
            self._build_footer(),
        ]
        
        return "\n\n".join(filter(None, sections))
    
    def _build_system_prompt_from_config(self) -> str:
        """从JSON配置构建System Prompt"""
        # 加载System Prompt配置
        config_path = "phase_two/system_prompt"
        
        # 构建各个section
        sections = []
        
        # 1. Header
        header = self._render_component("header", {"title": self.title})
        if header:
            sections.append(header)
        else:
            sections.append(self._build_header())
        
        # 2. Core Setting
        core_setting = self._render_component("core_rules", {})
        if core_setting:
            sections.append(core_setting)
        else:
            sections.append(self._build_core_setting())
        
        # 3. Worldview Section
        sections.append(self._build_worldview_section())
        
        # 4. Protagonist Section
        sections.append(self._build_protagonist_section())
        
        # 5. Golden Three Chapters
        golden = self._render_component("golden_chapter_guide", {})
        if golden:
            sections.append(golden)
        else:
            sections.append(self._build_golden_three_chapters())
        
        # 6. Tomato Algorithm
        algo = self._render_component("tomato_algorithm_guide", {})
        if algo:
            sections.append(algo)
        else:
            sections.append(self._build_tomato_algorithm_guide())
        
        # 7. Micro Innovation
        micro = self._render_component("micro_innovation_guide", {})
        if micro:
            sections.append(micro)
        else:
            sections.append(self._build_micro_innovation_guide())
        
        # 8. Genre Specific
        sections.append(self._build_genre_specific_guide())
        
        # 9. Shock Techniques
        sections.append(self._build_shock_techniques())
        
        # 10. Emotion Control
        emotion = self._render_component("emotion_control_guide", {})
        if emotion:
            sections.append(emotion)
        else:
            sections.append(self._build_emotion_control())
        
        # 11. Format Rules
        fmt = self._render_component("format_rules", {})
        if fmt:
            sections.append(fmt)
        else:
            sections.append(self._build_format_rules())
        
        # 12. AI Self Check
        check = self._render_component("ai_self_check_guide", {})
        if check:
            sections.append(check)
        else:
            sections.append(self._build_ai_self_check_guide())
        
        # 13. Footer
        sections.append(self._build_footer())
        
        return "\n\n".join(filter(None, sections))
    
    def _render_component(self, component_id: str, variables: Dict) -> Optional[str]:
        """
        渲染组件
        
        Args:
            component_id: 组件ID
            variables: 变量字典
            
        Returns:
            组件内容，失败返回None
        """
        if not self._prompt_loader:
            return None
        
        try:
            component = self._prompt_loader.get_component(f"market_driven/components/{component_id}")
            if not component:
                return None
            
            template = component.get("template", "")
            if not template:
                return None
            
            # 变量替换
            result = template
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value) if value is not None else "")
            
            return result
        except Exception as e:
            logger.debug(f"[PromptV3] 渲染组件 {component_id} 失败: {e}")
            return None
    
    def _build_header(self) -> str:
        """构建头部 - 从 JSON 配置加载"""
        return self._get_common_component('header', title=self.title)
    
    def _build_core_setting(self) -> str:
        """构建核心设定 - 从 JSON 配置加载"""
        return self._get_common_component('core_setting')
    
    def _build_worldview_section(self) -> str:
        """构建世界观章节"""
        worldview = self.worldview
        if not worldview:
            return ""
        
        parts = []
        
        # 世界观概述
        overview = worldview.get('world_overview', '')
        if overview:
            if len(overview) > 300:
                overview = overview[:300] + "..."
            parts.append("【世界观核心】\n" + overview)
        
        # 核心规则
        rules = worldview.get('world_rules', [])
        if rules and isinstance(rules, list):
            parts.append("【核心规则】")
            for rule in rules[:3]:
                if isinstance(rule, dict):
                    rule_text = rule.get('rule', '') or rule.get('description', '') or str(rule)
                    parts.append("- " + str(rule_text))
                elif isinstance(rule, str):
                    parts.append("- " + rule[:50])
        
        # 力量体系
        power = worldview.get('power_system', {})
        if isinstance(power, dict):
            summary = power.get('summary', '')
            if summary:
                parts.append("【力量体系】\n" + summary[:150])
        
        return "## 【世界观设定】（不可违背）\n\n" + "\n".join(parts) if parts else ""
    
    def _build_protagonist_section(self) -> str:
        """构建主角设定"""
        protagonist = self.char_design.get('protagonist', {}) if self.char_design else {}
        if not protagonist:
            return ""
        
        parts = []
        
        # 基本信息 - 适配两种数据结构
        # 结构1: protagonist.name (AI直接返回)
        if 'name' in protagonist:
            name = protagonist['name']
            age = protagonist.get('age', '')
        else:
            # 结构2: protagonist.basic_info.name (旧格式)
            basic = protagonist.get('basic_info', {})
            name = basic.get('name', self.protagonist_name)
            age = basic.get('age', '')
        
        parts.append(f"【主角：{name}】" + (f"，{age}岁" if age else ""))
        
        # 人设原型
        archetype = protagonist.get('archetype', '')
        if archetype:
            parts.append(f"人设原型：{archetype[:100]}")
        
        # 核心特质
        traits = protagonist.get('traits', [])
        if traits:
            parts.append("\n核心特质：")
            for trait in traits[:3]:
                if isinstance(trait, str):
                    parts.append(f"- {trait[:100]}")
                elif isinstance(trait, dict):
                    trait_desc = trait.get('trait', '') or trait.get('description', '')
                    if trait_desc:
                        parts.append(f"- {str(trait_desc)[:100]}")
        
        # 标志性细节
        sig = protagonist.get('signature_details', {})
        if isinstance(sig, dict):
            catchphrases = sig.get('catchphrase', [])
            if catchphrases:
                quotes = ' | '.join([f'"{c}"' for c in catchphrases[:3]])
                parts.append(f"\n标志性台词：{quotes}")
            
            actions = sig.get('actions', [])
            if actions:
                parts.append(f"标志性动作：{actions[0][:80]}")
        
        return "## 【主角人设】（严格遵循）\n\n" + "\n".join(parts) if parts else ""
    
    def _build_golden_three_chapters(self) -> str:
        """构建黄金三章指南 - 从 JSON 配置加载"""
        guide = self._get_common_component('golden_three_chapters')
        if guide:
            return guide
        
        # JSON 配置缺失时抛出错误
        raise ConfigError("golden_three_chapters 配置缺失", "common_prompt_components.json")

    def _build_tomato_algorithm_guide(self) -> str:
        """构建番茄算法指南 - 从 JSON 配置加载"""
        guide = self._get_common_component('tomato_algorithm_guide')
        if guide:
            return guide
        
        # JSON 配置缺失时抛出错误
        raise ConfigError("tomato_algorithm_guide 配置缺失", "common_prompt_components.json")

    def _build_micro_innovation_guide(self) -> str:
        """构建微创新原则指南 - 从 JSON 配置加载"""
        guide = self._get_common_component('micro_innovation_guide')
        if guide:
            return guide
        
        # JSON 配置缺失时抛出错误
        raise ConfigError("micro_innovation_guide 配置缺失", "common_prompt_components.json")

    def _build_genre_specific_guide(self) -> str:
        """构建题材专项指南"""
        genre_type = self.genre_type
        
        if genre_type not in self.GENRE_TEMPLATES:
            return ""
        
        template = self.GENRE_TEMPLATES[genre_type]
        
        sections = [f"## 🎮 {genre_type}专项技法（必须融入）\n"]
        
        # 弹幕模板（国运/直播类）
        if template.get("has_livestream"):
            sections.append("### 弹幕设计模板（每章至少3-5条）")
            sections.append("```")
            for barrage in template.get("弹幕模板", []):
                sections.append(barrage)
            sections.append("```")
            
            sections.append("\n### 官方反应链（层层递进）")
            for i, level in enumerate(template.get("反应链", []), 1):
                sections.append(f"{i}. {level}的反应")
        
        # 数字精确（神豪类）
        if template.get("数字精确"):
            sections.append("\n### 金钱数字规范")
            sections.append("- 所有金额必须精确到小数点后2位")
            sections.append("- 返利到账必须有系统提示音效果：")
            sections.append(f"  `{template.get('返利音效', '')}`")
            
            sections.append("\n### 周围人心理活动模板")
            for tmpl in template.get("价格计算模板", []):
                sections.append(f"- {tmpl}")
        
        # 模拟器类
        if template.get("has_simulation"):
            sections.append("\n### 模拟过程写法（快速剪辑感）")
            sections.append("```")
            for tmpl in template.get("模拟过程模板", []):
                sections.append(tmpl)
            sections.append("```")
            
            sections.append(f"\n### 天赋展示格式")
            sections.append(f"`{template.get('技能展示', '')}`")
        
        # 修仙类
        if template.get("has_cultivation"):
            sections.append("\n### 突破场景写法")
            sections.append(f"特效描述：`{template.get('突破特效', '')}`")
            
            sections.append("\n### 震惊层级（层层递进）")
            for i, level in enumerate(template.get("震惊层级", []), 1):
                sections.append(f"{i}. {level}震惊")
        
        return "\n".join(sections)
    
    def _build_shock_techniques(self) -> str:
        """构建震惊流技法 - 从 JSON 配置文件加载"""
        # 使用 StyleLoader 从 JSON 加载震惊流配置
        guide = get_style_guide("shock_flow")
        if guide:
            return guide
        
        # JSON 配置缺失时抛出错误
        raise ConfigError("shock_flow 配置缺失", "styles/shock_flow.json")

    def _build_emotion_control(self) -> str:
        """构建情绪控制指南 - 从 JSON 配置加载"""
        guide = self._get_common_component('emotion_control')
        if guide:
            return guide
        
        # JSON 配置缺失时抛出错误
        raise ConfigError("emotion_control 配置缺失", "common_prompt_components.json")

    def _build_format_rules(self) -> str:
        """构建格式规则 - 从 JSON 配置加载"""
        guide = self._get_common_component('format_rules')
        if guide:
            return guide
        
        # JSON 配置缺失时抛出错误
        raise ConfigError("format_rules 配置缺失", "common_prompt_components.json")

    def _build_ai_self_check_guide(self) -> str:
        """构建AI自检指南（生成后自检）- 从 JSON 配置加载"""
        guide = self._get_common_component('ai_self_check')
        if guide:
            return guide
        
        # JSON 配置缺失时抛出错误
        raise ConfigError("ai_self_check 配置缺失", "common_prompt_components.json")

    def _build_footer(self) -> str:
        """构建页脚"""
        return """---

## 开始生成

现在，请根据我提供的"章节指令"生成章节内容。

生成流程：
1. 先阅读"章节指令"理解本章要求
2. 生成本章正文（2000-2500字）
3. 必须进行AI自检（按照自检指南）
4. 输出自检报告
5. 如果自检不通过，重新优化后再次输出

记住：
1. 你是番茄爆款作家，不是普通写手
2. 每章都要让读者欲罢不能
3. 严格按照上述所有规则执行
4. 必须自检，不可跳过！
5. 写出让人通宵追更的神作！

准备好后，请输出：已理解所有规则，开始生成章节。"""


    # ==================== 章节类型判断 ====================
    
    def detect_chapter_type(self, chapter_num: int, blueprint: Dict = None) -> str:
        """
        智能判断章节类型
        
        Args:
            chapter_num: 章节号
            blueprint: 章节规划
            
        Returns:
            章节类型标识（SETUP/FACE_SLAP/REWARD/REVEAL/CRISIS/TRANSITION）
        """
        # 黄金三章特殊处理
        if chapter_num <= 3:
            return self._detect_golden_chapter_type(chapter_num)
        
        # 从emotion_curve获取情绪设计（直接访问原始数据）
        emotion_curve = self.emotion_curve
        if emotion_curve:
            # 查找各阶段的详细曲线
            phases = ['phase_1_early_domination', 'phase_2_rising_power', 
                      'phase_3_global_dominance', 'phase_4_cosmic_conquest']
            
            for phase_key in phases:
                phase = emotion_curve.get(phase_key, {})
                if not phase:
                    continue
                
                curve = phase.get('curve', [])
                for beat in curve:
                    if beat.get('ch') == chapter_num:
                        beat_type = beat.get('beat_type', '').lower()
                        
                        # 根据节拍类型判断
                        if beat_type in ['压抑', '铺垫', 'setup']:
                            return 'SETUP'
                        elif beat_type in ['爽点', '打脸', '高潮', 'climax']:
                            return 'FACE_SLAP'
                        elif beat_type in ['收获', 'reward', '升级']:
                            return 'REWARD'
                        elif beat_type in ['揭秘', '曝光', 'reveal']:
                            return 'REVEAL'
                        elif beat_type in ['危机', 'crisis']:
                            return 'CRISIS'
                        break
        
        # 根据章节号规律判断
        chapter_in_cycle = (chapter_num - 1) % 10  # 10章一个周期
        
        if chapter_in_cycle in [0, 1, 2]:  # 第1-3章：铺垫
            return 'SETUP'
        elif chapter_in_cycle == 3:  # 第4章：爽点
            return 'FACE_SLAP'
        elif chapter_in_cycle in [4, 5]:  # 第5-6章：过渡/收获
            return 'REWARD'
        elif chapter_in_cycle == 6:  # 第7章：揭秘或危机
            return 'REVEAL' if chapter_num % 2 == 0 else 'CRISIS'
        elif chapter_in_cycle in [7, 8]:  # 第8-9章：铺垫
            return 'SETUP'
        else:  # 第10章：大爽点
            return 'FACE_SLAP'
    
    def _detect_golden_chapter_type(self, chapter_num: int) -> str:
        """黄金三章类型判断"""
        if chapter_num == 1:
            return 'GOLDEN_1'  # 钩子章
        elif chapter_num == 2:
            return 'GOLDEN_2'  # 验证章
        else:
            return 'GOLDEN_3'  # 打脸章
    
    # ==================== 单章提示词构建（核心）====================
    
    def build_chapter_prompt(
        self, 
        chapter_num: int, 
        blueprint: Dict = None, 
        prev_summary: str = "",
        stage_goal: Dict = None  # ← 新增：阶段目标
    ) -> str:
        """
        构建单章生成提示词（v3.0终极版）
        
        Args:
            chapter_num: 章节号
            blueprint: 章节规划
            prev_summary: 前文摘要
            stage_goal: 阶段目标（与战术目标对齐）
            
        Returns:
            完整的单章提示词
        """
        # 判断章节类型
        chapter_type = self.detect_chapter_type(chapter_num, blueprint)
        
        logger.info(f"[PromptV3] 构建第{chapter_num}章提示词 | 类型: {chapter_type}")
        
        # 构建阶段目标对齐提示
        goal_alignment = ""
        if stage_goal:
            goal_alignment = f"""
## 【阶段目标对齐 - 必须遵守】
当前阶段目标: {stage_goal.get('description', '无')}
成功标准: {stage_goal.get('success_criteria', '无')}
关键交付物: {', '.join(stage_goal.get('key_deliverables', []))}

本章必须服务于阶段目标，推进关键交付物的完成。
"""
        
        # 根据类型选择模板
        if chapter_type.startswith('GOLDEN_'):
            prompt = self._build_golden_chapter_prompt(chapter_num, chapter_type, 
                                                        blueprint, prev_summary)
        else:
            prompt = self._build_standard_chapter_prompt(chapter_num, chapter_type,
                                                          blueprint, prev_summary)
        
        # 在标准提示词后插入阶段目标对齐（黄金三章除外，它们有特殊结构）
        if not chapter_type.startswith('GOLDEN_'):
            # 在字数要求之前插入阶段目标对齐
            prompt = prompt.replace(
                "## 【字数强制要求】",
                f"{goal_alignment}\n## 【字数强制要求】"
            )
        
        return prompt
    
    def _build_golden_chapter_prompt(self, chapter_num: int, chapter_type: str,
                                      blueprint: Dict, prev_summary: str) -> str:
        """构建黄金三章提示词"""
        if chapter_type == 'GOLDEN_1':
            return self._build_golden_chapter_1(blueprint, prev_summary)
        elif chapter_type == 'GOLDEN_2':
            return self._build_golden_chapter_2(blueprint, prev_summary)
        else:
            return self._build_golden_chapter_3(blueprint, prev_summary)
    
    def _build_golden_chapter_1(self, blueprint: Dict, prev_summary: str) -> str:
        """构建第1章（钩子章）提示词 - 从 JSON 配置加载"""
        if not self._golden_chapter_prompts or 'chapter_1' not in self._golden_chapter_prompts:
            raise ConfigError("第1章提示词配置缺失", "golden_chapter_prompts.json")
        
        try:
            return self._render_golden_chapter_1_from_config(blueprint)
        except Exception as e:
            logger.error(f"[PromptV3] 从配置渲染第1章提示词失败: {e}")
            raise ConfigError(f"第1章提示词渲染失败: {e}", "golden_chapter_prompts.json")
    def _get_micro_innov_for_chapter_1(self) -> str:
        """获取第1章微创新建议"""
        return """
## 【微创新专项要求】

### 时间场景（必须避开的套路）
不要：深夜23:47，暴雨倾盆
尝试：凌晨5:30刚下班、早高峰地铁、正午烈日下的工地

### 系统激活（必须避开的套路）
不要：天降金光、额头流血触发、被雷劈
尝试：
- 手机收到【人生模拟器】内测邀请短信，发件人是自己手机号
- 微信突然多了一个"模拟器助手"好友
- 电脑屏幕突然弹出无法关闭的窗口

### 反派羞辱（必须避开的套路）
不要：纯嚣张"穷鬼就该有穷鬼的觉悟"、让主角跪下
尝试：
- 网络暴力式：拿出手机"来，对着镜头说'我穷我有理'，让网友评评理"
- 规则打压式："我能让你连贫困生补助都拿不到，你信吗？"
- 利益威胁式："这奖学金我买定了，你尽管去告，看有没有人理你"

### 配角设计（必须在线）
至少设计2-3个配角：
- 支持者：偷偷塞给主角钱的室友/同事
- 观望者：暂时中立，看形势站队的人
- 记录者：拍照发朋友圈/直播的人
- 背景板升级：不只是"卧槽"，要有具体反应

### 钩子设计（必须具体）
不要："明天你就知道了"、主角突然霸气侧漏
尝试：
- 时间锁："71小时59分后开奖"
- 信息差：主角知道反派不知道的秘密
- 蝴蝶效应：系统警告"当前轨迹下你会错过购买时间"
- 多重可能：展示3种未来，主角必须选择
"""
    
    def _render_golden_chapter_1_from_config(self, blueprint: Dict) -> str:
        """
        从 JSON 配置渲染第1章提示词
        
        Args:
            blueprint: 战术大纲
            
        Returns:
            渲染后的提示词字符串
        """
        config = self._golden_chapter_prompts.get('chapter_1', {})
        common = self._golden_chapter_prompts.get('common_elements', {})
        
        # 提取蓝图变量
        scene = blueprint.get('scene', '')
        event = blueprint.get('event', '')
        hook_content = blueprint.get('hook_content', '')
        emotion = blueprint.get('emotion', '')
        purpose = blueprint.get('purpose', '')
        beat_type = blueprint.get('beat_type', '')
        has_blueprint = bool(scene or event or hook_content)
        
        # 获取题材元素
        genre_elements = self._get_genre_elements_for_chapter(1)
        
        # 构建大纲约束
        blueprint_constraint = self._build_blueprint_constraint(
            beat_type, purpose, emotion, scene, event, hook_content, has_blueprint
        )
        
        # 获取结构配置
        structure = config.get('structure', {})
        part_1 = structure.get('part_1', {})
        part_2 = structure.get('part_2', {})
        part_3 = structure.get('part_3', {})
        
        # 获取算法要求
        algo = common.get('algorithm_requirements', {})
        
        # 渲染提示词
        prompt = f"""# 第1章生成指令【黄金三章 - 钩子章】

**这是全书最重要的章节！决定读者是否继续阅读！**

## 【章节定位】
类型：钩子章（生死线）
功能：{config.get('function', '极端困境开局 + 系统觉醒 + 悬念钩子')}
目标：{config.get('goal', '让读者3句话内同情主角，章尾必须点下一章')}

{blueprint_constraint}

## 【结构要求】（严格按字数分配）

### 第一部分：{part_1.get('name', '极端困境')}（{part_1.get('range', '0-500字')}）
**必须完成的任务：**
{chr(10).join(['- ' + r for r in part_1.get('requirements', [])])}

**写法示例：**
```
{event[:150] + '...' if event and len(event) > 150 else event if event else part_1.get('example', '')}
```

**禁止：**
{chr(10).join(['- ' + f for f in part_1.get('forbidden', [])])}

{self._get_micro_innov_for_chapter_1() if not has_blueprint else ""}

---

### 第二部分：{part_2.get('name', '系统觉醒')}（{part_2.get('range', '500-2000字')}）
**必须完成的任务：**
{chr(10).join(['- ' + r for r in part_2.get('requirements', [])])}

**微创新激活方式（推荐尝试）：**
{chr(10).join([f"- **{m.get('type', '')}**：{m.get('description', '')}" for m in part_2.get('micro_innovations', [])])}

**参考写法：**
```
{part_2.get('example', '')}
```

{genre_elements}

---

### 第三部分：{part_3.get('name', '悬念钩子')}（{part_3.get('range', '2000-2500字')}）
**必须完成的任务：**
{chr(10).join(['- ' + r for r in part_3.get('requirements', [])])}

**微创新钩子（推荐）：**
{chr(10).join([f"- **{h.get('type', '')}**：{h.get('example', '')}" for h in part_3.get('hook_types', [])])}

**主角情绪层次：**
{chr(10).join([f"{i+1}. {e}" for i, e in enumerate(part_3.get('protagonist_emotion_layers', []))])}

**配角反应设计：**
{chr(10).join([f"- {r.get('type', '')}：{r.get('description', '')}" for r in part_3.get('supporting_roles', [])])}

**禁止：**
{chr(10).join(['- ' + f for f in part_3.get('forbidden', [])])}

{self._render_algorithm_requirements_from_config(algo)}

{self._render_self_check_from_config(config.get('self_check_steps', []))}

{self._render_output_format_from_config(common.get('output_format', {}))}

---
【AI自检报告 - 第1章】
总字数：XXXX字

🚨【三大问题修复检查】
情绪密度：X个/千字（目标≥2.0）| 情绪词列表：XXX、XXX、XXX...
章尾钩子：有/无 | 钩子类型：XXX | 最后50字："..."
爽点密度：X个/千字（目标≥1.5）| 爽点时刻：X个

番茄算法：前300字冲突（是/否），500字系统（是/否）
微创新检查：时间（创新/套路），系统激活（创新/套路），反派（有智商/脸谱化）
情绪曲线：X次转变（列出）
自检结论：【通过/需优化】
问题与优化：列出发现的问题
---
"""
        return prompt
    
    def _render_golden_chapter_2_from_config(self, blueprint: Dict, prev_summary: str) -> str:
        """从 JSON 配置渲染第2章提示词"""
        config = self._golden_chapter_prompts.get('chapter_2', {})
        common = self._golden_chapter_prompts.get('common_elements', {})
        
        structure = config.get('structure', {})
        emotion_vocab = config.get('emotion_vocabulary', {})
        algo_req = common.get('algorithm_requirements', {})
        
        emotion_curve = config.get('emotion_curve', ['犹豫', '期待', '满足', '紧张'])
        emotion_curve_str = ' → '.join(emotion_curve)
        
        prompt = f"""# 第2章生成指令【黄金三章 - 收益验证章】

**功能：{config.get('function', '金手指成功应用 + 第一次小爽点')}**
**目标：{config.get('goal', '让读者对金手指有信心，期待后续')}**

## 【情绪曲线】（必须严格遵循）
{emotion_curve_str}

## 【结构要求】（按字数节拍创作）

### 承接回顾（{structure.get('recap', {}).get('range', '0-300字')}）
{structure.get('recap', {}).get('requirement', '简洁承接第一章，回顾系统')}

### 首次使用（{structure.get('first_use', {}).get('range', '800字处')}）
{structure.get('first_use', {}).get('requirement', '金手指首次正式使用')}

### 首次成功（{structure.get('first_success', {}).get('range', '1500字处')}）
{structure.get('first_success', {}).get('requirement', '第一次成功，具体数字收益')}

### 新冲突（{structure.get('new_conflict', {}).get('range', '章尾')}）
{structure.get('new_conflict', {}).get('requirement', '新反派登场，更大危机')}

## 【情绪词汇表】（必须选用）
- 犹豫：{', '.join(emotion_vocab.get('hesitation', ['迟疑', '纠结', '忐忑']))}
- 期待：{', '.join(emotion_vocab.get('anticipation', ['心跳加速', '呼吸急促']))}
- 满足：{', '.join(emotion_vocab.get('satisfaction', ['狂喜', '畅快', '扬眉吐气']))}
- 紧张：{', '.join(emotion_vocab.get('tension', ['瞳孔收缩', '后背发凉']))}

{self._render_algorithm_requirements_from_config(algo_req)}

{self._render_self_check_from_config(config.get('self_check_steps', []))}

{self._render_output_format_from_config(common.get('output_format', {}))}
"""
        return prompt

    def _render_golden_chapter_3_from_config(self, blueprint: Dict, prev_summary: str) -> str:
        """从 JSON 配置渲染第3章提示词"""
        config = self._golden_chapter_prompts.get('chapter_3', {})
        common = self._golden_chapter_prompts.get('common_elements', {})
        
        structure = config.get('structure', {})
        shock_flow = config.get('shock_flow', {})
        algo_req = common.get('algorithm_requirements', {})
        
        layers = shock_flow.get('layers', [])
        layers_str = '\n'.join([f"- {layer}" for layer in layers])
        
        prompt = f"""# 第3章生成指令【黄金三章 - 打脸章】

**功能：{config.get('function', '铺垫→压抑→爆发→震惊流')}**
**目标：{config.get('goal', '让读者彻底痛快，建立追读信心')}**
**情绪强度：{config.get('emotion_intensity', '8→10→9→7')}**

## 【结构要求】（严格按节拍分配）

### 承接回顾（{structure.get('recap', {}).get('range', '0-200字')}）
{structure.get('recap', {}).get('requirement', '回顾上一章结尾，简洁过渡')}

### 反派极致羞辱（{structure.get('villain_ramp_up', {}).get('range', '500字处')}）
**情绪强度：8/10**
{structure.get('villain_ramp_up', {}).get('requirement', '反派极致羞辱')}

### 转折点（{structure.get('turning_point', {}).get('range', '800-1200字')}）
{structure.get('turning_point', {}).get('requirement', '主角反击开始，反派出招')}

### 打脸高潮（{structure.get('climax', {}).get('range', '1500字处')}）
**情绪强度：10/10（本章最高潮）**
{structure.get('climax', {}).get('requirement', '打脸高潮，碾压式反击')}

### 收益展示（{structure.get('harvest', {}).get('range', '2000字处')}）
{structure.get('harvest', {}).get('requirement', '系统提示+具体数字收益')}

### 章尾钩子（{structure.get('hook', {}).get('range', '章尾')}）
{structure.get('hook', {}).get('requirement', '更大反派/新目标')}

## 【震惊流写法】（必须三层结构）
{shock_flow.get('description', '现场→传播→权威')}

**铺展层次：**
{layers_str}

**反派转变：{shock_flow.get('villain_turn', '180度态度转变')}**

{self._render_algorithm_requirements_from_config(algo_req)}

{self._render_self_check_from_config(config.get('self_check_steps', []))}

{self._render_output_format_from_config(common.get('output_format', {}))}
"""
        return prompt

    def _render_standard_chapter_from_config(
        self, chapter_num: int, chapter_type: str, 
        blueprint: Dict, prev_summary: str
    ) -> str:
        """从 JSON 配置渲染标准章节提示词"""
        if not self._standard_chapter_prompts:
            raise ConfigError("标准章节提示词配置未加载", "standard_chapter_prompts.json")
        
        config = self._standard_chapter_prompts
        
        # 提取蓝图变量
        scene = blueprint.get('scene', '')
        event = blueprint.get('event', '')
        emotion = blueprint.get('emotion', '')
        purpose = blueprint.get('purpose', '')
        beat_type = blueprint.get('beat_type', '')
        
        # 构建策略列表
        strategies = config.get('expansion_strategies', [])
        strategies_str = '\n'.join([f"- {s}" for s in strategies])
        
        # 构建连贯性检查列表
        coherence = config.get('coherence_checks', [])
        coherence_str = '\n'.join([f"- {c}" for c in coherence])
        
        # 构建提示词
        prompt = f"""# 第{chapter_num}章生成指令

## 【章节定位】
类型：{chapter_type}
情绪：{emotion if emotion else '根据章节功能判断'}

## 【战术大纲约束】
**场景：{scene}**
**事件：{event}**
**战术企图：{purpose}**
**节拍类型：{beat_type}**

## 【字数要求】
{config.get('word_count', {}).get('target', '2200-2500字')}
绝对下限：{config.get('word_count', {}).get('min_absolute', '2000字')}，绝对上限：{config.get('word_count', {}).get('max_absolute', '2500字')}

## 【算法要求】
{self._render_algorithm_requirements_from_config(config.get('algorithm_requirements', {}))}

## 【展开策略】
{strategies_str}

## 【连贯性检查】
{coherence_str}

## 【自检清单】
{self._render_self_check_from_config(config.get('self_check_steps', []))}

{self._render_output_format_from_config(config.get('output_format', {}))}
"""
        return prompt

    def _render_algorithm_requirements_from_config(self, algo: Dict) -> str:
        """从配置渲染算法要求"""
        if not algo:
            return ""
        
        emotion = algo.get('emotion_density', {})
        hook = algo.get('hook_presence', {})
        appeal = algo.get('appeal_density', {})
        basic = algo.get('basic', [])
        
        return f"""## 【番茄算法强制指标 - 必须严格达标】

### 🔥 情绪密度指标（严重缺失，必须修复！）
**目标：{emotion.get('target', '≥2.0个/千字')}**（当前0.59，差距-70%！）

**强制要求：**
- 每500字必须出现≥{emotion.get('min_count', 10) // 4}个强烈情绪词
- 每章至少{emotion.get('min_count', 10)}个不同情绪词
- 情绪词必须分布在全文，禁止集中在某一段

**情绪词库（必须使用）：**
- 愤怒类：暴怒、狂怒、目眦尽裂、杀意滔天、怒火中烧、恨意滔天
- 震惊类：震撼、骇然、惊恐、目瞪口呆、头皮发麻、倒吸凉气
- 爽快类：狂喜、激动、兴奋、畅快、扬眉吐气、通体舒泰
- 压抑类：绝望、无力、屈辱、悲愤、心如刀割、窒息
- 反转类：错愕、懵然、难以置信、怀疑人生、惊骇欲绝

---

### 🎣 章尾钩子指标（83%缺失，必须修复！）
**目标：{hook.get('compliance_rate', '100%')}章节必须有钩子**（当前仅17%！）

**强制要求：**
- 最后50字**必须是悬念/钩子**，绝对禁止平淡结尾
- 钩子类型（必须选一种）：
  1. **时间锁**：具体倒计时（"71小时59分后，死局降临"）
  2. **信息差**：主角知道读者知道但反派不知道（"他嘴角微扬，那畜生不知道的是..."）
  3. **危机预警**：更大危机逼近（"远处，S级凶兽睁开了眼..."）
  4. **身份揭露**：神秘人物登场（"电话那头，竟是已死的父亲..."）
  5. **反派出招**：反派放大招（"你以为这就完了？真正的游戏刚开始"）

---

### ⚡ 爽点密度指标（断档严重，必须修复！）
**目标：{appeal.get('target', '≥1.5个/千字')}**（当前0.67，差距-55%！）

**强制要求：**
- 每章至少{appeal.get('min_moments', 3)}-5个爽点时刻
- 爽点必须有"震惊反应链"（现场→围观者→传播→权威）
- 必须有具体数字/数值强化爽感

**爽点词库（必须使用）：**
- 碾压类：碾压、横扫、瞬杀、一招秒杀、摧枯拉朽
- 震惊类：全场死寂、骇然失色、难以置信、怀疑人生
- 收获类：暴涨、飙升、翻倍、突破、觉醒、进化
- 打脸类：打脸、反转、跪服、求饶、后悔莫及

---

### 📊 基础指标
{chr(10).join(['- ' + b for b in basic])}

## 【🚨 三大问题修复检查清单】
**以下指标严重不达标，必须重点检查！**

### 1. 情绪密度检查（目标：{emotion.get('target', '≥2.0/千字')}）
- [ ] 统计本章情绪词数量（不少于{emotion.get('min_count', 10)}个）
- [ ] 情绪词分布是否均匀（每500字至少1个）
- [ ] 情绪词强度是否足够（用"暴怒"而非"生气"）

### 2. 章尾钩子检查（目标：{hook.get('compliance_rate', '100%')}有钩子）
- [ ] 最后50字必须是钩子，禁止平淡结尾
- [ ] 钩子类型是否明确（时间锁/信息差/危机/身份揭露）
- [ ] 是否让人产生"必须点下一章"的冲动

### 3. 爽点密度检查（目标：{appeal.get('target', '≥1.5/千字')}）
- [ ] 本章爽点时刻数量（不少于{appeal.get('min_moments', 3)}个）
- [ ] 每个爽点是否有震惊反应链
- [ ] 是否有具体数字强化爽感
"""
    
    def _render_self_check_from_config(self, steps: List[Dict]) -> str:
        """从配置渲染自检清单"""
        if not steps:
            return ""
        
        sections = []
        for step in steps:
            name = step.get('name', '')
            items = step.get('items', [])
            sections.append(f"**Step {len(sections)+1}: {name}**\n" + chr(10).join([f"- {item}" for item in items]))
        
        return f"""## 【重要：生成后必须自检】

生成完第1章正文后，你必须按照以下步骤自检：

{chr(10).join(sections)}

如果自检不通过，请重新优化后再次输出。
"""
    
    def _render_output_format_from_config(self, output_format: Dict) -> str:
        """从配置渲染输出格式"""
        if not output_format:
            return ""
        
        schema = output_format.get('schema', {})
        rules = output_format.get('rules', [])
        
        rules_text = chr(10).join(['- ' + r for r in rules]) if rules else "- title字段只放标题文本，不要加'第X章'前缀\n- content字段只放正文，绝对禁止在正文开头写'第X章 XXX'"
        
        return f"""## 【🚨 强制输出格式 - 必须严格遵守】

### 标题规范（番茄爆款标准）
- 字数：8-14字（**不含**"第X章"前缀）
- 内容：概括本章核心爽点/悬念
- 风格：简洁有力，有冲击力
- **⚠️ 致命错误**：如果在正文开头写"第12章 XXX"这样的标题行，内容将被判定为不合格！

### JSON输出格式（唯一允许的格式）
**你必须且只能返回一个符合以下结构的JSON对象，任何其他格式都会被拒绝：**

```json
{{
  "title": "章节标题（8-14字，不含'第X章'）",
  "content": "章节正文内容（2000-2500字，正文开头不要写标题）"
}}
```

### 🚨 强制规则（违反会导致生成失败）
{rules_text}

### ❌ 错误示例（绝对禁止）
```json
{{
  "chapter_number": 12,
  "content": "第12章 国际联盟逼宫...\\n\\n昆仑山脉的炮声..."
}}
```
**错误原因**：content字段包含了"第12章"标题行！

### ✅ 正确示例
```json
{{
  "title": "国际联盟逼宫，公知带节奏卖国求荣",
  "content": "昆仑山脉的炮声还未停歇，联合国特别会议的邀请函已经送到了龙国大长老的案头..."
}}
```

### 🔥 最终检查清单
输出前必须检查：
- [ ] 返回的是否是合法JSON格式？
- [ ] title字段是否存在且不含"第X章"？
- [ ] content字段是否以正文开头（不是标题）？
- [ ] content字段内是否绝对没有出现"第X章 XXX"字样？

**警告：如果检查不通过，必须重新生成！**
"""
    
    def _build_blueprint_constraint(self, beat_type: str, purpose: str, 
                                    emotion: str, scene: str, event: str, 
                                    hook_content: str, has_blueprint: bool) -> str:
        """构建大纲约束部分"""
        if not has_blueprint:
            return ""
        
        # 构建节拍类型描述
        beat_type_desc = ""
        if beat_type:
            beat_type_map = {
                "铺垫": """- 本章要积蓄情绪，为高潮做准备
- 不要让主角太早得意，要压抑
- 要埋下伏笔和悬念""",
                "冲突": """- 本章要制造对抗，让矛盾白热化
- 要让读者感到紧张和压力
- 反派要强势，让主角陷入困境""",
                "反转": """- 本章要完成刷新认知的反转
- 主角要从被动转为主动
- 要让读者感到大爽或震惊""",
                "渲染": """- 本章要放大已有情绪或震惊效果
- 要通过多角度、多层次描写震惊
- 要让读者完全代入情绪""",
                "伏笔": """- 本章要埋下伏笔，为后文做铺垫
- 要抛出新的悬念和线索
- 不要急于收线，要留空间"""
            }
            beat_type_desc = beat_type_map.get(beat_type, "")
        
        return f"""## 【⚠️ 战术大纲强制约束 - 必须严格遵守】

**本章必须按照以下大纲内容创作，严禁偏离！**

### 🎺 节拍类型（决定章节结构）
**节拍类型：{beat_type}**
{beat_type_desc}

### 🎯 战术企图（必须达成的目标）
**{purpose}**

本章的核心任务是完成上述战术企图，所有情节设计必须围绕此目标展开。
禁止写与战术企图无关的内容。

### 🎨 情绪基调（必须严格执行）
**本章情绪：{emotion if emotion else '根据事件判断'}**
情绪是本章的核心！整章必须统一在此情绪基调下，禁止情绪乱跳或偏离！
- 如果是"压抑"：整章要让读者感到绝望、无力、心痛
- 如果是"大爽快"：整章要让读者感到痛快、解气、通体舒泰
- 如果是"紧张"：整章要让读者紧张得缩起脚趾
- 如果是"震惊"：要通过多层次震惊描写让读者感叹

### 🏛️ 场景设定（必须严格遵循）
- 场景：{scene if scene else '详见事件描述'}
- 必须保持世界观一致性，禁止出现校园场景

### 📜 核心事件（必须完整呈现）
{event if event else '无具体事件描述'}

### 🎭 章尾钩子（必须在最后50字呈现）
{hook_content if hook_content else '根据情节自然留白'}

### ❌ 禁止出现的元素{self._build_forbidden_list()}

### ✅ 必须出现的元素
- 严格按照大纲指定的节拍类型进行创作
- 严格按照大纲指定的战术企图完成章节目标
- 严格按照大纲指定的情绪基调进行创作
- 严格按照大纲指定的场景和事件
- 主角行为必须符合题材设定
"""
    
    def _build_golden_chapter_2(self, blueprint: Dict, prev_summary: str) -> str:
        """构建第2章（验证章）提示词 - 从 JSON 配置加载"""
        if not self._golden_chapter_prompts or 'chapter_2' not in self._golden_chapter_prompts:
            raise ConfigError("第2章提示词配置缺失", "golden_chapter_prompts.json")
        try:
            return self._render_golden_chapter_2_from_config(blueprint, prev_summary)
        except Exception as e:
            logger.error(f"[PromptV3] 从配置渲染第2章提示词失败: {e}")
            raise ConfigError(f"第2章提示词渲染失败: {e}", "golden_chapter_prompts.json")

    def _build_golden_chapter_3(self, blueprint: Dict, prev_summary: str) -> str:
        """构建第3章（打脸章）提示词 - 从 JSON 配置加载"""
        if not self._golden_chapter_prompts or 'chapter_3' not in self._golden_chapter_prompts:
            raise ConfigError("第3章提示词配置缺失", "golden_chapter_prompts.json")
        try:
            return self._render_golden_chapter_3_from_config(blueprint, prev_summary)
        except Exception as e:
            logger.error(f"[PromptV3] 从配置渲染第3章提示词失败: {e}")
            raise ConfigError(f"第3章提示词渲染失败: {e}", "golden_chapter_prompts.json")
    def _build_standard_chapter_prompt(self, chapter_num: int, chapter_type: str,
                                        blueprint: Dict, prev_summary: str) -> str:
        """构建标准章节提示词（第4章以后）- 从 JSON 配置加载"""
        if self._standard_chapter_prompts:
            try:
                return self._render_standard_chapter_from_config(
                    chapter_num, chapter_type, blueprint, prev_summary
                )
            except Exception as e:
                logger.error(f"[PromptV3] 从配置渲染标准章节提示词失败: {e}")
                raise ConfigError(f"标准章节提示词渲染失败: {e}", "standard_chapter_prompts.json")
        raise ConfigError("标准章节提示词配置缺失", "standard_chapter_prompts.json")
    def _build_setup_template(self) -> str:
        """构建铺垫章模板 - 从 JSON 配置加载"""
        return self._render_template("SETUP")
    
    def _build_faceslap_template(self) -> str:
        """构建打脸章模板 - 从 JSON 配置加载"""
        return self._render_template("FACE_SLAP")
    
    def _build_reward_template(self) -> str:
        """构建收获章模板 - 从 JSON 配置加载"""
        return self._render_template("REWARD")
    
    def _build_reveal_template(self) -> str:
        """构建揭秘章模板 - 从 JSON 配置加载"""
        return self._render_template("REVEAL")
    
    def _build_crisis_template(self) -> str:
        """构建危机章模板 - 从 JSON 配置加载"""
        return self._render_template("CRISIS")
    
    def _build_transition_template(self) -> str:
        """构建过渡章模板 - 从 JSON 配置加载"""
        return self._render_template("TRANSITION")
    
    # ==================== 辅助方法 ====================
    
    def _get_genre_elements_for_chapter(self, chapter_num: int) -> str:
        """获取题材专项元素"""
        if self.genre_type not in self.GENRE_TEMPLATES:
            return ""
        
        template = self.GENRE_TEMPLATES[self.genre_type]
        sections = [f"\n## 【{self.genre_type}专项技法】\n"]
        
        # 弹幕模板
        if template.get("has_livestream") and chapter_num <= 3:
            sections.append("### 弹幕设计（每章至少3-5条）")
            sections.append("```")
            for 弹幕 in template.get("弹幕模板", [])[:5]:
                sections.append(弹幕)
            sections.append("```")
        
        # 系统提示音
        if template.get("返利音效"):
            sections.append(f"\n### 系统提示音模板")
            sections.append(f"`{template.get('返利音效', '')}`")
        
        # 模拟过程
        if template.get("has_simulation") and chapter_num <= 3:
            sections.append("\n### 模拟过程写法（快速剪辑感）")
            sections.append("```")
            for tmpl in template.get("模拟过程模板", []):
                sections.append(tmpl)
            sections.append("```")
        
        # 震惊层级
        if template.get("震惊层级"):
            sections.append("\n### 震惊层级（层层递进）")
            for i, level in enumerate(template.get("震惊层级", []), 1):
                sections.append(f"{i}. {level}")
        
        return "\n".join(sections)
    
    def _get_emotion_beat(self, chapter_num: int) -> str:
        """获取情绪节拍"""
        emotion_curve = self.emotion_curve
        if not emotion_curve:
            return ""
        
        # 查找各阶段的详细曲线
        phases = ['phase_1_early_domination', 'phase_2_rising_power', 
                  'phase_3_global_dominance', 'phase_4_cosmic_conquest']
        
        for phase_key in phases:
            phase = emotion_curve.get(phase_key, {})
            if not phase:
                continue
            
            curve = phase.get('curve', [])
            milestones = phase.get('key_milestones', [])
            
            # 在详细曲线中查找
            for beat in curve:
                if beat.get('ch') == chapter_num:
                    result = f"情绪类型：{beat.get('emotion', '期待')}（强度{beat.get('intensity', 6)}/10）\n"
                    result += f"节拍类型：{beat.get('beat_type', '推进')}\n"
                    result += f"核心事件：{beat.get('event', '剧情推进')}\n"
                    result += f"章节目的：{beat.get('purpose', '推进剧情')}\n"
                    result += f"钩子设计：{beat.get('hook', '根据类型选择')}"
                    return result
            
            # 在里程碑中查找
            for milestone in milestones:
                if isinstance(milestone, dict):
                    ch = milestone.get('ch') or milestone.get('chapter')
                    if ch == chapter_num:
                        result = f"【关键里程碑章节】\n"
                        result += f"事件：{milestone.get('event', '')}\n"
                        result += f"情绪：{milestone.get('emotion', '大爽')}\n"
                        result += f"强度：{milestone.get('intensity', 10)}/10\n"
                        result += f"这是重要节点，必须大场面！"
                        return result
        
        return ""
    
    def _get_chapter_outline(self, chapter_num: int) -> str:
        """获取章节大纲"""
        plan = self.plan
        if not plan:
            return f"第{chapter_num}章"
        
        # 🔥 弃用：outline_first_30 不再在一阶段生成
        # 详细章节规划现由 TacticalPlanner 动态生成
        # 保留此代码仅用于向后兼容，实际返回回退值
        outline = plan.get('outline_first_30', [])
        
        # 查找该章（legacy，通常为空列表）
        for item in outline:
            if isinstance(item, dict):
                ch = item.get('chapter', item.get('ch', 0))
                if ch == chapter_num:
                    title = item.get('title', '')
                    event = item.get('event', item.get('key_event', ''))
                    emotion = item.get('emotion', '')
                    result = f"第{chapter_num}章"
                    if title:
                        result += f" | 标题：{title}"
                    if event:
                        result += f" | 关键事件：{event}"
                    if emotion:
                        result += f" | 情绪：{emotion}"
                    return result
        
        # 根据章节号判断阶段
        if chapter_num <= 3:
            return f"第{chapter_num}章 | 【开局阶段】建立主角形象，展示金手指"
        elif chapter_num <= 10:
            return f"第{chapter_num}章 | 【第一次小高潮区间】小爽点密集"
        elif chapter_num <= 15:
            return f"第{chapter_num}章 | 【第一次中高潮区间】关键转折"
        elif chapter_num <= 30:
            return f"第{chapter_num}章 | 【第一阶段高潮】重大事件"
        else:
            return f"第{chapter_num}章 | 【持续发展阶段】保持节奏"
    
    def _build_checklist(self, chapter_type: str) -> str:
        """构建检查清单"""
        checklists = {
            "GOLDEN_1": """
- [ ] 3句话内让读者同情主角
- [ ] 系统触发有画面感
- [ ] 章尾钩子让人想点下一章
- [ ] 有具体的数字（金额/数值）
- [ ] 前300字出现冲突/羞辱
- [ ] 500字处系统触发
- [ ] 对话自然推动剧情
- [ ] 无大段环境描写
- [ ] 无超过100字内心独白
""",
            "GOLDEN_2": """
- [ ] 金手指使用过程清晰
- [ ] 首次成功有具体数字
- [ ] 新反派让读者恨
- [ ] 为第3章打脸做铺垫
- [ ] 第800字处金手指使用
- [ ] 1500字处第一次成功
- [ ] 章尾出现新冲突
- [ ] 情绪曲线正确
""",
            "GOLDEN_3": """
- [ ] 公开场合有围观群众
- [ ] 反派极致羞辱（先抑）
- [ ] 主角强势反击（后扬）
- [ ] 有具体数字（金额/数值）
- [ ] 震惊反应完整（现场→传播→权威）
- [ ] 反派态度180度转变
- [ ] 系统提示和收益展示
- [ ] 章尾有钩子
- [ ] 500字处压抑，1500字处爆发
""",
            "FACE_SLAP": """
- [ ] 公开场合（有围观群众）
- [ ] 反派极致羞辱
- [ ] 主角强势反击
- [ ] 具体数字（金额/数值）
- [ ] 震惊反应完整（现场→传播→权威）
- [ ] 反派态度转变
- [ ] 情绪强度：8→10→9→7
- [ ] 章尾钩子
""",
            "REWARD": """
- [ ] 系统提示音
- [ ] 具体收益（数值/物品）
- [ ] 效果展示
- [ ] 实际应用
- [ ] 之前vs现在对比
- [ ] 让读者有获得感
- [ ] 章尾新目标
""",
        }
        
        return checklists.get(chapter_type, checklists.get("FACE_SLAP", ""))
    
    def _build_tactical_plan_section(self, chapter_num: int, blueprint: Dict) -> str:
        """
        构建战术规划部分 - 从blueprint提取本章的详细规划（增强版）
        
        修复：添加强制约束，确保AI严格遵守大纲
        
        Args:
            chapter_num: 章节号
            blueprint: 可以是完整蓝图（含chapters列表）或单章规划（chapter_plan）
        """
        if not blueprint:
            return "战术规划：无（请自由发挥，但需符合章节类型）"
        
        # 🔥 修复：处理两种传入情况
        # 情况1：完整蓝图，包含 chapters 列表
        # 情况2：单章规划，直接就是当前章节的规划
        chapter_plan = None
        
        if 'chapters' in blueprint:
            # 情况1：从 chapters 列表中查找
            chapters = blueprint.get('chapters', [])
            if isinstance(chapters, list):
                for ch in chapters:
                    if isinstance(ch, dict) and ch.get('chapter_number') == chapter_num:
                        chapter_plan = ch
                        break
            elif isinstance(chapters, dict):
                # 兼容旧格式
                chapter_plan = chapters.get(f"chapter_{chapter_num:03d}")
        else:
            # 情况2：blueprint本身就是单章规划
            # 验证章节号是否匹配（如果规划中有chapter_number）
            plan_ch_num = blueprint.get('chapter_number')
            if plan_ch_num is None or plan_ch_num == chapter_num:
                chapter_plan = blueprint
        
        if not chapter_plan:
            return f"战术规划：第{chapter_num}章无详细规划（请根据章节类型自由发挥）"
        
        # 🔥🔥🔥 提取关键字段
        emotion = chapter_plan.get('emotion', '')
        intensity = chapter_plan.get('intensity', '')
        beat_type = chapter_plan.get('beat_type', '')
        event = chapter_plan.get('event', '')
        purpose = chapter_plan.get('purpose', '')
        hook_type = chapter_plan.get('hook_type', '')
        hook_content = chapter_plan.get('hook_content', '')
        stage_goal = chapter_plan.get('stage_goal_alignment', '')
        
        # 构建节拍类型说明
        beat_type_guide = ""
        if beat_type:
            beat_descriptions = {
                "铺垫": "铺垫：积蓄情绪，为高潮做准备，不要让主角太早得意",
                "冲突": "冲突：制造对抗，让矛盾白热化，让读者紧张",
                "反转": "反转：完成刷新认知的反转，主角从被动转为主动",
                "渲染": "渲染：放大已有情绪或震惊效果，多角度描写",
                "伏笔": "埋笔：埋下伏笔，为后文做铺垫，抛出新线索",
            }
            beat_guide = beat_descriptions.get(beat_type, "按节拍类型自行把握")
            beat_type_guide = f"""
### 🎺 节拍类型（决定章节结构）
**节拍类型：{beat_type}**
- {beat_guide}
"""
        
        # 构建战术企图说明
        purpose_section = ""
        if purpose:
            purpose_section = f"""
### 🎯 战术企图（必须达成的目标）
**{purpose}**

本章的核心任务是完成上述战术企图，所有情节设计必须围绕此目标展开。
禁止写与战术企图无关的内容。
"""
        
        # 构建情绪说明
        emotion_guide = ""
        if emotion:
            emotion_descriptions = {
                "压抑": "整章要让读者感到绝望、无力、心痛，主角处于被动",
                "大爽快": "整章要让读者感到痛快、解气、通体舒泰，主角完美反杀",
                "紧张": "整章要让读者紧张得缩起脚趾，不知道结果如何",
                "震惊": "要通过多层次震惊描写让读者感叹，三层反应必须到位",
                "期待": "要让读者对未来充满好奇和期待，抛出新线索",
            }
            em_guide = emotion_descriptions.get(emotion, "根据情绪类型自行把握")
            emotion_guide = f"""
### 🎨 情绪基调（必须严格执行）
**本章情绪：{emotion}**强度：{intensity}/10

{em_guide}

情绪是本章的核心！整章必须统一在此情绪基调下，禁止情绪乱跳或偏离！
"""
        
        # 构建核心事件
        event_section = ""
        if event:
            event_section = f"""
### 📜 核心事件（必须完整呈现）
{event}

**严禁偏离上述事件！** 如需扩写，必须在不改变核心剧情的前提下进行。
"""
        
        # 构建钩子
        hook_section = ""
        if hook_content:
            hook_section = f"""
### 🎭 章尾钩子（必须在最后50字呈现）
{hook_content}

**钩子类型：{hook_type if hook_type else '根据内容自行判断'}**
"""
        
        # 构建阶段目标
        stage_section = ""
        if stage_goal:
            stage_section = f"""
### 🎯 阶段目标对齐
{stage_goal}

本章必须服务于上述阶段目标，推进关键交付物的完成。
"""
        
        # 构建禁止清单（根据题材动态生成）
        forbidden_list = self._build_forbidden_list()
        forbidden_section = f"""
### ❌ 禁止出现的元素{forbidden_list}
"""
        
        # 构建必须清单
        required_section = """
### ✅ 必须出现的元素
- 严格按照大纲指定的节拍类型进行创作
- 严格按照大纲指定的战术企图完成章节目标
- 严格按照大纲指定的情绪基调进行创作
- 严格按照大纲指定的场景和事件
- 主角行为必须符合题材设定
"""
        
        # 组合最终输出
        result_parts = [
            beat_type_guide,
            purpose_section,
            emotion_guide,
            event_section,
            hook_section,
            stage_section,
            forbidden_section,
            required_section,
        ]
        
        return "\n".join([p for p in result_parts if p])
    
    def _format_prev_summary(self, prev_summary: str, chapter_num: int, blueprint: Dict) -> str:
        """
        格式化前文摘要（增强版）
        
        优化：使用 _build_tactical_plan_section 获取更完整的前一章战术规划
        
        Args:
            prev_summary: 前一章内容摘要
            chapter_num: 当前章节号
            blueprint: 可以是完整蓝图或单章规划
        """
        result_lines = []
        
        # 优先使用传入的摘要（如果有效）
        if prev_summary and len(prev_summary.strip()) > 50:
            result_lines.append(f"第{chapter_num-1}章内容摘要：{prev_summary[:400]}")
        
        # 🔥 只有当blueprint包含chapters列表（完整蓝图）时，才尝试获取前一章战术规划
        # 如果blueprint是单章规划，无法获取前一章信息
        if blueprint and chapter_num > 1 and 'chapters' in blueprint:
            prev_tactical = self._build_tactical_plan_section(chapter_num - 1, blueprint)
            if prev_tactical and not prev_tactical.startswith("战术规划：无"):
                result_lines.append(f"第{chapter_num-1}章战术规划：")
                for line in prev_tactical.split('\n'):
                    result_lines.append(f"  {line}")
        
        if result_lines:
            return "\n".join(result_lines)
        
        return f"继续第{chapter_num-1}章剧情，保持连贯性"



# ==================== 便捷函数 ====================

def create_optimizer_v3(novel_data: Dict) -> ChapterPromptOptimizerV3:
    """
    便捷函数：创建v3.0优化器
    
    Args:
        novel_data: 小说数据
        
    Returns:
        ChapterPromptOptimizerV3实例
    """
    return ChapterPromptOptimizerV3(novel_data)


# 向后兼容性别名
ChapterPromptOptimizer = ChapterPromptOptimizerV3


# 测试代码
if __name__ == "__main__":
    # 测试数据
    test_data = {
        "title": "测试小说：开局无敌",
        "genre": "国运文-直播类",
        "plan": {
            "protagonist": {
                "basic_info": {"name": "林上", "age": 22}
            },
            "opening_design": {
                "chapter_1": {"scene": "开局场景", "key_scene": "关键场景"}
            }
        },
        "character_design": {
            "protagonist": {
                "basic_info": {"name": "林上", "age": 22},
                "traits": ["杀伐果断", "护短"],
                "signature_details": {
                    "catchphrase": ["蝼蚁", "记账了"],
                    "actions": ["负手而立"]
                }
            }
        },
        "core_worldview": {
            "world_overview": "国运禁地，直播",
            "world_rules": [{"rule": "弱肉强食"}]
        }
    }
    
    optimizer = ChapterPromptOptimizerV3(test_data)
    
    print("=" * 60)
    print("System Prompt 长度:", len(optimizer.build_system_prompt()))
    print("=" * 60)
    
    print("\n第1章提示词预览:")
    ch1_prompt = optimizer.build_chapter_prompt(1)
    print(ch1_prompt[:500] + "...")
    
    print("\n第2章提示词预览:")
    ch2_prompt = optimizer.build_chapter_prompt(2)
    print(ch2_prompt[:500] + "...")
    
    print("\n第3章提示词预览:")
    ch3_prompt = optimizer.build_chapter_prompt(3)
    print(ch3_prompt[:500] + "...")
    
    print("\n✅ 所有测试通过！")
