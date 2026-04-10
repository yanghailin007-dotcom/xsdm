# -*- coding: utf-8 -*-
"""
V2 六层架构集成适配器

将 V2 架构 (Layer 3/4/5/6) 集成到现有的 ChapterConversationGenerator

集成策略:
- System Prompt = Layer 3 (题材技法) + Layer 4 (文风)
- User Prompt = Layer 5 (AI约束+情绪曲线) + Layer 6 (自检) + 任务指令
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class V2IntegrationAdapter:
    """
    V2 架构集成适配器
    
    负责:
    1. 检测题材类型并加载对应的 Layer 3 (题材技法)
    2. 组装 Layer 3-4 为 System Prompt
    3. 组装 Layer 5-6 + 任务为 User Prompt
    """
    
    def __init__(self, novel_data: Dict, genre: str = None):
        """
        初始化适配器
        
        Args:
            novel_data: 小说数据
            genre: 题材类型 (如 "神豪文-盲盒返利类", "国运文-直播类")
        """
        logger.debug(f"[V2适配器] __init__ 开始 | novel_data类型: {type(novel_data)}")
        
        # 处理 novel_data 是 list 的情况（从某些API传入时可能出现）
        if isinstance(novel_data, list):
            logger.warning(f"[V2适配器] novel_data 是列表类型，尝试取第一个元素")
            novel_data = novel_data[0] if novel_data else {}
            logger.debug(f"[V2适配器] 取第一个元素后类型: {type(novel_data)}")
        
        # 确保是字典类型
        if not isinstance(novel_data, dict):
            logger.warning(f"[V2适配器] novel_data 类型异常: {type(novel_data)}，使用空字典")
            novel_data = {}
        
        self.novel_data = novel_data
        
        # 检测题材
        try:
            self.genre = genre or self._detect_genre()
            logger.info(f"[V2适配器] 初始化 | 题材: {self.genre}")
        except Exception as e:
            logger.error(f"[V2适配器] _detect_genre 失败: {e}")
            self.genre = '通用'
        
        # 懒加载 V2 组件
        self._layered_system_prompt = None
        self._layered_user_prompt = None
        self._genre_loader = None
        self._genre_renderer = None
    
    def _get_genre_config_path(self, genre_file: str) -> Path:
        """
        获取题材配置文件路径
        优先级:
        1. prompt_packages/default/market_driven/v2_config/genre_techniques/ (用户配置)
        2. prompt_packages/v2_architecture/genre_techniques/ (系统默认)
        """
        project_root = Path(__file__).parent.parent.parent.parent
        
        # 优先使用用户配置
        user_path = project_root / "prompt_packages" / "default" / "market_driven" / "v2_config" / "genre_techniques" / genre_file
        if user_path.exists():
            return user_path
        
        # 回退到系统默认
        default_path = project_root / "prompt_packages" / "v2_architecture" / "genre_techniques" / genre_file
        if default_path.exists():
            return default_path
        
        return None
    
    def _detect_genre(self) -> str:
        """从小说数据中检测题材类型"""
        logger.debug(f"[V2适配器] _detect_genre 开始 | novel_data类型: {type(self.novel_data)}")
        
        # 确保 novel_data 是字典
        if not isinstance(self.novel_data, dict):
            logger.warning(f"[V2适配器] _detect_genre: novel_data 不是字典，是 {type(self.novel_data)}，返回通用")
            return '通用'
        
        # 🔥 1. 优先从 suggestions.genre 获取（最准确的来源）
        try:
            suggestions = self.novel_data.get('suggestions', {})
            logger.debug(f"[V2适配器] suggestions 类型: {type(suggestions)}")
            if isinstance(suggestions, dict) and suggestions.get('genre'):
                genre = suggestions.get('genre')
                logger.info(f"[V2适配器] 从 suggestions.genre 获取题材: {genre}")
                return genre
        except Exception as e:
            logger.warning(f"[V2适配器] 获取 suggestions.genre 失败: {e}")
        
        # 2. 尝试从 tags 中获取
        try:
            tags = self.novel_data.get('tags', {})
            logger.debug(f"[V2适配器] tags 类型: {type(tags)}")
            
            # 处理 tags 是 list 的情况
            if isinstance(tags, list):
                logger.debug(f"[V2适配器] tags 是列表类型，跳过")
                themes = []
            elif isinstance(tags, dict):
                themes = tags.get('themes', [])
            else:
                themes = []
            
            if '神豪' in themes or '花钱' in themes or '返利' in themes:
                return '神豪文-花钱返利类'
            if '国运' in themes:
                return '国运文-直播类'
            if '签到' in themes:
                return '神豪文-签到奖励类'
        except Exception as e:
            logger.warning(f"[V2适配器] 获取 tags 失败: {e}")
        
        # 3. 尝试从标题/简介中检测（扩展支持更多题材）
        try:
            title = self.novel_data.get('title', '')
            synopsis = self.novel_data.get('synopsis', '')
            text = title + synopsis
            
            # 女频题材
            if any(kw in text for kw in ['甜宠', '豪门', '总裁', '先婚后爱']):
                return '甜宠文-豪门总裁类'
            if any(kw in text for kw in ['虐恋', '替身', '白月光', '破镜重圆']):
                return '虐恋文-替身白月光类'
            if any(kw in text for kw in ['穿越', '古代', '嫡女', '王妃']):
                return '穿越文-古代言情类'
            if any(kw in text for kw in ['重生', '复仇', '逆袭']):
                return '重生文-复仇逆袭类'
            if any(kw in text for kw in ['宫斗', '皇后', '后宫']):
                return '宫斗文-后宫升级类'
            if any(kw in text for kw in ['宅斗', '嫡女', '主母']):
                return '宅斗文-嫡女逆袭类'
            if any(kw in text for kw in ['快穿', '攻略', '反派']):
                return '快穿文-攻略反派类'
            if any(kw in text for kw in ['军婚', '七零', '年代']):
                return '军婚文-七零年代类'
            if any(kw in text for kw in ['团宠', '锦鲤', '福宝']):
                return '团宠文-锦鲤福宝类'
            if any(kw in text for kw in ['娱乐圈', '顶流', '影帝']):
                return '娱乐圈文-顶流恋人类'
            if any(kw in text for kw in ['玄学', '算命', '直播捉鬼']):
                return '玄学文-直播算命类'
            if any(kw in text for kw in ['兽世', '兽人', '部落']):
                return '兽世文-穿越兽人类'
            if any(kw in text for kw in ['种田', '空间', '灵泉']):
                return '种田文-发家致富类'
            
            # 男频题材
            if any(kw in text for kw in ['神豪', '花钱', '返利', '百倍', '盲盒', '签到']):
                if '国运' in text:
                    return '国运文-直播类'
                return '神豪文-花钱返利类'
            if any(kw in text for kw in ['国运', '禁地', '扮演', '求生']):
                return '国运文-直播类'
            if any(kw in text for kw in ['奶爸', '萌宝', '带娃']):
                return '奶爸文-萌宝类'
            if any(kw in text for kw in ['神选', '神明', '神级']):
                return '神选文-神明选拔类'
            if any(kw in text for kw in ['模拟器', '模拟人生', '回档']):
                return '模拟器文-人生模拟类'
            if any(kw in text for kw in ['灵气复苏', '觉醒', '超凡']):
                return '灵气复苏-觉醒类'
            if any(kw in text for kw in ['末日', '求生', '囤货', '丧尸']):
                return '末日求生-囤货类'
            if any(kw in text for kw in ['四合院', '禽满', '年代']):
                return '四合院-日常类'
            if any(kw in text for kw in ['诡异', '规则怪谈', '恐怖']):
                return '诡异复苏-规则怪谈类'
            if any(kw in text for kw in ['游戏', '网游', '虚拟现实']):
                return '游戏异界-虚拟现实类'
            if any(kw in text for kw in ['美食', '厨神', '系统烹饪']):
                return '美食文-系统烹饪类'
            if any(kw in text for kw in ['御兽', '宠物', '召唤']):
                return '宠物文-御兽进化类'
            if any(kw in text for kw in ['历史', '架空', '权谋']):
                return '历史架空-权谋争霸类'
            if any(kw in text for kw in ['文娱', '文抄公', '娱乐']):
                return '文娱文-文抄公类'
            if any(kw in text for kw in ['盗墓', '探险', '古墓']):
                return '盗墓文-探险寻宝类'
            if any(kw in text for kw in ['综漫', '无限流', '诸天']):
                return '综漫文-无限流类'
                
        except Exception as e:
            logger.warning(f"[V2适配器] 从标题检测失败: {e}")
        
        # 4. 默认通用
        logger.info(f"[V2适配器] 无法检测题材，返回通用")
        return '通用'
    
    def _init_v2_components(self):
        """
        懒加载 V2 组件
        
        注意分层:
        - Layer 1-2,4: 从项目信息动态构建 (novel_data/writing_style/chapter_plan)
        - Layer 3,5-6: 从 YAML 配置文件加载
        """
        if self._genre_loader is None:
            try:
                from .v2_architecture import (
                    GenreTechniquesLoader,
                    GenreTechniquesRenderer,
                    AIConstraintsLoader,
                    SelfCheckLoader,
                    LayeredSystemPrompt,
                    LayeredUserPrompt,
                    WritingStyleRenderer
                )
                
                # Layer 3,5-6 Loaders (从 YAML 配置文件加载)
                self._genre_loader = GenreTechniquesLoader()
                self._genre_renderer = GenreTechniquesRenderer()
                self._constraints_loader = AIConstraintsLoader()
                self._selfcheck_loader = SelfCheckLoader()
                
                # Layer 4 Renderer (从 YAML 加载默认风格)
                self._style_renderer = WritingStyleRenderer()
                
                # Layered Prompt Classes
                self._LayeredSystemPrompt = LayeredSystemPrompt
                self._LayeredUserPrompt = LayeredUserPrompt
                
                logger.info("[V2适配器] V2组件加载成功 (Layer 3,5-6 从YAML; Layer 1-2,4 从项目信息)")
            except ImportError as e:
                logger.warning(f"[V2适配器] V2组件加载失败: {e}")
                self._genre_loader = None
    
    def build_system_prompt_v2(self, chapter_num: int = 1) -> str:
        """
        构建 V2 System Prompt (Layer 3-4)
        注意: Layer 1-2 是从项目信息动态构建的，见 build_full_system_prompt_v2()
        
        Args:
            chapter_num: 章节号
            
        Returns:
            System Prompt 字符串
        """
        self._init_v2_components()
        
        if self._genre_loader is None:
            logger.warning("[V2适配器] V2组件不可用，回退到传统模式")
            return None
        
        try:
            # 加载 Layer 3: 题材技法（从配置文件）
            genre_data = self._genre_loader.load(self.genre)
            layer3_content = self._genre_renderer.render(genre_data)
            
            # 加载 Layer 4: 文风技法（使用项目写作风格，如果没有则使用默认值）
            layer4_content = self._build_layer4_from_style({})
            
            # 构建分层 System Prompt
            system_prompt = self._LayeredSystemPrompt(
                layer1_core_setting="",  # Layer 1 从项目信息构建
                layer2_tactical_planning="",  # Layer 2 从项目信息构建
                layer3_genre_techniques=layer3_content,
                layer4_writing_style=layer4_content
            )
            
            # 只使用 Layer 3-4 (题材技法 + 文风)
            result = system_prompt.combine([3, 4])
            
            logger.info(f"[V2适配器] System Prompt (Layer 3-4) 构建成功 | 题材: {self.genre} | 长度: {len(result)} 字符")
            return result
            
        except Exception as e:
            logger.error(f"[V2适配器] 构建 System Prompt 失败: {e}")
            return None
    
    def build_user_prompt_v2(self, 
                             chapter_num: int,
                             chapter_plan: Dict,
                             emotion_beat: Dict,
                             prev_summary: str = "") -> str:
        """
        构建 V2 User Prompt (Layer 5 + Layer 6 + 任务指令)
        
        Args:
            chapter_num: 章节号
            chapter_plan: 章节规划
            emotion_beat: 情绪节拍
            prev_summary: 上一章摘要
            
        Returns:
            User Prompt 字符串
        """
        self._init_v2_components()
        
        if self._constraints_loader is None:
            logger.warning("[V2适配器] V2组件不可用，回退到传统模式")
            return None
        
        try:
            # 加载 Layer 5: AI约束
            constraints = self._constraints_loader.load()
            layer5_content = self._format_constraints(constraints, chapter_num)
            
            # 添加情绪曲线 (Layer 5 的一部分)
            emotion_curve = self._get_emotion_curve(chapter_plan)
            layer5_content = f"{layer5_content}\n\n{emotion_curve}"
            
            # 加载 Layer 6: 自检清单
            selfcheck = self._selfcheck_loader.load()
            layer6_content = self._format_selfcheck(selfcheck)
            
            # 构建任务指令
            task_instruction = self._build_task_instruction(
                chapter_num=chapter_num,
                chapter_plan=chapter_plan,
                prev_summary=prev_summary
            )
            
            # 构建分层 User Prompt
            user_prompt = self._LayeredUserPrompt(
                layer5_ai_constraints=layer5_content,
                layer6_self_check=layer6_content,
                task_instruction=task_instruction
            )
            
            result = user_prompt.combine()
            
            logger.info(f"[V2适配器] User Prompt 构建成功 | 第{chapter_num}章 | 长度: {len(result)} 字符")
            return result
            
        except Exception as e:
            logger.error(f"[V2适配器] 构建 User Prompt 失败: {e}")
            return None
    
    def _format_constraints(self, constraints, chapter_num: int) -> str:
        """格式化 AI 约束 - Layer 5"""
        lines = ["## 【Layer 5】AI约束 + 情绪曲线 + 输出格式 + 结尾模板"]
        lines.append("")
        
        # 字数约束
        lines.append("### 【Layer 5.1】字数约束")
        if hasattr(constraints, 'word_count') and constraints.word_count:
            wc = constraints.word_count
            lines.append(f"- 目标：{wc.target}字")
            lines.append(f"- 范围：{wc.min}-{wc.max}字")
        
        # 格式约束
        lines.append("")
        lines.append("### 【Layer 5.2】格式约束")
        if hasattr(constraints, 'format_rules') and constraints.format_rules:
            fmt = constraints.format_rules
            lines.append(f"- 对话包裹：{fmt.dialogue_wrapper}")
            lines.append(f"- 系统提示包裹：{fmt.system_wrapper}")
            lines.append(f"- 段落最大行数：{fmt.paragraph_max_lines}")
        
        # 🔥 输出格式（Layer 5 的关键部分）
        lines.extend([
            "",
            "### 【Layer 5.3】输出格式（必须严格遵守）",
            "",
            "必须按以下格式返回，使用 ---标题--- 和 ---正文--- 分隔：",
            "",
            "```",
            "---标题---",
            "章节标题（8-14字，概括核心爽点，不要'第X章'前缀）",
            "",
            "---正文---",
            "章节正文内容（2000-2500字，直接写场景）",
            "```",
            "",
            "### 【Layer 5.3b】格式规范",
            "- 角色对话：用引号\"\"包裹",
            "- 系统提示/弹幕：用【】包裹",
            "- 段落：每段不超过4行",
        ])
        
        # 🔥 结尾模板（新增）
        ending_template = self._build_ending_template(constraints)
        if ending_template:
            lines.extend(["", ending_template])
        
        # 禁止事项
        lines.extend([
            "",
            "### 【Layer 5.5】🚫 禁止事项",
            "- 爽点回退（爽后突然压抑）",
            "- 预告欺诈（章尾预告不兑现）",
            "- 人设崩塌",
            "- 正文开头写'第X章'",
            "- 严禁使用'起-承-转-合'节奏",
            "- 章尾以'完'/'结束'/'休息'等词结尾",
        ])
        
        return "\n".join(lines)
    
    def _build_ending_template(self, constraints) -> str:
        """构建结尾模板 - Layer 5.4"""
        # 从 constraints 获取结尾模板配置
        ending_config = None
        if hasattr(constraints, 'ending_template'):
            ending_config = constraints.ending_template
        elif isinstance(constraints, dict):
            ending_config = constraints.get('ending_template')
        
        if not ending_config:
            # 使用默认结尾模板
            return self._get_default_ending_template()
        
        lines = []
        
        # 标题
        title = ending_config.get('title', '【番茄爆款结尾模板 - 必须遵循】')
        lines.append(f"### 【Layer 5.4】{title}")
        lines.append("")
        
        # 描述
        description = ending_config.get('description', '章节最后100-150字必须是强力钩子')
        lines.append(f"> {description}")
        lines.append("")
        
        # 模板列表
        templates = ending_config.get('templates', [])
        if templates:
            lines.append("**5种结尾模板（根据剧情选择最合适的1种）：**")
            lines.append("")
            for i, tmpl in enumerate(templates, 1):
                tmpl_id = tmpl.get('id', f'template_{i}')
                tmpl_name = tmpl.get('name', f'模板{i}')
                tmpl_desc = tmpl.get('description', '')
                tmpl_example = tmpl.get('example', '')
                
                lines.append(f"**模板{i}-{tmpl_name}：**")
                lines.append(f"- 类型：{tmpl_desc}")
                lines.append(f"- 示例：{tmpl_example}")
                lines.append("")
        
        # 规则
        rules = ending_config.get('rules', [])
        if rules:
            lines.append("**结尾规则：**")
            for rule in rules:
                lines.append(f"- {rule}")
            lines.append("")
        
        # 选择指南
        selection_guide = ending_config.get('selection_guide', '')
        if selection_guide:
            lines.append(selection_guide)
        
        return "\n".join(lines)
    
    def _get_default_ending_template(self) -> str:
        """获取默认结尾模板"""
        return """### 【Layer 5.4】番茄爆款结尾模板

