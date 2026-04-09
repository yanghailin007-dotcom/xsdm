"""
对话模式章节生成器
在一个连续对话中批量生成多章,保持上下文连贯

v3.0更新:
1. 使用优化后的提示词系统
2. 集成AI质检系统,生成前自动检查质量
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# 导入优化的提示词构建器(优先使用v3.0)
try:
    from .chapter_prompt_optimizer_v3 import ChapterPromptOptimizerV3 as ChapterPromptOptimizer
    HAS_OPTIMIZER = True
    OPTIMIZER_VERSION = "3.0"
    logging.info("[ChapterConversationGenerator] 已加载提示词优化器 v3.0(番茄爆款版)")
except ImportError:
    try:
        from .chapter_prompt_optimizer import ChapterPromptOptimizer
        HAS_OPTIMIZER = True
        OPTIMIZER_VERSION = "2.0"
        logging.info("[ChapterConversationGenerator] 已加载提示词优化器 v2.0")
    except ImportError:
        HAS_OPTIMIZER = False
        OPTIMIZER_VERSION = None
        logging.warning("[ChapterConversationGenerator] 提示词优化器未加载,使用传统模式")

# 导入对话日志记录器
try:
    from .market_driven_conversation import ConversationLogger
    HAS_CONVERSATION_LOGGER = True
except ImportError:
    HAS_CONVERSATION_LOGGER = False
    logging.warning("[ChapterConversationGenerator] 对话日志记录器未加载")

# 导入质量检查器
try:
    from .chapter_quality_checker import ChapterQualityChecker, format_quality_report
    HAS_QUALITY_CHECKER = True
    logging.info("[ChapterConversationGenerator] 已加载质量检查器")
except ImportError:
    HAS_QUALITY_CHECKER = False
    logging.warning("[ChapterConversationGenerator] 质量检查器未加载")

# 导入TropePromptBuilder(分层System Prompt支持)
try:
    from .trope_prompt_builder import TropePromptBuilder
    HAS_TROPE_PROMPT_BUILDER = True
    logging.info("[ChapterConversationGenerator] 已加载TropePromptBuilder")
except ImportError:
    HAS_TROPE_PROMPT_BUILDER = False
    logging.warning("[ChapterConversationGenerator] TropePromptBuilder未加载")

# 导入章节信息提取器(AI自动提取)
try:
    from .chapter_info_extractor import ChapterInfoExtractor
    HAS_INFO_EXTRACTOR = True
    logging.info("[ChapterConversationGenerator] 已加载信息提取器")
except ImportError:
    HAS_INFO_EXTRACTOR = False
    logging.warning("[ChapterConversationGenerator] 信息提取器未加载")

# 导入阶段性复盘优化器(滑动窗口版)
try:
    from .stage_review_optimizer import StageReviewOptimizer
    HAS_STAGE_REVIEW_OPTIMIZER = True
    logging.info("[ChapterConversationGenerator] 已加载阶段性复盘优化器")
except ImportError:
    HAS_STAGE_REVIEW_OPTIMIZER = False
    logging.warning("[ChapterConversationGenerator] 阶段性复盘优化器未加载")
    
# 定义备用的优化器(简化版)
class SimpleOptimizer:
    """简化版优化器(备用)"""
    def __init__(self, novel_data):
        # 确保 novel_data 是字典类型
        if isinstance(novel_data, list):
            novel_data = novel_data[0] if novel_data else {}
        if not isinstance(novel_data, dict):
            novel_data = {}
        self.novel_data = novel_data
        self._prompt_config = self._load_prompt_config()
    
    def _load_prompt_config(self) -> Dict:
        """从JSON加载提示词配置"""
        try:
            base_dir = Path(__file__).parent.parent.parent.parent
            config_file = base_dir / "prompt_packages" / "default" / "market_driven" / "components" / "conversation" / "conversation_step_prompts.json"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logging.info("[SimpleOptimizer] 加载对话提示词配置成功")
                return config
            else:
                logging.warning(f"[SimpleOptimizer] 提示词配置不存在: {config_file}")
                return {}
        except Exception as e:
            logging.error(f"[SimpleOptimizer] 加载提示词配置失败: {e}")
            return {}
    
    def build_system_prompt(self):
        """构建System Prompt - 从JSON配置加载"""
        title = self.novel_data.get('title', '未命名')
        
        # 从配置加载模板
        config = self._prompt_config.get("system_prompt", {})
        template = config.get("template", "")
        
        if not template:
            raise ValueError("[SimpleOptimizer] system_prompt 配置未找到，请检查 prompt 配置")
        
        return template.replace("{title}", title)
    
    def build_chapter_prompt(self, chapter_num, blueprint, prev_summary):
        parts = [
            f"请生成第{chapter_num}章.",
            "",
            "## 写作要求",
            "1. 字数2000-2500字",
            "2. 承接前文",
            "3. 本章必须有爽点或钩子",
            "4. 章尾留悬念",
            "",
            "## 【输出格式 - 使用分隔符】",
            "必须按以下格式返回：",
            "",
            "---标题---",
            "章节标题（8-14字，不要'第X章'前缀）",
            "---正文---",
            "章节正文内容（2000-2500字）"
        ]
        return "\n".join(parts)

logger = logging.getLogger(__name__)


class ChapterConversationGenerator:
    """
    章节对话生成器
    
    特点:
    1. 创建一个长对话会话
    2. 连续生成多章,每章都基于前文上下文
    3. 利用 Kimi 256K 上下文窗口,可连续生成 10-20 章
    4. 集成AI质检系统,生成前自动检查质量
    """
    
    # 质检配置
    QUALITY_CHECK_CONFIG = {
        "enabled": True,           # 是否启用质检
        "min_score": 70,           # 最低通过分数
        "auto_fix": True,          # 是否自动修复问题
        "stop_on_critical": True,  # 遇到严重问题是否停止
        "log_level": "info",       # 日志级别:debug/info/warning
    }
    
    # 配置路径
    CONFIG_PATH = "prompt_packages/default/market_driven/components/chapter_expansion_prompts.json"
    
    def __init__(self, api_client, novel_data: Dict, tropes: Dict, 
                 quality_config: Dict = None,
                 world_state_manager=None,  #  世界状态管理器
                 project_path: str = None,  #  项目路径
                 writing_style: Dict = None):  #  🔥 文风选择
        self.api_client = api_client
        # 确保 novel_data 是字典类型
        if isinstance(novel_data, list):
            logger.warning(f"[ChapterConversationGenerator] novel_data 是列表类型,转换为字典")
            novel_data = novel_data[0] if novel_data else {}
        if not isinstance(novel_data, dict):
            logger.warning(f"[ChapterConversationGenerator] novel_data 类型异常: {type(novel_data)},使用空字典")
            novel_data = {}
        self.novel_data = novel_data
        self.tropes = tropes
        self.writing_style = writing_style  #  🔥 保存文风设置
        self.session = None
        self.logger = None  # 对话日志记录器
        self.quality_checker = None  # 质量检查器
        self.quality_reports = []  # 质检报告列表
        self.world_state_manager = world_state_manager  #  世界状态管理器
        self.project_path = project_path  #  项目路径
        
        #  加载扩写提示词配置
        self._expansion_config = self._load_expansion_config()
        
        #  加载章节展开策略配置
        self._chapter_expansion_prompts = self._load_chapter_expansion_prompts()
        
        #  加载节拍类型到风格的映射配置
        self._beat_style_mapping = self._load_beat_style_mapping()
        
        #  加载番茄爆款结尾模板
        self._ending_template = self._load_ending_template()
        
        # 质检配置
        if quality_config:
            self.QUALITY_CHECK_CONFIG.update(quality_config)
        
        # 提取小说基本信息
        self.novel_title = novel_data.get('title', '未命名')
        
        # 生成会话ID(包含书名前缀,便于识别)
        import uuid
        # 书名处理:取前10个字符,去除特殊字符
        title_prefix = self._sanitize_title(self.novel_title)[:10]
        self.session_id = f"CCG-{title_prefix}-{uuid.uuid4().hex[:8].upper()}"
        
        # 初始化对话日志记录器
        if HAS_CONVERSATION_LOGGER:
            try:
                self.logger = ConversationLogger(self.session_id)
                logging.info(f"[章节对话 {self.session_id}] 对话日志记录器已启动")
            except Exception as e:
                logging.warning(f"[章节对话 {self.session_id}] 日志记录器初始化失败: {e}")
        
        # 初始化质量检查器
        if HAS_QUALITY_CHECKER and HAS_OPTIMIZER and self.QUALITY_CHECK_CONFIG["enabled"]:
            try:
                optimizer = ChapterPromptOptimizer(novel_data)
                self.quality_checker = ChapterQualityChecker(novel_data, optimizer)
                logging.info(f"[章节对话 {self.session_id}] 质量检查器已启动")
            except Exception as e:
                logging.warning(f"[章节对话 {self.session_id}] 质量检查器初始化失败: {e}")
        
        # 初始化信息提取器(AI自动提取章节信息)
        self.info_extractor = None
        if HAS_INFO_EXTRACTOR:
            try:
                self.info_extractor = ChapterInfoExtractor(api_client)
                logging.info(f"[章节对话 {self.session_id}] 信息提取器已启动")
            except Exception as e:
                logging.warning(f"[章节对话 {self.session_id}] 信息提取器初始化失败: {e}")
        
        #  章节标题历史记录(用于唯一性检查)
        self._chapter_titles = set()
        logging.info(f"[章节对话 {self.session_id}] 标题唯一性检查器已初始化")
        
        #  阶段性复盘优化器跟踪(滑动窗口10章复盘)
        self.stage_review_triggered = set()  # 已触发的复盘里程碑(10, 20, 30...)
        self.stage_review_optimizer = None
        if HAS_STAGE_REVIEW_OPTIMIZER and project_path:
            try:
                self.stage_review_optimizer = StageReviewOptimizer(project_path, api_client)
                logging.info(f"[章节对话 {self.session_id}] 阶段性复盘优化器已启动")
            except Exception as e:
                logging.warning(f"[章节对话 {self.session_id}] 阶段性复盘优化器初始化失败: {e}")
        
        # 初始化主角名称
        self.protagonist_name = self._get_protagonist_name()
    
    def _load_expansion_config(self) -> Dict:
        """加载章节扩写提示词配置"""
        config_path = Path(__file__).parent.parent.parent.parent / "prompt_packages" / "default" / "market_driven" / "components" / "chapter_expansion_prompts.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"[ChapterConversationGenerator] 加载扩写配置失败: {e}")
        return {}
    
    def _load_chapter_expansion_prompts(self) -> Dict:
        """加载章节展开策略和弹幕剧本配置"""
        config_path = Path(__file__).parent.parent.parent.parent / "prompt_packages" / "default" / "market_driven" / "components" / "chapter_expansion_prompts.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info("[ChapterConversationGenerator] 已加载章节展开策略配置")
                    return config
            except Exception as e:
                logger.warning(f"[ChapterConversationGenerator] 加载章节展开策略配置失败: {e}")
        return {}
    
    def _load_beat_style_mapping(self) -> Dict:
        """加载节拍类型到风格的映射配置"""
        config_path = Path(__file__).parent.parent.parent.parent / "prompt_packages" / "default" / "market_driven" / "components" / "beat_style_mapping.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info("[ChapterConversationGenerator] 已加载节拍风格映射配置")
                    return config
            except Exception as e:
                logger.warning(f"[ChapterConversationGenerator] 加载节拍风格映射失败: {e}")
        return {}
    
    def _load_ending_template(self) -> str:
        """加载番茄爆款结尾模板"""
        config_path = Path(__file__).parent.parent.parent.parent / "prompt_packages" / "default" / "market_driven" / "components" / "chapters" / "standard_chapter_prompts.json"
        if not config_path.exists():
            raise ValueError("[ChapterConversationGenerator] standard_chapter_prompts.json 配置文件不存在")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        ending_config = config.get("standard_chapter", {}).get("tomato_bestseller_ending_templates", {})
        prompt_template = ending_config.get("prompt_template", "")
        if not prompt_template:
            raise ValueError("[ChapterConversationGenerator] tomato_bestseller_ending_templates.prompt_template 未找到")
        
        logger.info(f"[ChapterConversationGenerator] 已加载番茄爆款结尾模板")
        return prompt_template
    
    def _sanitize_title(self, title: str) -> str:
        """清理书名,去除特殊字符,用于文件名"""
        import re
        # 保留中文,英文,数字
        return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', title)
    
    def _get_protagonist_name(self) -> str:
        """获取主角姓名"""
        char_design = self.novel_data.get('character_design', {})
        if isinstance(char_design, dict):
            protagonist = char_design.get('protagonist', {})
            if isinstance(protagonist, dict):
                basic_info = protagonist.get('basic_info', {})
                return basic_info.get('name', '主角')
        return '主角'
    
    def _create_session(self, start_chapter: int) -> 'ConversationSession':
        """创建对话会话"""
        from src.core.APIClient import ConversationSession
        
        system_prompt = self._build_system_prompt(start_chapter)
        
        session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            provider=self.api_client.default_provider,
            purpose_prefix=f"{self.session_id}"
        )
        # 设置历史限制
        session.max_history = 50  # 保留更多历史,支持多章连贯
        
        logger.info(f"[章节对话 {self.session_id}] 会话创建 | 小说: {self.novel_title} | 起始章: {start_chapter}")
        return session
    
    def _get_enforced_protagonist_name(self) -> str:
        """获取强制主角名(多层回退,确保有值)"""
        # 第一层:user_choices(用户填写的)
        user_choices = self.novel_data.get('user_choices', {})
        name = user_choices.get('protagonist_name', '')
        if name:
            return name
        
        # 第二层:character_design.protagonist.name
        char_design = self.novel_data.get('character_design', {})
        protagonist = char_design.get('protagonist', {})
        if isinstance(protagonist, dict):
            name = protagonist.get('name', '')
            if name:
                return name
            basic_info = protagonist.get('basic_info', {})
            name = basic_info.get('name', '')
            if name:
                return name
        
        # 第三层:plan.protagonist
        plan = self.novel_data.get('plan', {})
        plan_protagonist = plan.get('protagonist', {})
        if isinstance(plan_protagonist, dict):
            name = plan_protagonist.get('name', '')
            if name:
                return name
        
        # 最后回退
        logger.warning(f"[章节对话 {self.session_id}] 警告:未能找到主角名!")
        return '主角'
    
    def _build_writing_style_prompt(self) -> str:
        """🔥 构建文风提示词"""
        if not self.writing_style:
            return ""
        
        style = self.writing_style
        style_name = style.get('name', '未命名')
        style_desc = style.get('description', '')
        features = style.get('features', {})
        
        prompt_parts = [
            f"""