> 章节最后100-150字必须是强力钩子，从以下5种模板中选择1种：

**模板1-危机降临型（推荐）：**主角刚成功→突然→新危机出现→悬念截止
示例：苏白刚收好战利品，突然——【全球通告】警告！检测到SS级凶兽正在接近！白月魁脸色骤变："快走！那是..."

**模板2-身份揭露型：**关键时刻→有人即将发现真相→揭露前截止
示例："等等！"白月魁突然盯着苏白，"你刚才用的那招...根本不是盲人的战斗方式！"苏白心中一凛...

**模板3-系统提示型：**完成某事→系统提示→出乎意料的奖励/惩罚
示例：【叮！恭喜宿主完成隐藏任务！】【奖励：扮演度+20%】但紧接着——【警告：您已被标记为SS级目标！】

**模板4-时间锁型：**倒计时开始→时间紧迫→截止
示例：【系统提示】禁地第二区域即将开启，倒计时：23小时59分。【警告】第二区域难度提升100%！

**模板5-对峙爆发型：**正面对峙→剑拔弩张→动手前一秒截止
示例：约翰带着人堵住洞口："终于找到你了，龙国的瞎子。"苏白站起身，嘴角勾起冷笑："你确定要在这里动手？"

**【结尾禁忌】**
- 禁止以"完"/"结束"/"休息"/"晚安"等词结尾
- 最后50字必须是悬念
"""
    
    def _get_emotion_curve(self, chapter_plan: Dict) -> str:
        """获取情绪曲线文本"""
        # 处理 chapter_plan 是 list 的情况
        if isinstance(chapter_plan, list):
            logger.warning(f"[V2适配器] chapter_plan 是列表类型，取第一个元素")
            chapter_plan = chapter_plan[0] if chapter_plan else {}
        
        # 确保是字典
        if not isinstance(chapter_plan, dict):
            logger.warning(f"[V2适配器] chapter_plan 不是字典，使用默认值")
            chapter_plan = {}
        
        # 从章节规划中获取情绪类型
        chapter_type = chapter_plan.get('chapter_type', '')
        emotion = chapter_plan.get('emotion', '期待')
        intensity = chapter_plan.get('intensity', 6)
        beat_type = chapter_plan.get('beat_type', '铺垫')
        
        # 映射到 V2 情绪曲线类型
        emotion_map = {
            '打脸章': '打脸章',
            '爽点': '爆发章',
            '爆发': '爆发章',
            '反转': '爆发章',
            '收获': '收获章',
            'SETUP': '铺垫章',
            '铺垫': '铺垫章',
            '危机': '危机章',
        }
        
        chapter_type_mapped = emotion_map.get(beat_type, '打脸章')
        
        # 情绪曲线模板
        emotion_templates = {
            "打脸章": {
                "curve": "虐(4)→急(7)→爽(9)→悬(7)",
                "breakdown": [
                    {"position": "0-20%", "emotion": "虐", "intensity": 4, "technique": "铺垫压抑场景"},
                    {"position": "20-50%", "emotion": "急", "intensity": 7, "technique": "冲突升级"},
                    {"position": "50-80%", "emotion": "爽", "intensity": 9, "technique": "主角反击高潮"},
                    {"position": "80-100%", "emotion": "悬", "intensity": 7, "technique": "结尾留钩子"},
                ]
            },
            "爆发章": {
                "curve": "蓄(3)→爆(10)→收(5)",
                "breakdown": [
                    {"position": "0-30%", "emotion": "蓄势", "intensity": 3, "technique": "铺垫积累"},
                    {"position": "30-70%", "emotion": "爆发", "intensity": 10, "technique": "全力释放高潮"},
                    {"position": "70-100%", "emotion": "收尾", "intensity": 5, "technique": "结果展示+悬念"},
                ]
            },
            "收获章": {
                "curve": "争(6)→得(8)→惊(7)",
                "breakdown": [
                    {"position": "0-30%", "emotion": "争夺", "intensity": 6, "technique": "多方竞争"},
                    {"position": "30-70%", "emotion": "获得", "intensity": 8, "technique": "主角得到宝物"},
                    {"position": "70-100%", "emotion": "震惊", "intensity": 7, "technique": "众人反应"},
                ]
            },
            "危机章": {
                "curve": "安(3)→危(8)→逃(6)",
                "breakdown": [
                    {"position": "0-20%", "emotion": "安稳", "intensity": 3, "technique": "平静开局"},
                    {"position": "20-60%", "emotion": "危机", "intensity": 8, "technique": "突发危机"},
                    {"position": "60-100%", "emotion": "逃脱", "intensity": 6, "technique": "惊险脱身"},
                ]
            },
            "铺垫章": {
                "curve": "平(4)→伏(5)→引(6)",
                "breakdown": [
                    {"position": "0-40%", "emotion": "平静", "intensity": 4, "technique": "日常描写"},
                    {"position": "40-80%", "emotion": "伏笔", "intensity": 5, "technique": "埋设线索"},
                    {"position": "80-100%", "emotion": "引子", "intensity": 6, "technique": "引出下文"},
                ]
            },
        }
        
        data = emotion_templates.get(chapter_type_mapped, emotion_templates["打脸章"])
        
        lines = ["### 【Layer 5.6】情绪节奏规划"]
        lines.append(f"- 章节类型: {chapter_type_mapped}")
        lines.append(f"- 情绪强度: {intensity}/10")
        lines.append(f"- 整体曲线: {data['curve']}")
        lines.append("")
        lines.append("#### 分段情绪点位:")
        for point in data['breakdown']:
            lines.append(f"  - **{point['position']}**: {point['emotion']} ({point['intensity']}分) - {point['technique']}")
        
        return "\n".join(lines)
    
    def _format_selfcheck(self, selfcheck) -> str:
        """格式化自检清单 - Layer 6"""
        lines = ["## 【Layer 6】自检清单（生成后必须完成）"]
        lines.append("")
        
        # 写前自检
        lines.append("### 【Layer 6.1】写前确认")
        if hasattr(selfcheck, 'pre_writing') and selfcheck.pre_writing:
            for item in selfcheck.pre_writing[:3]:
                item_text = item.item if hasattr(item, 'item') else str(item)
                mark = "🔴" if getattr(item, 'critical', False) else "⚪"
                lines.append(f"□ {mark} {item_text}")
        else:
            lines.append(f"□ 确认本章题材为'{self.genre}'，无禁用元素混入")
            lines.append(f"□ 确认主角姓名、人设与核心设定一致")
            lines.append(f"□ 确认已理解本章情绪曲线规划")
        
        # 格式检查
        lines.append("")
        lines.append("### 【Layer 6.2】写作后-格式检查")
        if hasattr(selfcheck, 'post_writing_format') and selfcheck.post_writing_format:
            for item in selfcheck.post_writing_format[:3]:
                item_text = item.item if hasattr(item, 'item') else str(item)
                severity = getattr(item, 'severity', 'warning')
                severity_mark = {"critical": "🔴", "warning": "🟡"}.get(severity, "⚪")
                lines.append(f"□ {severity_mark} {item_text}")
        else:
            lines.append("□ 🔴 字数是否在2000-2500范围内")
            lines.append("□ 🟡 对话占比是否≥50%")
            lines.append("□ 🔴 是否正确使用 ---标题--- / ---正文--- 分隔符")
        
        # 内容检查
        lines.append("")
        lines.append("### 【Layer 6.3】写作后-内容检查")
        if hasattr(selfcheck, 'post_writing_content') and selfcheck.post_writing_content:
            for item in selfcheck.post_writing_content[:3]:
                item_text = item.item if hasattr(item, 'item') else str(item)
                lines.append(f"□ {item_text}")
        else:
            lines.append("□ 情节是否按blueprint执行")
            lines.append("□ 爽点是否到位")
            lines.append("□ 钩子是否有效")
        
        # 题材特定检查
        lines.append("")
        lines.append("### 【Layer 6.4】写作后-题材检查")
        if hasattr(selfcheck, 'post_writing_genre') and selfcheck.post_writing_genre:
            for item in selfcheck.post_writing_genre[:3]:
                item_text = item.item if hasattr(item, 'item') else str(item)
                lines.append(f"□ {item_text}")
        else:
            if "神豪" in self.genre:
                lines.append("□ 🔴 神豪文：精确金额≥3处，精确到分")
                lines.append("□ 🔴 神豪文：系统提示音格式正确【叮！...】")
                lines.append("□ 🟡 神豪文：路人价格计算反应")
            elif "国运" in self.genre:
                lines.append("□ 🔴 国运文：弹幕数量≥8条")
                lines.append("□ 🔴 国运文：国运值/排名变化展示")
                lines.append("□ 🟡 国运文：全球直播反应链")
        
        return "\n".join(lines)
    
    def _load_character_design_from_project(self, project_path: str) -> Dict:
        """
        从项目文件加载角色设计
        
        Args:
            project_path: 项目路径
            
        Returns:
            角色设计字典
        """
        try:
            from pathlib import Path
            
            # 可能的文件路径
            possible_paths = [
                Path(project_path) / "phase_one_products" / "角色设计.json",
                Path(project_path) / "phase_one_products" / "character_design.json",
                Path(project_path) / "products" / "角色设计.json",
            ]
            
            for file_path in possible_paths:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        logger.info(f"[V2适配器] 从 {file_path.name} 加载角色设计成功")
                        return data
            
            logger.debug(f"[V2适配器] 未找到角色设计文件，路径: {project_path}")
            return {}
            
        except Exception as e:
            logger.warning(f"[V2适配器] 加载角色设计失败: {e}")
            return {}
    
    def _load_golden_finger_from_project(self, project_path: str) -> Dict:
        """
        从项目文件加载金手指设定
        
        Args:
            project_path: 项目路径
            
        Returns:
            金手指设定字典
        """
        try:
            from pathlib import Path
            
            # 可能的文件路径（按优先级排序）
            possible_paths = [
                Path(project_path) / "phase_one_products" / "金手指设计.json",  # 标准格式（推荐）
                Path(project_path) / "phase_one_products" / "金手指设定.json",  # 兼容旧命名
                Path(project_path) / "phase_one_products" / "golden_finger.json",  # 英文文件名
                Path(project_path) / "phase_one_products" / "plan.json",  # plan 文件中可能包含 golden_finger
            ]
            
            for file_path in possible_paths:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # 如果加载的是 plan.json，提取 golden_finger 字段
                        if file_path.name == "plan.json":
                            gf_data = data.get('golden_finger', {})
                            if gf_data:
                                logger.info(f"[V2适配器] 从 plan.json 加载金手指设定成功")
                                return gf_data
                        else:
                            logger.info(f"[V2适配器] 从 {file_path.name} 加载金手指设定成功")
                            return data
            
            logger.debug(f"[V2适配器] 未找到金手指设定文件，路径: {project_path}")
            return {}
            
        except Exception as e:
            logger.warning(f"[V2适配器] 加载金手指设定失败: {e}")
            return {}
    
    def _build_task_instruction(self,
                               chapter_num: int,
                               chapter_plan: Dict,
                               prev_summary: str) -> str:
        """
        构建任务指令
        
        支持从多种数据结构中提取章节规划：
        1. 直接的章节字典：{'title': '...', 'event': '...'}
        2. 包含 chapters 数组的字典：{'chapters': [{'chapter_number': 1, ...}, ...]}
        3. 战术规划格式：{'tactical_plan': {'chapters': [...]}}
        """
        # 处理 chapter_plan 是 list 的情况
        if isinstance(chapter_plan, list):
            # 如果是列表，尝试找到对应 chapter_num 的章节
            for ch in chapter_plan:
                if isinstance(ch, dict) and ch.get('chapter_number') == chapter_num:
                    chapter_plan = ch
                    break
            else:
                # 没找到对应章节，使用第一个
                chapter_plan = chapter_plan[0] if chapter_plan else {}
        
        # 确保是字典
        if not isinstance(chapter_plan, dict):
            chapter_plan = {}
        
        # 🔥 如果 chapter_plan 包含 chapters 数组，从中提取当前章节
        if 'chapters' in chapter_plan and isinstance(chapter_plan['chapters'], list):
            chapters = chapter_plan['chapters']
            # 查找对应 chapter_num 的章节
            for ch in chapters:
                if isinstance(ch, dict) and ch.get('chapter_number') == chapter_num:
                    # 合并父级规划和章节特定规划
                    merged_plan = {**chapter_plan, **ch}
                    chapter_plan = merged_plan
                    break
        
        # 从 tactical_plan.chapters 中提取（如果有）
        tactical_plan = chapter_plan.get('tactical_plan', {})
        if isinstance(tactical_plan, dict) and 'chapters' in tactical_plan:
            for ch in tactical_plan['chapters']:
                if isinstance(ch, dict) and ch.get('chapter_number') == chapter_num:
                    merged_plan = {**chapter_plan, **ch}
                    chapter_plan = merged_plan
                    break
        
        # 🔥 提取字段（支持多种字段名）
        title = chapter_plan.get('title') or chapter_plan.get('chapter_title') or f'第{chapter_num}章'
        
        # 本章事件（支持多种字段名）
        event = (chapter_plan.get('event') or 
                chapter_plan.get('main_event') or 
                chapter_plan.get('plot') or
                chapter_plan.get('content', ''))
        
        # 爽点设计（支持多种字段名）
        satisfaction_point = (chapter_plan.get('satisfaction_point') or 
                             chapter_plan.get('burst_point') or 
                             chapter_plan.get('爽点') or
                             chapter_plan.get('satisfaction', ''))
        
        # 打脸设计（支持多种字段名）
        face_slapping = (chapter_plan.get('face_slapping') or 
                        chapter_plan.get('打脸') or
                        chapter_plan.get('反派', ''))
        
        # 章尾钩子（支持多种字段名）
        hook_content = (chapter_plan.get('hook_content') or 
                       chapter_plan.get('hook') or 
                       chapter_plan.get('chapter_hook') or
                       chapter_plan.get('ending_hook', ''))
        
        # 🔥 从 beat_type / emotion_beat 推导情绪目标
        beat_type = chapter_plan.get('beat_type', '爽点')
        emotion_target = chapter_plan.get('emotion', '爽快')
        intensity = chapter_plan.get('intensity', 8)
        
        # 🔥 构建任务指令（极简版 - Layer 2 已有详细规划，此处只保留执行指令）
        lines = [
            "## 【任务指令】开始生成",
            "",
            f"**第 {chapter_num} 章** | {title} | {beat_type}（强度{intensity}/10）",
            "",
            "**执行要求：**",
            "1. 严格遵循 Layer 1-6 的所有约束",
            "2. 承接 Layer 2.2 的钩子（前300字必须处理）",
            "3. 使用 Layer 3 的题材技法",
            "4. 遵循 Layer 4 的文风规范",
            "5. 按 Layer 5.4 的模板写章尾钩子",
            "6. 完成 Layer 6 的自检清单",
            "7. 只输出章节正文，不要大纲/分析",
            "",
        ]
        
        # 前章回顾（仅在存在时显示，用于上下文衔接）
        if prev_summary:
            # 只保留前80字作为上下文提示
            summary_short = prev_summary[:80] + "..." if len(prev_summary) > 80 else prev_summary
            lines.extend([
                "**前章衔接**：" + summary_short,
                "",
            ])
        
        lines.extend([
            "请开始生成章节内容：",
            "",
        ])
        
        return "\n".join(lines)
    
    def _build_layer1_core_setting(self, world_state: Dict = None, project_path: str = None) -> str:
        """
        从 novel_data 构建 Layer 1 核心设定
        包含：主角人设、核心角色阵容、金手指设定、世界状态
        
        Args:
            world_state: 世界状态（角色状态、系统状态、活跃剧情线索等）
            project_path: 项目路径（用于加载角色设计等产物文件）
        """
        lines = ["## 【Layer 1】核心设定（宪法级，全文遵守）"]
        lines.append("")
        
        # 尝试从 novel_data 提取核心设定
        character_design = self.novel_data.get('character_design', {})
        
        # 🔥 如果 novel_data 中没有 character_design，尝试从项目文件加载
        if not character_design and project_path:
            character_design = self._load_character_design_from_project(project_path)
            if character_design:
                logger.info(f"[V2适配器] 从项目文件加载角色设计成功")
        
        protagonist = character_design.get('protagonist', {}) if isinstance(character_design, dict) else {}
        golden_finger = self.novel_data.get('golden_finger', {}) or self.novel_data.get('golden_finger_summary', '')
        
        # 🔥 同样尝试从项目文件加载金手指设定
        if not golden_finger and project_path:
            golden_finger = self._load_golden_finger_from_project(project_path)
        
        # 🔥 主角信息 - 优先从 character_design.protagonist 获取
        protagonist_name = "主角"  # 默认
        protagonist_identity = "神豪/国运绑定者"
        protagonist_traits = ["冷静理智", "杀伐果断", "极致护短"]
        forbidden_behaviors = ["圣母行为", "情绪失控", "暴露全部底牌"]
        unique_label = ""
        
        if isinstance(protagonist, dict) and protagonist.get('name'):
            # 新格式：从 protagonist 对象获取
            protagonist_name = protagonist.get('name', protagonist_name)
            protagonist_identity = protagonist.get('identity', protagonist_identity)
            # traits 可能是列表或字符串
            traits = protagonist.get('traits', [])
            if isinstance(traits, list) and traits:
                protagonist_traits = traits
            elif isinstance(traits, str):
                protagonist_traits = [t.strip() for t in traits.split(',') if t.strip()]
            # 唯一标签/人设描述
            unique_label = protagonist.get('unique_label', '')
            # 禁止行为
            forbidden = protagonist.get('forbidden', [])
            if isinstance(forbidden, list) and forbidden:
                forbidden_behaviors = forbidden
        elif 'suggestions' in self.novel_data and isinstance(self.novel_data['suggestions'], dict):
            # 旧格式：从 suggestions 获取
            protagonist_name = self.novel_data['suggestions'].get('name', protagonist_name)
        
        lines.append("### 【Layer 1.1】主角人设（绝对不可更改）")
        lines.append(f"- **姓名**：{protagonist_name}")
        lines.append(f"- **当前身份**：{protagonist_identity}")
        lines.append(f"- **核心特质**：{', '.join(protagonist_traits)}")
        lines.append(f"- **禁止行为**：{', '.join(forbidden_behaviors)}")
        if unique_label:
            lines.append(f"- **人设标签**：{unique_label}")
        lines.append("")
        
        # 🔥 Layer 1.1b 核心角色阵容（从 character_design 获取）
        lines.append("### 【Layer 1.1b】核心角色阵容（本章可能涉及）")
        
        # 核心盟友
        core_allies = character_design.get('core_allies', []) if isinstance(character_design, dict) else []
        if core_allies and isinstance(core_allies, list):
            lines.append("**核心盟友：**")
            for i, ally in enumerate(core_allies[:3], 1):  # 最多显示3个
                if isinstance(ally, dict):
                    ally_name = ally.get('name', f'盟友{i}')
                    ally_role = ally.get('role', '盟友')
                    ally_function = ally.get('function', '')
                    lines.append(f"- {ally_name}（{ally_role}）{ally_function}")
            lines.append("")
        
        # 主要反派
        main_antagonists = character_design.get('main_antagonists', {}) if isinstance(character_design, dict) else {}
        if main_antagonists and isinstance(main_antagonists, dict):
            lines.append("**主要反派：**")
            if 'early' in main_antagonists:
                early = main_antagonists['early']
                if isinstance(early, dict):
                    lines.append(f"- 早期反派：{early.get('description', '小人物、势利眼')}")
            if 'mid' in main_antagonists:
                mid = main_antagonists['mid']
                if isinstance(mid, dict):
                    lines.append(f"- 中期反派：{mid.get('description', '有背景的敌人')}")
            lines.append("")
        
        # 如果没有角色阵容数据，显示提示
        if not core_allies and not main_antagonists:
            lines.append("- （角色阵容数据待生成）")
            lines.append("")
        
        # 🔥 Layer 1.1c 世界状态约束（动态传入）
        if world_state and isinstance(world_state, dict):
                lines.append("### 【Layer 1.1c】世界状态约束（本章必须遵循）")
                
                # 主角当前状态
                protagonist_state = filtered_state.get('protagonist_state', {})
                if protagonist_state:
                    lines.append("**主角当前状态：**")
                    health = protagonist_state.get('health', '健康')
                    lines.append(f"- 健康: {health}")
                    
                    unlocked_abilities = protagonist_state.get('unlocked_abilities', [])
                    if unlocked_abilities:
                        lines.append(f"- 已解锁能力: {', '.join(unlocked_abilities)}")
                    lines.append("")
                
                # 系统状态
                system_state = filtered_state.get('system_state', {})
                if system_state:
                    lines.append("**系统状态：**")
                    current_level = system_state.get('current_level', '初始')
                    current_value = system_state.get('current_value', '')
                    lines.append(f"- 当前等级/阶段: {current_level}")
                    if current_value:
                        lines.append(f"- 当前能力值: {current_value}")
                    
                    sys_unlocked = system_state.get('unlocked_abilities', [])
                    if sys_unlocked:
                        lines.append(f"- 系统已解锁: {', '.join(sys_unlocked)}")
                    lines.append("")
                
                # 活跃剧情线索
                active_plots = filtered_state.get('active_plots', [])
                if active_plots:
                    lines.append("**活跃剧情线索（本章必须提及或推进）：**")
                    for plot in active_plots:
                        if isinstance(plot, dict):
                            plot_name = plot.get('name', '未命名线索')
                            plot_status = plot.get('status', '')
                            plot_hint = plot.get('hint', '')
                            status_str = f" [{plot_status}]" if plot_status else ""
                            hint_str = f" - {plot_hint}" if plot_hint else ""
                            lines.append(f"- {plot_name}{status_str}{hint_str}")
                        elif isinstance(plot, str):
                            lines.append(f"- {plot}")
                    lines.append("")
                
                # 约束规则
                lines.append("**【约束规则】**")
                lines.append("1. 必须保持上述角色状态与系统状态一致")
                lines.append("2. 不能突然解锁未获得的能力")
                if active_plots:
                    lines.append("3. 活跃的剧情线索需要在文中体现（至少提及）")
                    lines.append("4. 能力/等级变化需要有合理过渡，不能突变")
                lines.append("")
        
        # 🔥 金手指信息 - 优先从 golden_finger 对象获取完整信息
        # 🔥 Layer 1.2 金手指设定（支持标准金手指设计文件格式）
        lines.append("### 【Layer 1.2】金手指设定")
        if isinstance(golden_finger, dict):
            # 判断是否为标准金手指设计文件格式
            is_standard_format = 'core_mechanism' in golden_finger or 'activation' in golden_finger
            
            if is_standard_format:
                # 标准格式（来自金手指设计.json）
                gf_name = golden_finger.get('name', '系统')
                gf_type = golden_finger.get('type', '系统流')
                gf_core = golden_finger.get('core_mechanism', '')
                
                lines.append(f"- **名称**：{gf_name}")
                lines.append(f"- **类型**：{gf_type}")
                lines.append(f"- **核心机制**：{gf_core}")
                
                # 激活条件
                activation = golden_finger.get('activation', {})
                if activation:
                    lines.append(f"- **激活条件**：{activation.get('trigger', '自动激活')}")
                    if activation.get('initial_reward'):
                        lines.append(f"- **初始奖励**：{activation.get('initial_reward')}")
                
                # 能力阶段
                abilities = golden_finger.get('abilities', [])
                if abilities:
                    lines.append("- **能力阶段**：")
                    for ab in abilities[:3]:  # 最多显示3个阶段
                        stage = ab.get('stage', '')
                        ability = ab.get('ability', '')
                        lines.append(f"  - {stage}：{ability}")
                
                # 升级体系
                upgrade = golden_finger.get('upgrade_system', {})
                if upgrade:
                    lines.append(f"- **升级体系**：{upgrade.get('metric', '经验值')} - {upgrade.get('formula', '')}")
                
                # 限制条件（重要！）
                limitations = golden_finger.get('limitations', [])
                if limitations:
                    lines.append("- **限制条件**（必须遵守）：")
                    for i, lim in enumerate(limitations[:3], 1):
                        lines.append(f"  {i}. {lim}")
                
                # 系统提示音
                reward_sound = golden_finger.get('reward_sound', '')
                if reward_sound:
                    lines.append(f"- **系统提示音模板**：{reward_sound}")
                
                # 特殊机制
                special = golden_finger.get('special_mechanics', [])
                if special:
                    lines.append("- **特殊机制**：")
                    for sp in special[:2]:
                        sp_name = sp.get('name', '')
                        sp_desc = sp.get('description', '')
                        lines.append(f"  - {sp_name}：{sp_desc}")
                
                # 叙事指导
                guidelines = golden_finger.get('narrative_guidelines', [])
                if guidelines:
                    lines.append("- **叙事要求**：")
                    for guide in guidelines[:3]:
                        lines.append(f"  - {guide}")
            else:
                # 简化格式（来自 plan.json）
                gf_name = golden_finger.get('name', '每日盲盒系统')
                gf_concept = golden_finger.get('concept', golden_finger.get('description', '通过系统不断变强'))
                gf_initial = golden_finger.get('initial', '系统激活，获得基础能力')
                gf_trigger = golden_finger.get('trigger_mechanism', '完成任务获得奖励')
                gf_upgrade = golden_finger.get('upgrade_formula', '通过使用不断提升，解锁更强能力')
                gf_limitations = golden_finger.get('limitations', [])
                
                lines.append(f"- **名称**：{gf_name}")
                lines.append(f"- **核心机制**：{gf_concept}")
                lines.append(f"- **初始能力**：{gf_initial}")
                lines.append(f"- **触发方式**：{gf_trigger}")
                lines.append(f"- **成长公式**：{gf_upgrade}")
                if isinstance(gf_limitations, list) and gf_limitations:
                    lines.append(f"- **限制条件**：{', '.join(gf_limitations[:3])}")
        elif isinstance(golden_finger, str) and golden_finger:
            lines.append(f"- **核心机制**：{golden_finger}")
        else:
            lines.append("- **名称**：每日盲盒系统")
            lines.append("- **核心机制**：每日零点开启盲盒，消费获得随机奖励")
            lines.append("- **初始能力**：系统激活，获得基础返利能力")
            lines.append("- **触发方式**：消费、完成任务")
            lines.append("- **成长公式**：通过消费和任务提升系统等级，解锁更强奖励")
        lines.append("")
        
        # 🔥 从题材配置加载 Layer 1.3-1.5（直接读取YAML原始数据）
        import yaml
        from pathlib import Path
        
        genre_config = {}
        if "神豪" in self.genre:
            genre_file = "神豪文.yaml"
        elif "国运" in self.genre:
            genre_file = "国运文.yaml"
        elif "甜宠" in self.genre:
            genre_file = "甜宠文.yaml"
        elif "虐恋" in self.genre:
            genre_file = "虐恋文.yaml"
        elif "穿越" in self.genre:
            genre_file = "穿越文.yaml"
        elif "重生" in self.genre:
            genre_file = "重生文.yaml"
        else:
            genre_file = f"{self.genre}.yaml"
        
        # 获取配置路径（优先用户配置，其次系统默认）
        config_path = self._get_genre_config_path(genre_file)
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    genre_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"[V2适配器] 加载题材配置失败: {e}")
        
        # Layer 1.3: 世界核心规则（从配置或动态生成）
        lines.append("### 【Layer 1.3】世界核心规则")
        world_rules = genre_config.get('world_rules', [])
        if world_rules:
            for rule in world_rules:
                if isinstance(rule, dict):
                    rule_name = rule.get('name', '')
                    rule_desc = rule.get('description', '')
                    lines.append(f"- **{rule_name}**：{rule_desc}")
                elif isinstance(rule, str):
                    lines.append(f"- {rule}")
        else:
            # 根据题材生成默认规则
            if '神豪' in self.genre:
                lines.append("- **金钱即权力**：资本可以影响规则，对抗超自然力量")
                lines.append("- **高维观察者存在**：存在超越人类的观察者，会关注表现突出的个体")
                lines.append("- **系统规则**：消费返利，完成任务获得奖励")
            elif '国运' in self.genre:
                lines.append("- **国运绑定**：主角与国家命运绑定，一荣俱荣")
                lines.append("- **直播规则**：全球直播，全国人民能看到主角表现")
                lines.append("- **扮演系统**：通过扮演角色获得能力")
            elif '甜宠' in self.genre:
                lines.append("- **真爱至上**：真爱可以战胜一切障碍")
                lines.append("- **男主专一**：男主必须专一深情，只爱女主")
                lines.append("- **高糖低虐**：80%甜+20%小波折，不能真虐")
            else:
                lines.append("- **系统规则**：金手指辅助主角成长")
                lines.append("- **爽文原则**：主角最终必胜，反派必败")
        lines.append("")
        
        # Layer 1.4: 核心卖点（从配置或动态生成）
        lines.append("### 【Layer 1.4】核心卖点（必须体现）")
        selling_points = genre_config.get('selling_points', [])
        if selling_points:
            for point in selling_points[:5]:  # 最多5个
                if isinstance(point, dict):
                    point_name = point.get('name', '')
                    point_desc = point.get('description', '')
                    lines.append(f"- **{point_name}**：{point_desc}")
                elif isinstance(point, str):
                    lines.append(f"- {point}")
        else:
            # 根据题材生成默认卖点
            if '神豪' in self.genre:
                lines.append("- **金钱碾压**：用金钱碾压一切，享受极致的降维打击")
                lines.append("- **身份反转**：从底层到顶层的身份转变带来的反差爽感")
                lines.append("- **护短报仇**：有恩必报，有仇必清算")
            elif '国运' in self.genre:
                lines.append("- **为国争光**：为国家争取荣誉，提升国运")
                lines.append("- **全球震惊**：让全世界为龙国震惊")
                lines.append("- **扮演升级**：通过扮演历史人物获得能力")
            elif '甜宠' in self.genre:
                lines.append("- **高糖互动**：男主宠妻无底线，各种甜蜜互动")
                lines.append("- **护短打脸**：男主不允许任何人欺负女主")
                lines.append("- **身份反差**：男主对外冷酷，对女主温柔")
            else:
                lines.append("- **升级爽感**：主角不断变强的成就感")
                lines.append("- **打脸反派**：让看不起主角的人后悔")
        lines.append("")
        
        # Layer 1.5: 爽点公式（从配置或动态生成）
        lines.append("### 【Layer 1.5】爽点公式（严格执行）")
        satisfaction_formula = genre_config.get('satisfaction_formula', [])
        if satisfaction_formula:
            lines.append("```")
            for step in satisfaction_formula:
                lines.append(step)
            lines.append("```")
        else:
            # 根据题材生成默认爽点公式
            if '甜宠' in self.genre:
                lines.append("```")
                lines.append("互动（暧昧/撩拨）→ 升温（肢体接触）→ ")
                lines.append("小波折（吃醋/误会）→ 和解（甜蜜和好）→ ")
                lines.append("撒糖（高甜互动）→ 钩子（新的期待）")
                lines.append("```")
            else:
                lines.append("```")
                lines.append("压抑（反派嚣张）→ 铺垫（主角准备）→ ")
                lines.append("反转（展示实力）→ 高潮（反派崩溃）→ ")
                lines.append("收获（获得奖励）→ 钩子（新危机出现）")
                lines.append("```")
        lines.append("")
        
        return "\n".join(lines)
    
    def _build_layer2_tactical_planning(self, chapter_num: int, chapter_plan: Dict, 
                                        prev_hook: str = None, cross_batch_hook: str = None) -> str:
        """
        构建 Layer 2 战术规划
        
        Args:
            chapter_num: 章节号
            chapter_plan: 章节规划
            prev_hook: 上一章结尾钩子（用于承接）
            cross_batch_hook: 跨批次钩子（如果是新批次的第1章）
        """
        lines = ["## 【Layer 2】战术规划（批次级，本章执行）"]
        lines.append("")
        
        # 当前阶段
        lines.append("### 【Layer 2.1】当前阶段信息")
        lines.append("- **阶段**：根据章节号自动判断")
        if chapter_num <= 10:
            lines.append("  - 初期：建立神豪身份，初步打脸")
        elif chapter_num <= 30:
            lines.append("  - 中期：势力扩张，清算敌人")
        else:
            lines.append("  - 后期：对抗高维，拯救世界")
        lines.append("")
        
        # 🔥 Layer 2.2 承接约束（上一章钩子）
        has_prev_hook = prev_hook and str(prev_hook).strip()
        has_cross_hook = cross_batch_hook and str(cross_batch_hook).strip()
        
        if has_prev_hook or has_cross_hook:
            lines.append("### 【Layer 2.2】承接约束（必须处理）")
            lines.append("⚠️ **本章开头必须承接上一章的钩子，不能跳过或忽略**")
            lines.append("")
            
            if has_cross_hook:
                lines.append(f"**跨批次钩子（第1章必须承接）：**")
                lines.append(f"> {cross_batch_hook}")
                lines.append("")
            
            if has_prev_hook:
                lines.append(f"**上一章结尾状态：**")
                # 只显示前100字，避免太长
                hook_short = prev_hook[:100] + "..." if len(str(prev_hook)) > 100 else prev_hook
                lines.append(f"> {hook_short}")
                lines.append("")
            
            lines.append("**承接要求：**")
            lines.append("1. 本章前300字必须承接上述钩子")
            lines.append("2. 不能假装什么都没发生")
            lines.append("3. 必须展示主角对钩子事件的反应或行动")
            lines.append("")
        
        # 本章战术目标
        lines.append(f"### 【Layer 2.3】第{chapter_num}章战术目标")
        
        # 从 chapter_plan 提取信息
        if isinstance(chapter_plan, dict):
            beat_type = chapter_plan.get('beat_type', '爽点')
            emotion = chapter_plan.get('emotion', '爽快')
            intensity = chapter_plan.get('intensity', 8)
            
            lines.append(f"- **章节类型**：{beat_type}")
            lines.append(f"- **情绪目标**：{emotion}（强度{intensity}/10）")
            
            # 爽点设计
            satisfaction = chapter_plan.get('satisfaction_point', '')
            if satisfaction:
                lines.append(f"- **爽点设计**：{satisfaction}")
            
            # 打脸设计
            face_slapping = chapter_plan.get('face_slapping', '')
            if face_slapping:
                lines.append(f"- **打脸设计**：{face_slapping}")
            
            # 钩子设计
            hook = chapter_plan.get('hook_content', '')
            if hook:
                lines.append(f"- **章尾钩子**：{hook}")
        
        lines.append("")
        
        # 章节结构设计
        lines.append("### 【Layer 2.4】章节结构设计")
        lines.append("```")
        lines.append("0-15%  开局：承接上文/引入冲突（300-400字）")
        lines.append("15-45% 铺垫：反派施压，主角隐忍（600-800字）")
        lines.append("45-75% 高潮：主角反击，爽点爆发（600-800字）")
        lines.append("75-90% 收获：返利到账，地位提升（400-500字）")
        lines.append("90-100%钩子：新危机/新人物/新线索（100-150字）")
        lines.append("```")
        lines.append("")
        
        # 情绪曲线
        lines.append("### 【Layer 2.5】情绪节奏控制")
        if isinstance(chapter_plan, dict):
            beat_type = chapter_plan.get('beat_type', '爽点')
            emotion_curves = {
                '打脸章': '虐(4)→急(7)→爽(9)→悬(7)',
                '爽点': '蓄(3)→爆(10)→收(5)',
                '爆发': '蓄(3)→爆(10)→收(5)',
                '反转': '平(5)→疑(6)→惊(9)→悟(7)',
                '收获': '争(6)→得(8)→惊(7)',
                '危机': '安(3)→危(8)→逃(6)',
                '铺垫': '平(4)→伏(5)→引(6)'
            }
            curve = emotion_curves.get(beat_type, '虐→急→爽→悬')
            lines.append(f"- **情绪曲线**：{curve}")
        lines.append("- **要求**：一章内情绪转变至少2次")
        lines.append("- **高潮**：情绪强度必须达到峰值")
        lines.append("")
        
        return "\n".join(lines)
    
    def _build_layer4_from_style(self, writing_style: Dict) -> str:
        """
        从项目的 writing_style 构建 Layer 4 文风技法
        
        支持两种格式:
        1. 新格式 (project_info): {style_id, style_name, style_config: {...}}
        2. 旧格式 (task): {id, name, description, features, ...}
        
        Args:
            writing_style: 项目的写作风格字典 (来自 novel_data['writing_style'] 或 project_info['writing_style'])
            
        Returns:
            Layer 4 内容字符串
        """
        # 🔥 统一提取配置：支持新格式（有 style_config 嵌套）和旧格式（扁平结构）
        if 'style_config' in writing_style:
            # 新格式：从 project_info 读取，配置在 style_config 中
            config = writing_style.get('style_config', {})
            style_name = config.get('name') or config.get('style_name') or writing_style.get('style_name', '番茄快节奏爽文')
        else:
            # 旧格式：直接从 task 读取
            config = writing_style
            style_name = config.get('name') or config.get('style_name', '番茄快节奏爽文')
        
        description = config.get('description', '快节奏、强情绪、强冲突')
        
        # 提取特征
        features = config.get('features', [])
        if isinstance(features, list) and features:
            features_str = '\n'.join([f"- {f}" for f in features[:5]])
        else:
            features_str = '- 快节奏叙事\n- 强情绪渲染\n- 高频冲突'
        
        # 提取禁忌
        taboos = config.get('taboos', [])
        if isinstance(taboos, list) and taboos:
            taboos_str = '\n'.join([f"- 禁止{t}" for t in taboos[:3]])
        else:
            taboos_str = '- 禁止注水\n- 禁止偏离主线'
        
        # 提取结构偏好
        structure = config.get('structure_preference', {})
        if isinstance(structure, dict):
            chapter_length = structure.get('chapter_length', '3000-3500字')
            pacing = structure.get('pacing', '快节奏')
            cliffhanger = structure.get('cliffhanger', '章尾强钩子')
        else:
            chapter_length = '3000-3500字'
            pacing = '快节奏'
            cliffhanger = '章尾强钩子'
        
        lines = [
            "## 【Layer 4】文风技法 - " + style_name,
            "",
            f"> {description}",
            "",
            "### 【Layer 4.1】风格特征",
            features_str,
            "",
            "### 【Layer 4.2】结构要求",
            f"- **单章长度**：{chapter_length}",
            f"- **叙事节奏**：{pacing}",
            f"- **收尾方式**：{cliffhanger}",
            "",
            "### 【Layer 4.3】段落规范",
            "- 每段3-4行，多用换行",
            "- 平均长度50-80字",
            "- 手机优先排版",
            "",
            "### 【Layer 4.4】句子规范",
            "- 短句(<10字)占比≥40%",
            "- 单句最长25字",
            "- 口语化表达，减少形容词",
            "",
            "### 【Layer 4.5】对话规范",
            "- 对话占比≥30%，用引号包裹",
            "- 一句一段，对话后接动作/反应",
            "- 禁止连续200字无对话",
            "",
            "### 【Layer 4.6】震惊流技法",
            "- 先写反应，后写原因",
            "- 层层递进，禁止跳级",
            "- 数字量化，拒绝模糊",
            "- 🚫 严禁使用'第一层/第二层'标签",
            "",
            "### 【Layer 4.7】创作禁忌",
            taboos_str,
            ""
        ]
        
        return "\n".join(lines)
    
    def build_full_system_prompt_v2(self, 
                                    chapter_num: int = 1,
                                    chapter_plan: Dict = None,
                                    writing_style: Dict = None,
                                    world_state: Dict = None,
                                    project_path: str = None,
                                    prev_hook: str = None,
                                    cross_batch_hook: str = None) -> str:
        """
        构建完整的 V2 System Prompt (Layer 1-4)
        包含从 novel_data 构建的 Layer 1-2，从writing_style构建的 Layer 4
        
        Args:
            chapter_num: 章节号
            chapter_plan: 章节规划
            writing_style: 写作风格（来自项目的写作风格系统）
            world_state: 世界状态（角色状态、系统状态、活跃剧情线索等）
            project_path: 项目路径（用于加载角色设计等产物文件）
            prev_hook: 上一章结尾钩子（用于承接）
            cross_batch_hook: 跨批次钩子（如果是新批次的第1章）
            
        Returns:
            System Prompt 字符串
        """
        self._init_v2_components()
        
        if self._genre_loader is None:
            logger.warning("[V2适配器] V2组件不可用，回退到传统模式")
            return None
        
        try:
            sections = []
            
            # Layer 1: 核心设定（从 novel_data 构建，包含 world_state 和 project_path）
            layer1_content = self._build_layer1_core_setting(
                world_state=world_state,
                project_path=project_path
            )
            sections.append(layer1_content)
            
            # Layer 2: 战术规划（从 chapter_plan 构建，包含上一章钩子承接）
            layer2_content = self._build_layer2_tactical_planning(
                chapter_num=chapter_num, 
                chapter_plan=chapter_plan or {},
                prev_hook=prev_hook,
                cross_batch_hook=cross_batch_hook
            )
            sections.append(layer2_content)
            
            # Layer 3: 题材技法
            genre_data = self._genre_loader.load(self.genre)
            layer3_content = self._genre_renderer.render(genre_data)
            sections.append(layer3_content)
            
            # Layer 4: 文风技法（从 writing_style 构建，而非YAML）
            if writing_style:
                layer4_content = self._build_layer4_from_style(writing_style)
            else:
                layer4_content = self._style_renderer.render_default()
            sections.append(layer4_content)
            
            # 组合所有层
            result = "\n\n".join(sections)
            
            logger.info(f"[V2适配器] 完整System Prompt构建成功 | 包含Layer 1-4 | 长度: {len(result)} 字符")
            return result
            
        except Exception as e:
            logger.error(f"[V2适配器] 构建完整System Prompt失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def is_available(self) -> bool:
        """检查 V2 组件是否可用"""
        self._init_v2_components()
        return self._genre_loader is not None


# ==================== 便捷函数 ====================

def create_v2_adapter(novel_data: Dict, genre: str = None) -> Optional[V2IntegrationAdapter]:
    """
    创建 V2 集成适配器
    
    Args:
        novel_data: 小说数据
        genre: 题材类型（可选，自动检测）
    
    Returns:
        V2IntegrationAdapter 实例，如果 V2 组件不可用则返回 None
    """
    adapter = V2IntegrationAdapter(novel_data, genre)
    if adapter.is_available():
        return adapter
    return None