【文风要求：{style_name}】
{style_desc}
"""
        ]
        
        # 如果有特征数据，添加具体指标
        if features:
            short_ratio = features.get('short_sentence_ratio', 0.3)
            dialogue_ratio = features.get('dialogue_ratio', 0.3)
            sensory_density = features.get('sensory_density', 0.03)
            colloquialism_density = features.get('colloquialism_density', 0.02)
            
            prompt_parts.append(f"""
具体指标要求：
- 短句（<10字）占比约{short_ratio*100:.0f}%，营造快节奏感
- 对话占比约{dialogue_ratio*100:.0f}%，推动情节发展
- 感官描写密度约{sensory_density*100:.1f}%，增强代入感
- 口语化程度约{colloquialism_density*100:.1f}%，贴近网文风格
""")
        
        return "\n".join(prompt_parts)
    
    def _build_system_prompt(self, start_chapter: int) -> str:
        """构建系统提示词(使用TropePromptBuilder分层架构)"""
        # 获取强制主角名
        protagonist_name = self._get_enforced_protagonist_name()
        
        # 🔥 构建文风提示词
        style_prompt = self._build_writing_style_prompt()
        
        # 使用TropePromptBuilder构建System Prompt(分层架构)
        if HAS_TROPE_PROMPT_BUILDER:
            try:
                builder = TropePromptBuilder(self.tropes)
                system_prompt = builder.build_chapter_system_prompt(
                    novel_title=self.novel_title,
                    chapter_num=start_chapter,
                    protagonist_name=protagonist_name,
                    emotion_arc=None  # 可以在调用时传入具体情绪弧线
                )
                logger.info(f"[章节对话 {self.session_id}] 使用TropePromptBuilder System Prompt | 主角: {protagonist_name}")
                
                # 添加角色设定强制执行
                enforcement = f"""
[角色设定 - 绝对不可更改]
主角姓名:{protagonist_name}
约束:
1. 必须使用此名字,禁止编造其他名字(如林枫,林霄等)
2. 每章正文必须多次出现主角名字,不能用"他"代替
3. 如果前文有错误名字,本章必须纠正回来
4. 违反此设定视为严重错误
"""
                # 🔥 注入文风提示词
                if style_prompt:
                    logger.info(f"[章节对话 {self.session_id}] 注入文风: {self.writing_style.get('name')}")
                    return system_prompt + style_prompt + enforcement
                return system_prompt + enforcement
                
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] TropePromptBuilder失败,回退到优化器: {e}")
        
        # 回退到原有优化器
        if HAS_OPTIMIZER:
            try:
                optimizer = ChapterPromptOptimizer(self.novel_data)
                system_prompt = optimizer.build_system_prompt()
                logger.info(f"[章节对话 {self.session_id}] 使用优化的System Prompt v2.0 | 主角: {protagonist_name}")
                
                enforcement = f"""[角色设定 - 绝对不可更改]
主角姓名:{protagonist_name}
约束:
1. 必须使用此名字,禁止编造其他名字(如林枫,林霄等)
2. 每章正文必须多次出现主角名字,不能用"他"代替
3. 如果前文有错误名字,本章必须纠正回来
4. 违反此设定视为严重错误

"""
                # 🔥 注入文风提示词
                if style_prompt:
                    logger.info(f"[章节对话 {self.session_id}] 注入文风: {self.writing_style.get('name')}")
                    return style_prompt + enforcement + system_prompt
                return enforcement + system_prompt
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 优化器失败,使用备用模式: {e}")
        
        # 使用简化版优化器(备用)
        optimizer = SimpleOptimizer(self.novel_data)
        base_prompt = optimizer.build_system_prompt()
        
        # 🔥 注入文风提示词
        if style_prompt:
            logger.info(f"[章节对话 {self.session_id}] 注入文风: {self.writing_style.get('name')}")
            return style_prompt + "\n" + base_prompt
        return base_prompt
    
    def generate_chapters(self, start_chapter: int, end_chapter: int, 
                         blueprint: Dict, progress_callback=None) -> List[Dict]:
        """
        连续生成多章
        
        Args:
            start_chapter: 起始章节号
            end_chapter: 结束章节号
            blueprint: 章节规划
            progress_callback: 进度回调(chapter_num, total)
        
        Returns:
            生成的章节列表
        """
        # 调试：检查参数类型
        logger.info(f"[CCG DEBUG] generate_chapters: start_chapter={start_chapter} (type={type(start_chapter)}), end_chapter={end_chapter} (type={type(end_chapter)})")
        
        total = end_chapter - start_chapter + 1
        logger.info(f"[章节对话 {self.session_id}] 开始生成第{start_chapter}-{end_chapter}章 | 共{total}章")
        
        # 创建会话
        self.session = self._create_session(start_chapter)
        
        chapters = []
        # 🔥 修复：如果是续写（start_chapter > 1），加载前面章节的内容作为初始上下文
        prev_chapter_summary = self._load_previous_chapter_summary(start_chapter)
        
        for i, chapter_num in enumerate(range(start_chapter, end_chapter + 1)):
            logger.info(f"[CCG DEBUG] Loop chapter_num={chapter_num}, type={type(chapter_num)}, i={i}")
            logger.info(f"[章节对话 {self.session_id}] 生成第{chapter_num}章 ({i+1}/{total})")
            
            try:
                # 生成单章
                chapter = self._generate_single_chapter_in_session(
                    chapter_num=chapter_num,
                    blueprint=blueprint,
                    prev_summary=prev_chapter_summary
                )
                
                chapters.append(chapter)
                
                # 更新上一章摘要(用于上下文)
                prev_chapter_summary = self._summarize_chapter(chapter)
                
                # 进度回调
                if progress_callback:
                    progress_callback(chapter_num, total)
                
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章完成 | 字数: {chapter.get('word_count', 0)}")
                
                #  注意:滑动窗口优化已移到 batch_chapter_generator.py 中批次完成后触发
                # 原因:生成过程中章节还未保存到磁盘,优化器无法加载
                # 原代码:if chapter_num % 10 == 0: self._trigger_stage_review(...)
                
            except Exception as e:
                import traceback
                stack_trace = traceback.format_exc()
                logger.error(f"[章节对话 {self.session_id}] 第{chapter_num}章失败: {e}\n完整堆栈:\n{stack_trace}")
                # 记录失败但不中断
                chapters.append({
                    "chapter_number": chapter_num,
                    "title": f"第{chapter_num}章(生成失败)",
                    "content": f"生成失败: {str(e)}\n\n堆栈:\n{stack_trace}",
                    "word_count": 0,
                    "quality_score": 0,
                    "error": str(e)
                })
        
        logger.info(f"[章节对话 {self.session_id}] 生成完成 | 成功: {len([c for c in chapters if c.get('word_count', 0) > 0])}/{total}章 | 总轮次: {self.session.turn_count}")
        
        #  批量保存提取的信息到世界状态文件
        self._save_extracted_info(chapters)
        
        return chapters
    
    def _save_extracted_info(self, chapters: List[Dict]):
        """
        保存提取的信息到设定文件
        """
        if not self.info_extractor:
            return
        
        try:
            # 收集所有章节的提取信息
            extractions = []
            for ch in chapters:
                if 'extracted_info' in ch:
                    extractions.append(ch['extracted_info'])
            
            if not extractions:
                logger.warning(f"[章节对话 {self.session_id}] 无提取信息可保存")
                return
            
            # 合并到世界状态
            # 先尝试读取现有状态
            project_path = self.project_path or '.'
            world_state_path = Path(project_path) / ".world_state.json"
            
            current_state = None
            if world_state_path.exists():
                try:
                    with open(world_state_path, 'r', encoding='utf-8') as f:
                        current_state = json.load(f)
                except:
                    pass
            
            merged_state = self.info_extractor.merge_to_world_state(extractions, current_state)
            
            # 保存到文件
            with open(world_state_path, 'w', encoding='utf-8') as f:
                json.dump(merged_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[章节对话 {self.session_id}] 世界状态已更新: {world_state_path}")
            
            # 同时保存详细的提取信息
            extraction_path = Path(project_path) / ".chapter_extractions.json"
            with open(extraction_path, 'w', encoding='utf-8') as f:
                json.dump(extractions, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[章节对话 {self.session_id}] 章节提取信息已保存: {extraction_path}")
            
        except Exception as e:
            logger.error(f"[章节对话 {self.session_id}] 保存提取信息失败: {e}")
    
    def _load_previous_chapter_summary(self, start_chapter: int) -> str:
        """
        加载前面章节的摘要作为续写的初始上下文
        
        如果是续写（start_chapter > 1），读取前几章的内容生成摘要
        如果是全新生成（start_chapter = 1），返回空字符串
        
        Args:
            start_chapter: 起始章节号
            
        Returns:
            前面章节的摘要，用于承接上下文
        """
        if start_chapter <= 1:
            return ""  # 从第1章开始，无前文
        
        if not self.project_path:
            logger.warning(f"[章节对话 {self.session_id}] 项目路径为空，无法加载前文")
            return ""
        
        try:
            # 加载前3章作为上下文（第 start_chapter-3 到 start_chapter-1 章）
            context_chapters = []
            for ch_num in range(max(1, start_chapter - 3), start_chapter):
                chapter_file = Path(self.project_path) / "chapters" / f"chapter_{ch_num:03d}.json"
                if chapter_file.exists():
                    try:
                        with open(chapter_file, 'r', encoding='utf-8') as f:
                            chapter_data = json.load(f)
                            context_chapters.append({
                                'chapter_num': ch_num,
                                'title': chapter_data.get('title', ''),
                                'content': chapter_data.get('content', '')
                            })
                    except Exception as e:
                        logger.warning(f"[章节对话 {self.session_id}] 读取第{ch_num}章失败: {e}")
            
            if not context_chapters:
                logger.warning(f"[章节对话 {self.session_id}] 未找到前文章节（第{start_chapter-3}-{start_chapter-1}章）")
                return ""
            
            # 生成前文摘要
            summaries = []
            for ch in context_chapters:
                content_preview = ch['content'][:300] if len(ch['content']) > 300 else ch['content']
                summaries.append(f"第{ch['chapter_num']}章《{ch['title']}》：{content_preview}...")
            
            summary = "前文回顾：\n" + "\n".join(summaries)
            logger.info(f"[章节对话 {self.session_id}] 已加载{len(context_chapters)}章前文作为上下文")
            return summary
            
        except Exception as e:
            logger.error(f"[章节对话 {self.session_id}] 加载前文摘要失败: {e}")
            return ""
    
    def _generate_single_chapter_in_session(self, chapter_num: int, 
                                            blueprint: Dict,
                                            prev_summary: str) -> Dict:
        """在会话中生成单章(集成质检)"""
        # 🔥 调试：检查 chapter_num
        logger.info(f"[CCG DEBUG] _generate_single_chapter_in_session: chapter_num={chapter_num}, type={type(chapter_num)}")
        
        # 🔥 如果 chapter_num 为 None，直接抛出异常以便追踪堆栈
        if chapter_num is None:
            import traceback
            stack = traceback.format_stack()
            logger.error(f"[CCG {self.session_id}] CRITICAL: chapter_num is None!\n调用堆栈:\n{''.join(stack)}")
            raise ValueError(f"chapter_num cannot be None in _generate_single_chapter_in_session")
        
        # 确保 chapter_num 是整数
        try:
            chapter_num = int(chapter_num)
        except (TypeError, ValueError) as e:
            raise ValueError(f"chapter_num must be an integer, got {chapter_num} ({type(chapter_num)})") from e
        
        # 获取本章规划
        chapter_plan = self._get_chapter_plan(chapter_num, blueprint)
        
        # 获取情绪节拍
        emotion_beat = self._get_emotion_beat(chapter_num)
        
        # 构建提示词
        prompt = self._build_chapter_prompt(
            chapter_num=chapter_num,
            chapter_plan=chapter_plan,
            emotion_beat=emotion_beat,
            prev_summary=prev_summary
        )
        
        # ===== 质检环节(v3.0新增)=====
        if self.quality_checker and self.QUALITY_CHECK_CONFIG["enabled"]:
            try:
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章开始质检...")
                quality_report = self.quality_checker.check_chapter(
                    chapter_num=chapter_num,
                    prompt=prompt,
                    blueprint=blueprint
                )
                
                # 保存质检报告
                self.quality_reports.append(quality_report)
                
                # 记录质检结果
                if self.QUALITY_CHECK_CONFIG["log_level"] in ["debug", "info"]:
                    report_text = format_quality_report(quality_report)
                    logger.info(f"[章节对话 {self.session_id}] 质检报告:\n{report_text}")
                
                # 检查是否可以通过
                if not quality_report.can_generate:
                    critical_issues = quality_report.get_critical_issues()
                    error_issues = quality_report.get_errors()
                    logger.error(
                        f"[章节对话 {self.session_id}] 第{chapter_num}章质检未通过! "
                        f"严重问题: {len(critical_issues)}, 错误: {len(error_issues)}"
                    )
                    
                    if self.QUALITY_CHECK_CONFIG["stop_on_critical"]:
                        raise Exception(
                            f"第{chapter_num}章提示词质量不达标(分数: {quality_report.score}),"
                            f"严重问题: {len(critical_issues)}个"
                        )
                
                # 检查分数
                if quality_report.score < self.QUALITY_CHECK_CONFIG["min_score"]:
                    # 收集扣分项详情
                    issues_detail = []
                    for issue in quality_report.issues:
                        # 🔥 修复：兼容 severity 是 Enum 或字典的情况
                        severity_val = issue.severity.value if hasattr(issue.severity, 'value') else issue.severity.get('value', '') if isinstance(issue.severity, dict) else str(issue.severity)
                        severity_icon = "🔴" if severity_val == "critical" else "🟠" if severity_val == "error" else "🟡"
                        issues_detail.append(f"{severity_icon} [{issue.category}] {issue.message}")
                    
                    issues_str = "\n    ".join(issues_detail) if issues_detail else "无详细扣分项"
                    
                    logger.warning(
                        f"[章节对话 {self.session_id}] 第{chapter_num}章分数较低({quality_report.score}),"
                        f"但仍继续生成\n"
                        f"    扣分详情 ({len(quality_report.issues)}项):\n    {issues_str}"
                    )
                
                # 自动修复
                if self.QUALITY_CHECK_CONFIG["auto_fix"] and quality_report.optimized_prompt:
                    original_score = quality_report.score
                    optimized_prompt = quality_report.optimized_prompt
                    
                    # 简单判断:如果优化后的提示词明显更长,可能添加了修复内容
                    if len(optimized_prompt) > len(prompt) * 1.1:
                        logger.info(
                            f"[章节对话 {self.session_id}] 第{chapter_num}章已自动优化提示词 "
                            f"({len(prompt)} -> {len(optimized_prompt)} 字符)"
                        )
                        prompt = optimized_prompt
                        
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 质检过程出错: {e}")
                # 质检出错不阻断生成,继续执行
        
        # 在会话中发送消息
        logger.info(f"[章节对话 {self.session_id}] 发送第{chapter_num}章提示词 | 当前历史: {len(self.session.messages)}条")
        response = self.session.send_message(
            user_prompt=prompt,
            temperature=0.7,
            purpose=f"第{chapter_num}章"
        )
        logger.info(f"[章节对话 {self.session_id}] 接收第{chapter_num}章响应 | 总轮次: {self.session.turn_count}")
        
        # 记录对话日志(如果日志记录器可用)
        if self.logger and HAS_CONVERSATION_LOGGER:
            try:
                # 构建消息列表用于日志记录
                messages_for_log = []
                if hasattr(self.session, 'messages') and self.session.messages:
                    for msg in self.session.messages[-2:]:  # 记录最后两条(user + assistant)
                        messages_for_log.append({
                            "role": msg.get("role", "unknown"),
                            "content": msg.get("content", "")[:500] + "..." if len(msg.get("content", "")) > 500 else msg.get("content", "")
                        })
                self.logger.log_round(
                    step=f"第{chapter_num}章",
                    messages=messages_for_log,
                    response=response[:2000] if len(response) > 2000 else response
                )
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 记录对话日志失败: {e}")
        
        # 解析内容(现在返回字典,包含 title 和 content)
        parsed_response = self._parse_response(response)
        ai_title = parsed_response.get('title', '')
        content = parsed_response.get('content', '')
        
        #  校验1:检查是否只返回了自检报告而没有正文
        if self._is_only_self_check_report(content):
            logger.error(f"[章节对话 {self.session_id}] 第{chapter_num}章只返回了自检报告,没有正文!可能是token限制或上下文过长.")
            # 尝试重试一次
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章尝试重试...")
            
            # 简化提示词重试 - 必须包含JSON格式要求
            retry_prompt = self._get_retry_prompt_template(chapter_num)
            retry_response = self.session.send_message(
                user_prompt=retry_prompt,
                temperature=0.7,
                purpose=f"第{chapter_num}章(重试)"
            )
            parsed_retry = self._parse_response(retry_response)
            retry_title = parsed_retry.get('title', '')
            content = parsed_retry.get('content', '')
            
            # 🔥 修复：重试时如果新标题有效则使用，否则保留原标题
            if retry_title and len(retry_title.strip()) >= 4:
                ai_title = retry_title.strip()
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章重试后使用新标题: '{ai_title}'")
            else:
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章重试后保留原标题: '{ai_title}'")
            
            # 再次校验
            if self._is_only_self_check_report(content):
                raise Exception(f"第{chapter_num}章重试后仍只返回自检报告,请检查token限制或减少每批章节数")
        
        #  校验2:检查和修复主角名
        content = self._validate_and_fix_protagonist_name(content, chapter_num)
        
        #  校验3:使用 WorldStateManager 校验剧情连贯性
        if self.world_state_manager:
            issues = self.world_state_manager.validate_chapter(chapter_num, content)
            if issues:
                logger.warning(f"[章节对话 {self.session_id}] 第{chapter_num}章剧情校验发现问题:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
            
            # 更新世界状态(用于下一章)
            self.world_state_manager.update_after_chapter(chapter_num, content)
        
        #  后处理:提取正文部分(根据分隔符)
        content = self._extract_main_content(content, chapter_num)
        
        #  校验4:检查内容完整性(是否被截断)
        completeness_check = self._check_content_completeness(content, chapter_num)
        if not completeness_check['is_complete']:
            logger.warning(f"[章节对话 {self.session_id}] 第{chapter_num}章内容不完整: {completeness_check['reason']}")
            # 记录问题,后续阶段会统一修复
        
        #  字数检查(仅记录,完全不在单章扩写)
        # 字数优化统一在 stage_review_optimizer 阶段处理,避免单章重复扩写
        word_count = len(content)
        
        if word_count < 1800:
            # 严重低于阈值:记录debug信息,留给后续阶段统一优化(不显示warning避免干扰)
            logger.debug(f"[章节对话 {self.session_id}] 第{chapter_num}章字数({word_count}),将在阶段审核时统一优化")
        elif word_count < 2000:
            # 低于2000字:记录debug信息,留给后续阶段统一优化(不显示warning避免干扰)
            logger.debug(f"[章节对话 {self.session_id}] 第{chapter_num}章字数({word_count}),将在阶段审核时统一优化")
        elif word_count < 2200:
            # 2000-2200字:记录信息,接受当前字数
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章字数略低({word_count}),接受当前字数,后续统一优化")
        
        #  AI信息提取:自动提取角色,钩子,世界设定等信息
        chapter_data = {
            "chapter_number": chapter_num,
            "title": self._extract_title(content, chapter_plan, ai_title),
            "content": content,
            "word_count": word_count,
            "quality_score": 8.0,
            "chapter_plan": chapter_plan,
            "generated_at": datetime.now().isoformat()
        }
        
        if self.info_extractor:
            try:
                extracted_info = self.info_extractor.extract_from_chapter(chapter_data)
                chapter_data["extracted_info"] = extracted_info
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章信息提取完成: {len(extracted_info.get('new_characters', []))}新角色, {len(extracted_info.get('new_hooks', []))}新钩子")
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 第{chapter_num}章信息提取失败: {e}")
        
        return chapter_data
    
    def _extract_main_content(self, content: str, chapter_num: int) -> str:
        """
        根据分隔符提取正文部分
        格式:正文内容 + [AI自检报告] + 自检报告内容
        
        注意:有些AI输出使用 --- 作为分隔符,需要特殊处理
        """
        # 尝试找到分隔符(优先匹配完整的标记)
        separators = [
            '[AI自检报告]',     # 标准标记
            '---正文结束---',   # 旧版标记
            '---\n【AI自检报告', # --- 换行后接自检报告
            '---\n[AI自检报告',  # 英文括号版本
            '自检报告:',        # 简化标记
            '[自检报告]'
        ]
        
        for sep in separators:
            if sep in content:
                # 找到分隔符,提取前面的内容
                main_content = content.split(sep)[0].strip()
                # 移除尾部可能的 --- 分隔符
                if main_content.endswith('---'):
                    main_content = main_content[:-3].strip()
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章使用分隔符'{sep[:20]}...'提取正文: {len(main_content)}字")
                return main_content
        
        # 特殊处理:内容以 "---" 开头(自检报告分隔符),跳过它
        if content.strip().startswith('---'):
            lines = content.split('\n')
            # 找到第一个不以 --- 开头且不是空的行
            main_lines = []
            found_start = False
            for line in lines:
                if not found_start:
                    # 跳过开头的 --- 和空行
                    if line.strip() == '---' or line.strip() == '':
                        continue
                    found_start = True
                
                # 开始收集正文
                if found_start:
                    # 遇到自检报告标记停止
                    if '自检' in line and '报告' in line:
                        break
                    if line.strip() == '---' and '[AI自检报告]' in content:
                        break
                    main_lines.append(line)
            
            if main_lines:
                main_content = '\n'.join(main_lines).strip()
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章跳过开头---提取正文: {len(main_content)}字")
                return main_content
        
        # 最后尝试:查找 "---" 后面跟着 "【AI自检报告" 的位置
        import re
        pattern = r'---\s*\n\s*【?\[?AI自检报告'
        match = re.search(pattern, content)
        if match:
            main_content = content[:match.start()].strip()
            if main_content.endswith('---'):
                main_content = main_content[:-3].strip()
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章使用正则提取正文: {len(main_content)}字")
            return main_content
        
        # 没有找到分隔符,尝试其他方式
        # 如果包含"自检报告"字样,尝试提取前面部分
        if '自检' in content or '字数:' in content:
            lines = content.split('\n')
            main_lines = []
            for line in lines:
                if '自检' in line or ('字数:' in line and '总字数' in line) or '番茄算法:' in line:
                    break
                main_lines.append(line)
            if main_lines:
                main_content = '\n'.join(main_lines).strip()
                # 移除尾部可能的 --- 
                if main_content.endswith('---'):
                    main_content = main_content[:-3].strip()
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章通过关键词提取正文: {len(main_content)}字")
                return main_content
        
        # 没有找到任何标记,返回原内容(但移除尾部的---)
        result = content.strip()
        if result.endswith('---'):
            result = result[:-3].strip()
        return result
    
    def _expand_chapter(self, content: str, chapter_num: int, need_words: int) -> str:
        """
        强制扩写 - 确保字数达标
        """
        if need_words <= 0:
            return content
            
        try:
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章开始扩写,需要+{need_words}字")
            
            prompt = self._get_expansion_prompt_template(chapter_num, content, need_words)
            
            response = self.session.send_message(
                user_prompt=prompt,
                temperature=0.8,
                purpose=f"第{chapter_num}章强制扩写"
            )
            
            #  解析JSON响应,提取content
            parsed_response = self._parse_response(response)
            full_content = parsed_response.get('content', '')
            
            # 验证扩写后字数
            final_count = len(full_content)
            if final_count < len(content) + need_words * 0.8:  # 允许20%误差
                logger.warning(f"[章节对话 {self.session_id}] 扩写后字数({final_count})仍不足,原始{len(content)},需要+{need_words}")
                # 如果还不够,在末尾追加扩写标记提示
                return full_content + f"\n\n[注:当前{final_count}字,仍需扩写]"
            
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章扩写完成: {final_count}字 (原{len(content)}字)")
            return full_content
            
        except Exception as e:
            logger.warning(f"[章节对话 {self.session_id}] 扩写失败: {e}")
            return content
    
    def _insert_expansion(self, original: str, expansion: str) -> str:
        """
        将扩写内容智能插入到原文中
        优先插入到高潮/爽点段落,而不是末尾
        """
        # 查找高潮标记词位置
        climax_markers = ['"轰!"', '"砰!"', '"轰隆!"', '炸裂', '爆发', '震惊']
        
        best_pos = len(original)  # 默认插入到末尾
        
        for marker in climax_markers:
            # 找到最后一个高潮标记
            pos = original.rfind(marker)
            if pos > 0:
                # 在高潮后插入扩写
                best_pos = pos + len(marker)
                break
        
        # 插入扩写内容
        before = original[:best_pos]
        after = original[best_pos:]
        
        combined = before + "\n\n" + expansion + "\n\n" + after
        return combined.strip()
    
    def _get_chapter_plan(self, chapter_num: int, blueprint: Dict) -> Dict:
        """获取本章规划"""
        chapters = blueprint.get("chapters", [])
        for ch in chapters:
            if ch.get("chapter_number") == chapter_num:
                return ch
        
        # 默认规划
        return {
            "chapter_number": chapter_num,
            "title": f"第{chapter_num}章",
            "climax_type": "推进",
            "required_elements": ["剧情推进"]
        }
    
    def _get_emotion_beat(self, chapter_num: int) -> Dict:
        """获取情绪节拍"""
        emotion_curve = self.novel_data.get('emotion_curve', [])
        for beat in emotion_curve:
            if beat.get('ch') == chapter_num:
                return beat
        return {"emotion": "期待", "intensity": 6}
    
    def _is_only_self_check_report(self, content: str) -> bool:
        """检查内容是否只包含自检报告而没有正文"""
        if not content:
            return True
        
        content = content.strip()
        
        # 如果只包含自检报告标记,没有正文
        if content.startswith("[AI自检报告") and "第" not in content[:50]:
            return True
        
        # 如果字数太少(少于300字),认为没有正文
        if len(content) < 300:
            return True
        
        # 检查是否只有自检报告部分
        lines = content.split('\n')
        report_lines = [l for l in lines if l.startswith("[AI自检报告") or l.startswith("总字数:") or l.startswith("番茄算法:")]
        if len(report_lines) >= 3 and len(content) < 500:
            return True
        
        return False
    
    def _check_content_completeness(self, content: str, chapter_num: int) -> dict:
        """
        检查章节内容是否完整(未被截断)
        番茄爆款结尾标准:最后50字必须是悬念/钩子
        
        Returns:
            {
                'is_complete': bool,
                'reason': str,
                'issues': list
            }
        """
        issues = []
        
        # 1. 检查是否以完整句子结尾(不以标点符号结尾可能是截断)
        content_stripped = content.strip()
        last_char = content_stripped[-1] if content_stripped else ''
        
        # 中文标点 + 英文标点 + 省略号
        sentence_endings = ['.', '!', '?', '」', '"', "'", '…', '.', '!', '?', '--', '-']
        
        if last_char not in sentence_endings:
            issues.append(f"章节未以完整句子结尾(最后字符:'{last_char}'),可能已被截断")
        
        # 2. [番茄爆款标准]检查章尾钩子质量(最后150字内)
        last_150_chars = content_stripped[-150:] if len(content_stripped) > 150 else content_stripped
        
        # 钩子关键词库(扩展版 - 番茄爆款常用)
        hook_keywords_crisis = ['突然', '就在这时', '与此同时', '远处', '警告', '紧急', '危险', '致命']
        hook_keywords_system = ['系统提示', '系统警告', '叮', '公告', '通知', '任务发布']
        hook_keywords_reveal = ['原来', '难道', '终于发现', '真相', '秘密', '身份']
        hook_keywords_confront = ['冷笑', '对峙', '剑拔弩张', '一触即发', '大战', '动手']
        hook_keywords_time = ['倒计时', '时间到', '即将', '马上', '刻不容缓']
        hook_keywords_emotion = ['震惊', '骇然', '惊恐', '狂喜', '绝望', '不敢置信']
        
        all_hook_keywords = (
            hook_keywords_crisis + hook_keywords_system + hook_keywords_reveal + 
            hook_keywords_confront + hook_keywords_time + hook_keywords_emotion
        )
        
        found_hooks = [kw for kw in all_hook_keywords if kw in last_150_chars]
        has_hook = len(found_hooks) > 0
        
        # 检查最后50字是否以悬念结尾(不能有完结感)
        last_50_chars = content_stripped[-50:] if len(content_stripped) > 50 else content_stripped
        forbidden_endings = ['完', '结束', '落幕', '安息', '休息', '睡觉', '晚安']
        has_forbidden_ending = any(fe in last_50_chars for fe in forbidden_endings)
        
        if not has_hook and len(content_stripped) > 1500:
            issues.append(f"章尾可能缺少钩子(最后150字内无明显悬念标记).建议模板:危机降临/系统提示/身份揭露/对峙爆发")
        elif has_forbidden_ending:
            issues.append("章尾有完结感词汇(完/结束/休息等),违反番茄爆款'章章有钩子'原则")
        
        # 3. [优化]对"未完待续"标记的检测 - 放宽标准
        # 番茄爆款允许"突然","正要"等悬念词结尾
        incomplete_markers_strict = ['第一个.', '第二个.', '第三个.']
        last_100_chars = content_stripped[-100:] if len(content_stripped) > 100 else content_stripped
        
        for marker in incomplete_markers_strict:
            if marker in last_100_chars:
                marker_pos = last_100_chars.rfind(marker)
                if marker_pos > len(last_100_chars) - 30:  # 只在最后30字内才算问题
                    issues.append(f"章节以列表标记'{marker}'结尾,建议改为悬念钩子")
        
        # 4. 检查字数
        word_count = len(content_stripped)
        if word_count < 1800:
            issues.append(f"字数严重不足({word_count}字),内容可能不完整")
        elif word_count < 2000:
            issues.append(f"字数不足({word_count}字),可能缺少部分内容")
        
        # 返回结果 - 只有字数问题才算严重,钩子问题只提醒
        is_complete = word_count >= 1800
        
        return {
            'is_complete': is_complete,
            'has_strong_hook': has_hook and len(found_hooks) >= 2,
            'hook_keywords_found': found_hooks,
            'reason': '; '.join(issues) if issues else '内容完整',
            'issues': issues
        }
    
    def _validate_and_fix_protagonist_name(self, content: str, chapter_num: int) -> str:
        """校验并修复主角名"""
        protagonist_name = self._get_enforced_protagonist_name()
        
        # 常见错误名字映射(根据实际问题定制)
        wrong_names_map = {
            '林枫': protagonist_name,
            '林霄': protagonist_name,
            '林雷': protagonist_name,
            '陆风': protagonist_name,
        }
        
        fixes = []
        for wrong_name, correct_name in wrong_names_map.items():
            if wrong_name in content:
                count = content.count(wrong_name)
                content = content.replace(wrong_name, correct_name)
                fixes.append(f"{wrong_name}->{correct_name}({count}处)")
        
        if fixes:
            logger.warning(f"[章节对话 {self.session_id}] 第{chapter_num}章自动修复角色名: {', '.join(fixes)}")
        
        # 检查正文是否完全没有主角名(可能只用了"他")
        if protagonist_name not in content:
            logger.error(f"[章节对话 {self.session_id}] 第{chapter_num}章警告:正文可能缺少主角名'{protagonist_name}'")
            # 不抛出异常,因为可能是正文还没展开
        
        return content
    
    def _build_protagonist_reminder(self) -> str:
        """构建主角设定提醒(防止AI忘记主角名)"""
        char_design = self.novel_data.get('character_design', {})
        if not char_design:
            return ""
        
        protagonist = char_design.get('protagonist', {})
        if not protagonist:
            return ""
        
        parts = []
        
        # 获取主角名(优先使用user_choices中的)
        user_choices = self.novel_data.get('user_choices', {})
        protagonist_name = user_choices.get('protagonist_name', '')
        
        if not protagonist_name:
            # 从character_design获取
            if 'name' in protagonist:
                protagonist_name = protagonist['name']
            else:
                basic_info = protagonist.get('basic_info', {})
                protagonist_name = basic_info.get('name', '')
        
        if protagonist_name:
            parts.append(f"[主角名]{protagonist_name}(必须严格使用此名字,禁止用其他名字)")
        
        # 获取核心特质
        traits = protagonist.get('traits', [])
        if traits:
            parts.append(f"[核心特质]{', '.join(traits[:3])}")
        
        # 获取标志性细节
        sig = protagonist.get('signature_details', {})
        if isinstance(sig, dict):
            catchphrases = sig.get('catchphrase', [])
            if catchphrases:
                parts.append(f"[口头禅]{catchphrases[0]}")
            actions = sig.get('action', [])
            if actions:
                parts.append(f"[标志性动作]{actions[0]}")
        
        if parts:
            return "\n[角色设定提醒]\n" + "\n".join(parts) + "\n"
        return ""
    
    def _build_chapter_prompt(self, chapter_num: int, chapter_plan: Dict,
                             emotion_beat: Dict, prev_summary: str) -> str:
        """构建章节生成提示词(使用优化后的详细版本)"""
        # 调试：检查 chapter_num
        logger.info(f"[CCG DEBUG] _build_chapter_prompt: chapter_num={chapter_num}, type={type(chapter_num)}")
        
        # 🔥 如果 chapter_num 为 None，直接抛出异常以便追踪堆栈
        if chapter_num is None:
            import traceback
            stack = traceback.format_stack()
            logger.error(f"[CCG {self.session_id}] CRITICAL: chapter_num is None in _build_chapter_prompt!\n调用堆栈:\n{''.join(stack)}")
            raise ValueError(f"chapter_num cannot be None in _build_chapter_prompt")
        
        # 构建主角设定提醒
        protagonist_reminder = self._build_protagonist_reminder()
        
        #  构建世界状态约束提示词
        world_state_constraint = ""
        if self.world_state_manager:
            world_state_constraint = self.world_state_manager.build_constraint_prompt(chapter_num)
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章已添加世界状态约束")
        
        # 记录主角设定提醒
        if protagonist_reminder:
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章已添加主角设定提醒")
        
        #  检查是否有跨批次传递的钩子信息(第2批及以后的第1章)
        cross_batch_hook = chapter_plan.get('hook_from_previous_batch', '')
        cross_batch_summary = chapter_plan.get('prev_chapter_summary', '')
        if cross_batch_hook or cross_batch_summary:
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章检测到跨批次钩子信息")
            # 将跨批次钩子信息添加到prev_summary中
            enhanced_summary = prev_summary or ""
            if cross_batch_summary:
                enhanced_summary = f"[前章结尾内容]{cross_batch_summary}\n\n{enhanced_summary}"
            if cross_batch_hook:
                enhanced_summary = f"[必须承接的钩子]{cross_batch_hook}\n\n{enhanced_summary}"
            prev_summary = enhanced_summary
        
        #  使用从JSON加载的番茄爆款结尾模板
        ending_template_prompt = self._ending_template
        
        #  从配置构建展开策略,弹幕剧本等
        beat_type = chapter_plan.get('beat_type', 'SETUP')
        expansion_strategy = self._build_expansion_strategy_from_config(beat_type)
        bullet_script = self._build_bullet_script_from_config(emotion_beat)
        coherence_check = self._build_coherence_check_from_config(chapter_num)
        self_check_list = self._build_self_check_list_from_config()
        
        #  根据节拍类型自动加载风格指南
        style_guide = self._load_style_guide_for_beat(beat_type)
        
        # 构建增强的章节提示词(填充空白字段)
        enhanced_chapter_plan = chapter_plan.copy()
        enhanced_chapter_plan['expansion_strategy'] = expansion_strategy
        enhanced_chapter_plan['bullet_script'] = bullet_script
        enhanced_chapter_plan['coherence_check'] = coherence_check
        enhanced_chapter_plan['self_check_list'] = self_check_list
        
        # 使用优化器构建详细的章节提示词
        if HAS_OPTIMIZER:
            try:
                optimizer = ChapterPromptOptimizer(self.novel_data)
                chapter_prompt = optimizer.build_chapter_prompt(chapter_num, enhanced_chapter_plan, prev_summary)
                # 在章节提示词前添加主角设定提醒和世界状态约束,后加结尾模板和风格指南
                full_prompt = protagonist_reminder + world_state_constraint + chapter_prompt + ending_template_prompt
                if style_guide:
                    full_prompt += f"\n\n## [本章风格指南]\n{style_guide}"
                return full_prompt
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 优化器失败,使用备用模式: {e}")
        
        # 使用简化版优化器(备用)
        optimizer = SimpleOptimizer(self.novel_data)
        chapter_prompt = optimizer.build_chapter_prompt(chapter_num, enhanced_chapter_plan, prev_summary)
        full_prompt = protagonist_reminder + chapter_prompt + ending_template_prompt
        if style_guide:
            full_prompt += f"\n\n## [本章风格指南]\n{style_guide}"
        return full_prompt
    
    def _build_expansion_strategy_from_config(self, beat_type: str) -> str:
        """从配置构建展开策略"""
        strategies = self._chapter_expansion_prompts.get('expansion_strategies', {})
        strategy = strategies.get(beat_type, strategies.get('SETUP', {}))
        
        if not strategy:
            return "根据章节类型自然展开"
        
        phases = strategy.get('phases', [])
        lines = [f"### {strategy.get('name', beat_type)}"]
        for phase in phases:
            lines.append(f"- {phase.get('range', '')}: {phase.get('name', '')} - {phase.get('content', '')}")
        
        return "\n".join(lines)
    
    def _build_bullet_script_from_config(self, emotion_beat: Dict) -> str:
        """从配置构建弹幕剧本"""
        emotion_type = emotion_beat.get('type', '反转').lower()
        scripts = self._chapter_expansion_prompts.get('bullet_scripts', {})
        
        # 尝试匹配情绪类型
        script = scripts.get(emotion_type, scripts.get('反转', {}))
        
        if not script:
            return "根据情绪变化自然设计弹幕"
        
        phases = script.get('phases', [])
        lines = []
        for phase in phases:
            phase_name = phase.get('phase', '')
            comments = phase.get('comments', [])
            lines.append(f"**{phase_name}**:")
            for comment in comments:
                lines.append(f"  - \"{comment}\"")
        
        return "\n".join(lines)
    
    def _build_coherence_check_from_config(self, chapter_num: int) -> str:
        """从配置构建连贯性检查"""
        # 🔥 调试：检查 chapter_num
        logger.info(f"[CCG DEBUG] _build_coherence_check_from_config: chapter_num={chapter_num}, type={type(chapter_num)}")
        
        # 🔥 如果 chapter_num 为 None，直接抛出异常以便追踪堆栈
        if chapter_num is None:
            import traceback
            stack = traceback.format_stack()
            logger.error(f"[CCG {self.session_id}] CRITICAL: chapter_num is None in _build_coherence_check_from_config!\n调用堆栈:\n{''.join(stack)}")
            raise ValueError(f"chapter_num cannot be None in _build_coherence_check_from_config")
        
        # 确保 chapter_num 是整数
        try:
            chapter_num = int(chapter_num)
        except (TypeError, ValueError) as e:
            raise ValueError(f"chapter_num must be an integer, got {chapter_num} ({type(chapter_num)})") from e
        
        checks = self._chapter_expansion_prompts.get('coherence_checks', [])
        
        # 获取主角信息用于格式化
        protagonist_name = self._get_enforced_protagonist_name()
        roleplay_percent = "90.0"  # 可以从状态管理器获取
        unlocked_abilities = "静电操控, 九霄神雷"  # 可以从状态管理器获取
        
        lines = []
        for check in checks:
            formatted = check.format(
                prev_chapter=chapter_num-1,
                roleplay_percent=roleplay_percent,
                unlocked_abilities=unlocked_abilities
            )
            lines.append(f"- {formatted}")
        
        return "\n".join(lines)
    
    def _build_self_check_list_from_config(self) -> str:
        """从配置构建自检清单"""
        checks = self._chapter_expansion_prompts.get('self_check_list', [])
        return "\n".join([f"- [ ] {check}" for check in checks])
    
    def _get_retry_prompt_template(self, chapter_num: int) -> str:
        """从配置获取重试提示词模板"""
        template = self._chapter_expansion_prompts.get('retry_prompt_template', '')
        if not template:
            raise ValueError("[ChapterConversationGenerator] retry_prompt_template 配置未找到")
        return template.format(chapter_num=chapter_num)
    
    def _get_expansion_prompt_template(self, chapter_num: int, content: str, need_words: int) -> str:
        """从配置获取扩写提示词模板"""
        template = self._chapter_expansion_prompts.get('force_expansion_prompt_template', '')
        if not template:
            raise ValueError("[ChapterConversationGenerator] force_expansion_prompt_template 配置未找到")
        return template.format(
            chapter_num=chapter_num,
            current_words=len(content),
            target_words=len(content) + need_words,
            need_words=need_words,
            content_preview=content[-800:] if len(content) > 800 else content
        )
    
    def _load_style_guide_for_beat(self, beat_type: str) -> str:
        """根据节拍类型加载对应风格指南"""
        try:
            from .style_loader import StyleLoader
            
            # 从映射配置获取 style_id
            mapping = self._beat_style_mapping.get('mapping', {})
            default = self._beat_style_mapping.get('default_mapping', {})
            
            beat_config = mapping.get(beat_type, default)
            style_id = beat_config.get('style_id')
            
            if not style_id:
                logger.debug(f"[章节对话 {self.session_id}] {beat_type} 节拍无对应风格")
                return ""
            
            # 加载风格指南
            style_loader = StyleLoader()
            style = style_loader.load_style(style_id)
            
            if style:
                # 提取核心原则和警告
                principles = style.get('core_principles', [])
                warning = style.get('warning', '')
                
                lines = []
                if warning:
                    lines.append(f"⚠️ {warning}")
                lines.append("**核心原则**:")
                for p in principles[:3]:  # 只取前3条避免过长
                    lines.append(f"- {p}")
                
                logger.info(f"[章节对话 {self.session_id}] 已加载 {style_id} 风格指南用于 {beat_type} 节拍")
                return "\n".join(lines)
            
        except Exception as e:
            logger.warning(f"[章节对话 {self.session_id}] 加载风格指南失败: {e}")
        
        return ""
    
    def _parse_response(self, response) -> Dict:
        """
        解析响应 - 支持多种格式(JSON/分隔符/纯文本)
        
        返回包含 title 和 content 的字典
        自动清理 content 中的标题行
        """
        import re
        
        result = {'title': '', 'content': ''}
        
        if isinstance(response, dict):
            result['title'] = response.get('title', '')
            result['content'] = response.get('content', str(response))
        elif isinstance(response, str):
            cleaned_response = response.strip()
            
            # 策略1: 尝试解析分隔符格式 ---标题---/---正文---
            title_match = re.search(r'---\s*标题\s*---\s*\n?(.*?)\n?---\s*正文\s*---', cleaned_response, re.DOTALL | re.IGNORECASE)
            if title_match:
                result['title'] = title_match.group(1).strip()
                # 正文在 ---正文--- 之后
                content_start = cleaned_response.find('---正文---') + len('---正文---')
                result['content'] = cleaned_response[content_start:].strip()
                logger.info(f"[章节对话] 使用分隔符格式解析,标题: '{result['title']}'")
                return self._clean_result(result)
            
            # 策略2: 移除 Markdown 代码块后尝试解析 JSON
            json_content = cleaned_response
            if json_content.startswith('```'):
                first_newline = json_content.find('\n')
                if first_newline != -1:
                    json_content = json_content[first_newline:].strip()
                if json_content.endswith('```'):
                    json_content = json_content[:-3].strip()
            
            try:
                import json
                parsed = json.loads(json_content)
                if isinstance(parsed, dict):
                    result['title'] = parsed.get('title', '')
                    result['content'] = parsed.get('content', '')
                    logger.info(f"[章节对话] 使用JSON格式解析,标题: '{result['title']}'")
                    return self._clean_result(result)
            except:
                pass
            
            # 策略3: 尝试从 ---正文开始--- 或类似标记提取
            content_markers = ['---正文开始---', '---正文---', '【正文】']
            for marker in content_markers:
                if marker in cleaned_response:
                    parts = cleaned_response.split(marker, 1)
                    if len(parts) == 2:
                        # 尝试从前面的内容提取标题
                        header = parts[0].strip()
                        result['content'] = parts[1].strip()
                        # 从header中提取非章节号的文本作为标题
                        for line in header.split('\n'):
                            line = line.strip()
                            if line and len(line) >= 4 and len(line) <= 20:
                                if not line.startswith('第') and '章' not in line and not line.startswith('---'):
                                    result['title'] = line
                                    break
                        logger.info(f"[章节对话] 使用内容标记解析,标题: '{result['title']}'")
                        return self._clean_result(result)
            
            # 策略4: 纯文本Fallback - 清理第X章后取第一行作为标题
            result['content'] = cleaned_response
            lines = cleaned_response.split('\n')
            for line in lines[:10]:  # 检查前10行
                line = line.strip()
                if not line:
                    continue
                # 跳过章节号行
                if re.match(r'^第[一二三四五六七八九十百千万零\d]+章', line):
                    continue
                if re.match(r'^Chapter\s*\d+', line, re.IGNORECASE):
                    continue
                # 找到可能是标题的行(4-20字,不是特殊标记)
                if 4 <= len(line) <= 20 and not line.startswith('【') and not line.startswith('['):
                    result['title'] = line
                    logger.info(f"[章节对话] 从纯文本提取标题: '{line}'")
                    break
        else:
            result['content'] = str(response)
        
        return self._clean_result(result)
    
    def _clean_result(self, result: Dict) -> Dict:
        """清理结果中的标题行和多余内容"""
        import re
        
        if not result['content']:
            return result
        
        content = result['content']
        original_content = content
        
        # 步骤1: 移除开头可能存在的标题行(各种变体)
        # 匹配 "第X章:标题" "第X章 标题" "第X章：标题" "第一章XXX"
        patterns = [
            r'^[\s]*第[一二三四五六七八九十百千万零\d]+章[：:\s]*[^\n]*\n+',  # 第X章:标题 + 换行
            r'^[\s]*Chapter\s*\d+[：:\s]*[^\n]*\n+',  # Chapter X + 换行
            r'^[\s]*第[一二三四五六七八九十百千万零\d]+章[：:\s]*',  # 只匹配章号
            r'^[\s]*\d+[\s]*章[：:\s]*[^\n]*\n+',  # 数字章
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # 步骤2: 如果提取的标题还在正文开头,移除它
        if result['title']:
            title_pattern = r'^[\s]*' + re.escape(result['title']) + r'[\s]*\n+'
            content = re.sub(title_pattern, '', content)
        
        # 步骤3: 移除开头的空行和特殊标记
        content = content.lstrip('\n').lstrip('\r').lstrip()
        
        # 步骤4: 移除自检报告分隔符及之后的内容
        separators = ['---正文结束---', '【AI自检报告】', '---自检报告---', '【自检报告】']
        for sep in separators:
            if sep in content:
                content = content.split(sep)[0].strip()
        
        if content != original_content:
            logger.info("[章节对话] 已自动清理 content 中的标题行和分隔符")
        
        result['content'] = content
        return result
    
    def _extract_title(self, content: str, chapter_plan: Dict, 
                        ai_title: str = '') -> str:
        """
        提取或生成章节标题
        
        策略(按优先级):
        1. 优先从AI返回的JSON中提取(ai_title参数)
        2. 从chapter_plan获取
        3. 从chapter_plan的event/purpose字段生成
        4. 最后使用默认标题
        
        标题规范:
        - 不再强制截取，保留AI生成的完整标题
        - 只清理"第X章"前缀
        - 确保长度至少4个字
        """
        import re
        
        # 1. 从AI返回的JSON中提取(最高优先级)
        if ai_title:
            title = ai_title.strip()
            # 清理可能存在的"第X章"前缀
            title = re.sub(r'^第[一二三四五六七八九十百千万零\d]+章\s*', '', title)
            # 不再截断标题，保留完整格式
            if len(title) >= 4:
                return self._ensure_unique_title(title)
        
        # 2. 从chapter_plan获取标题
        if chapter_plan:
            title = chapter_plan.get('title', '').strip()
            if title and title != '章节' and len(title) >= 4:
                # 清理"第X章"前缀
                title = re.sub(r'^第[一二三四五六七八九十百千万零\d]+章\s*', '', title)
                # 不再截断标题
                return self._ensure_unique_title(title)
            
            # 从event字段生成
            event = chapter_plan.get('event', '').strip()
            if event and len(event) >= 4:
                return self._ensure_unique_title(event)
            
            # 从purpose字段生成
            purpose = chapter_plan.get('purpose', '').strip()
            if purpose and len(purpose) >= 4:
                return self._ensure_unique_title(purpose)
            
            # 从hook_content获取
            hook = chapter_plan.get('hook_content', '').strip()
            if hook and len(hook) >= 4:
                return self._ensure_unique_title(hook)
        
        # 3. 从内容前10行分析提取(备用方案)
        lines = content.strip().split('\n')
        for line in lines[:10]:
            line = line.strip()
            if line.startswith('第') and '章' in line[:10]:
                continue
            if 8 <= len(line) <= 30 and not line.startswith('[') and not line.startswith('('):
                return self._ensure_unique_title(line)
        
        # 4. 默认返回
        return self._ensure_unique_title('剧情推进')
    
    def _smart_truncate_title(self, title: str, max_length: int = 14) -> str:
        """
        智能截断标题
        
        策略:
        1. 如果标题长度在限制内，直接返回
        2. 优先在标点符号处截断（，。！？；）
        3. 其次在词语边界截断（避免截断词中间）
        4. 确保截断后至少有4个字
        
        Args:
            title: 原始标题
            max_length: 最大长度限制
            
        Returns:
            截断后的标题
        """
        if not title or len(title) <= max_length:
            return title
        
        # 标点符号优先级（越靠前越优先截断）
        punctuations = ['，', '。', '！', '？', '；', '、', ',', '!', '?', ';']
        
        # 策略1: 在标点处截断
        truncated = title[:max_length]
        for punct in punctuations:
            last_punct_pos = truncated.rfind(punct)
            if last_punct_pos > 4:  # 确保截断后至少有4个字
                return truncated[:last_punct_pos]
        
        # 策略2: 在词语边界截断（中文通常在2-4字词组后）
        # 常见词边界模式：避免在"的"、"了"、"着"等虚词前截断
        weak_boundaries = ['的', '了', '着', '过', '是', '在', '和', '与']
        for i in range(max_length - 1, 3, -1):
            if title[i] not in weak_boundaries:
                return title[:i + 1]
        
        # 策略3: 硬截断（保底）
        return title[:max_length]
    
    def _ensure_unique_title(self, title: str) -> str:
        """
        确保标题唯一性
        如果标题已存在,则添加 (1), (2) 等序号
        """
        if not title:
            title = '剧情推进'
        
        # 清理标题中的"第X章"前缀
        import re
        clean_title = re.sub(r'^第[一二三四五六七八九十百千万零\d]+章\s*', '', title)
        if not clean_title:
            clean_title = '剧情推进'
        
        # 检查是否已存在
        original_title = clean_title
        counter = 1
        
        while clean_title in self._chapter_titles:
            clean_title = f"{original_title} ({counter})"
            counter += 1
        
        self._chapter_titles.add(clean_title)
        return clean_title
    
    def _summarize_chapter(self, chapter: Dict) -> str:
        """
        生成章节摘要(用于上下文衔接)
        
        修复:提取章尾钩子和关键结果,而不是开头内容
        这样才能保证前后章节衔接连贯
        """
        content = chapter.get('content', '')
        if not content:
            return ""
        
        # 提取最后300字(章尾内容,包含钩子和悬念)
        ending = content[-300:] if len(content) > 300 else content
        
        # 尝试提取最后一段(通常是钩子)
        paragraphs = content.strip().split('\n')
        last_paragraph = paragraphs[-1] if paragraphs else ""
        
        # 构建摘要:最后一段 + 结尾上下文
        summary_parts = []
        
        # 如果有标题,包含标题
        title = chapter.get('title', '')
        if title:
            summary_parts.append(f"章标题:{title}")
        
        # 包含最后一段(钩子)
        if last_paragraph and len(last_paragraph) > 10:
            summary_parts.append(f"章尾钩子:{last_paragraph[:150]}")
        
        # 包含结尾上下文
        if len(ending) > len(last_paragraph):
            summary_parts.append(f"结尾上下文:{ending[:200]}")
        
        summary = " | ".join(summary_parts)
        return summary if summary else ending[:200]
    
    def get_quality_summary(self) -> Dict:
        """
        获取质检汇总报告
        
        Returns:
            质检汇总信息
        """
        if not self.quality_reports:
            return {"status": "未启用质检或没有报告"}
        
        total = len(self.quality_reports)
        passed = len([r for r in self.quality_reports if r.can_generate])
        failed = total - passed
        avg_score = sum(r.score for r in self.quality_reports) / total if total > 0 else 0
        
        # 统计问题
        total_issues = sum(len(r.issues) for r in self.quality_reports)
        # 🔥 修复：兼容 severity 是 Enum 或字典的情况
        def get_severity_name(sev):
            try:
                # 先尝试作为 Enum 访问
                if hasattr(sev, 'name'):
                    return sev.name
            except (AttributeError, TypeError):
                pass
            # 尝试作为字典访问
            if isinstance(sev, dict):
                return sev.get('name', '')
            # 尝试获取 value 属性（Enum 的另一种形式）
            try:
                if hasattr(sev, 'value'):
                    return sev.value
            except (AttributeError, TypeError):
                pass
            return str(sev)
        
        critical_issues = sum(
            len([i for i in r.issues if get_severity_name(i.severity) == "CRITICAL"])
            for r in self.quality_reports
        )
        
        return {
            "total_chapters": total,
            "passed": passed,
            "failed": failed,
            "avg_score": round(avg_score, 1),
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "0%",
            "status": "质检完成" if total > 0 else "未开始"
        }
    
    def _trigger_stage_review(self, chapter_num: int, chapters: List[Dict]):
        """
         触发滑动窗口阶段性复盘
        
        每生成一批章节后,检查哪些滑动窗口已完整(10章),逐个窗口优化.
        
        滑动窗口配置:
        - 窗口大小:10章
        - 重叠:2章(保证连贯性)
        - 步长:8章
        
        窗口序列示例:
        - 窗口1: 第1-10章(第10章生成后可用)
        - 窗口2: 第8-17章(第17章生成后可用,重叠8-9章)
        - 窗口3: 第16-25章(第25章生成后可用,重叠16-17章)
        
        示例:
        - 生成1-6章 -> 无完整窗口
        - 生成7-14章 -> 第10章已完成,触发窗口1(1-10)优化
        - 生成15-22章 -> 第17章已完成,触发窗口2(8-17)优化
        """
        if not self.stage_review_optimizer or not self.project_path:
            return
        
        logger.info(f"[章节对话 {self.session_id}] 🔍 检查滑动窗口优化条件(当前第{chapter_num}章)")
        
        try:
            # 计算哪些滑动窗口已完整且未优化过
            windows_to_optimize = self._calculate_ready_windows(chapter_num)
            
            if not windows_to_optimize:
                logger.info(f"[章节对话 {self.session_id}] 暂无完整的滑动窗口需要优化")
                return
            
            logger.info(f"[章节对话 {self.session_id}]  发现 {len(windows_to_optimize)} 个窗口待优化 ")
            
            # 逐个窗口进行优化
            for window_start, window_end in windows_to_optimize:
                self._optimize_single_window(window_start, window_end)
                
        except Exception as e:
            logger.error(f"[章节对话 {self.session_id}] 滑动窗口优化失败: {e}")
            # 复盘失败不应中断生成流程
    
    def _calculate_ready_windows(self, current_chapter: int) -> List[Tuple[int, int]]:
        """
        计算哪些滑动窗口已完整且未优化过
        
        Returns:
            列表 of (window_start, window_end)
        """
        window_size = 10  # 默认窗口大小
        overlap = 2       # 默认重叠
        step = window_size - overlap  # 8
        
        ready_windows = []
        
        # 计算所有可能的窗口
        window_idx = 0
        while True:
            window_start = 1 + window_idx * step
            window_end = window_start + window_size - 1
            
            logger.debug(f"[章节对话 {self.session_id}] 检查窗口: {window_start}-{window_end} (当前章节: {current_chapter})")
            
            # 如果窗口结束超出当前章节,停止
            if window_end > current_chapter:
                logger.debug(f"[章节对话 {self.session_id}] 窗口 {window_start}-{window_end} 超出当前章节 {current_chapter},停止")
                break
            
            # 检查这个窗口是否已经优化过
            window_key = f"{window_start}_{window_end}"
            if window_key not in self.stage_review_triggered:
                # 额外检查:窗口内所有章节是否都存在
                chapters_exist = True
                for ch_num in range(window_start, window_end + 1):
                    chapter_file = self.project_path / "chapters" / f"chapter_{ch_num:03d}.json"
                    if not chapter_file.exists():
                        chapters_exist = False
                        logger.warning(f"[章节对话 {self.session_id}] 窗口 {window_start}-{window_end} 缺少第{ch_num}章,跳过")
                        break
                
                if chapters_exist:
                    ready_windows.append((window_start, window_end))
                    logger.info(f"[章节对话 {self.session_id}] 窗口 {window_start}-{window_end} 已就绪(当前第{current_chapter}章)")
            else:
                logger.debug(f"[章节对话 {self.session_id}] 窗口 {window_start}-{window_end} 已优化过")
            
            window_idx += 1
        
        return ready_windows
    
    def _optimize_single_window(self, window_start: int, window_end: int):
        """
        优化单个滑动窗口
        
        Args:
            window_start: 窗口起始章节
            window_end: 窗口结束章节
        """
        window_key = f"{window_start}_{window_end}"
        self.stage_review_triggered.add(window_key)
        
        logger.info(f"[章节对话 {self.session_id}] 🔄 开始优化窗口 {window_start}-{window_end}")
        
        try:
            # 调用优化器优化单个窗口
            report = self.stage_review_optimizer.optimize_window(window_start, window_end)
            
            # 记录优化结果
            issues_found = len(report.get('issues', []))
            fixes_applied = len(report.get('fixes_applied', []))
            
            logger.info(f"[章节对话 {self.session_id}] ✅ 窗口 {window_start}-{window_end} 优化完成 | 问题: {issues_found} | 修复: {fixes_applied}")
            
            # 如果有严重问题,记录警告
            if issues_found > 0:
                high_priority = [i for i in report.get('issues', []) if i.get('severity') == 'high']
                if high_priority:
                    logger.warning(f"[章节对话 {self.session_id}] ⚠️ 窗口 {window_start}-{window_end} 发现 {len(high_priority)} 个高优先级问题")
            
            # 保存窗口优化报告
            report_path = Path(self.project_path) / f"window_review_{window_start}_{window_end}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"[章节对话 {self.session_id}] 📝 窗口优化报告已保存: {report_path}")
            
        except Exception as e:
            logger.error(f"[章节对话 {self.session_id}] ❌ 窗口 {window_start}-{window_end} 优化失败: {e}")


# 便捷函数
def generate_chapters_with_conversation(api_client, novel_data: Dict, 
                                       blueprint: Dict, tropes: Dict,
                                       start_chapter: int, end_chapter: int,
                                       progress_callback=None,
                                       quality_config: Dict = None) -> List[Dict]:
    """
    使用对话模式生成章节(支持质检配置)
    
    Args:
        api_client: API客户端
        novel_data: 小说数据
        blueprint: 章节规划
        tropes: 套路数据
        start_chapter: 起始章节
        end_chapter: 结束章节
        progress_callback: 进度回调
        quality_config: 质检配置(可选)
            {
                "enabled": True,          # 是否启用质检
                "min_score": 70,          # 最低通过分数
                "auto_fix": True,         # 是否自动修复
                "stop_on_critical": True  # 严重问题是否停止
            }
    
    Returns:
        生成的章节列表
    """
    generator = ChapterConversationGenerator(
        api_client, novel_data, tropes, quality_config
    )
    chapters = generator.generate_chapters(
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        blueprint=blueprint,
        progress_callback=progress_callback
    )
    
    # 输出质检汇总
    quality_summary = generator.get_quality_summary()
    if quality_summary.get("status") == "质检完成":
        logger.info(
            f"[章节生成完成] 质检汇总: "
            f"通过率 {quality_summary['pass_rate']}, "
            f"平均分 {quality_summary['avg_score']}, "
            f"严重问题 {quality_summary['critical_issues']}个"
        )
    
    return chapters
