"""
对话模式章节生成器
在一个连续对话中批量生成多章，保持上下文连贯

v3.0更新：
1. 使用优化后的提示词系统
2. 集成AI质检系统，生成前自动检查质量
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# 导入优化的提示词构建器（优先使用v3.0）
try:
    from .chapter_prompt_optimizer_v3 import ChapterPromptOptimizerV3 as ChapterPromptOptimizer
    HAS_OPTIMIZER = True
    OPTIMIZER_VERSION = "3.0"
    logging.info("[ChapterConversationGenerator] 已加载提示词优化器 v3.0（番茄爆款版）")
except ImportError:
    try:
        from .chapter_prompt_optimizer import ChapterPromptOptimizer
        HAS_OPTIMIZER = True
        OPTIMIZER_VERSION = "2.0"
        logging.info("[ChapterConversationGenerator] 已加载提示词优化器 v2.0")
    except ImportError:
        HAS_OPTIMIZER = False
        OPTIMIZER_VERSION = None
        logging.warning("[ChapterConversationGenerator] 提示词优化器未加载，使用传统模式")

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

# 导入TropePromptBuilder（分层System Prompt支持）
try:
    from .trope_prompt_builder import TropePromptBuilder
    HAS_TROPE_PROMPT_BUILDER = True
    logging.info("[ChapterConversationGenerator] 已加载TropePromptBuilder")
except ImportError:
    HAS_TROPE_PROMPT_BUILDER = False
    logging.warning("[ChapterConversationGenerator] TropePromptBuilder未加载")

# 导入章节信息提取器（AI自动提取）
try:
    from .chapter_info_extractor import ChapterInfoExtractor
    HAS_INFO_EXTRACTOR = True
    logging.info("[ChapterConversationGenerator] 已加载信息提取器")
except ImportError:
    HAS_INFO_EXTRACTOR = False
    logging.warning("[ChapterConversationGenerator] 信息提取器未加载")
    
# 定义备用的优化器（简化版）
class SimpleOptimizer:
    """简化版优化器（备用）"""
    def __init__(self, novel_data):
        # 确保 novel_data 是字典类型
        if isinstance(novel_data, list):
            novel_data = novel_data[0] if novel_data else {}
        if not isinstance(novel_data, dict):
            novel_data = {}
        self.novel_data = novel_data
    
    def build_system_prompt(self):
        title = self.novel_data.get('title', '未命名')
        return f"""# 角色：顶级网络小说作家

你正在为小说《{title}》生成章节。

## 写作规范
1. **番茄风格**：快节奏、强爽点、章章有钩子
2. **每章2000-2500字**
3. **第三人称上帝视角**
4. **短段落**：每段不超过3行
5. **多对话**：对话占比≥40%
6. **情绪精准**：严格按照每章指定的情绪类型写作

## 重要规则
1. **保持人设一致**：主角性格、能力必须前后一致
2. **承上启下**：每章结尾必须留下钩子
3. **不跳剧情**：严格按照剧情路线推进
"""
    
    def build_chapter_prompt(self, chapter_num, blueprint, prev_summary):
        parts = [
            f"请生成第{chapter_num}章。",
            "",
            "## 写作要求",
            "1. 字数2000-2500字",
            "2. 承接前文",
            "3. 本章必须有爽点或钩子",
            "4. 章尾留悬念",
            "",
            "直接输出章节正文。"
        ]
        return "\n".join(parts)

logger = logging.getLogger(__name__)


class ChapterConversationGenerator:
    """
    章节对话生成器
    
    特点：
    1. 创建一个长对话会话
    2. 连续生成多章，每章都基于前文上下文
    3. 利用 Kimi 256K 上下文窗口，可连续生成 10-20 章
    4. 集成AI质检系统，生成前自动检查质量
    """
    
    # 质检配置
    QUALITY_CHECK_CONFIG = {
        "enabled": True,           # 是否启用质检
        "min_score": 70,           # 最低通过分数
        "auto_fix": True,          # 是否自动修复问题
        "stop_on_critical": True,  # 遇到严重问题是否停止
        "log_level": "info",       # 日志级别：debug/info/warning
    }
    
    def __init__(self, api_client, novel_data: Dict, tropes: Dict, 
                 quality_config: Dict = None,
                 world_state_manager=None):  # 🔥 世界状态管理器
        self.api_client = api_client
        # 确保 novel_data 是字典类型
        if isinstance(novel_data, list):
            logger.warning(f"[ChapterConversationGenerator] novel_data 是列表类型，转换为字典")
            novel_data = novel_data[0] if novel_data else {}
        if not isinstance(novel_data, dict):
            logger.warning(f"[ChapterConversationGenerator] novel_data 类型异常: {type(novel_data)}，使用空字典")
            novel_data = {}
        self.novel_data = novel_data
        self.tropes = tropes
        self.session = None
        self.logger = None  # 对话日志记录器
        self.quality_checker = None  # 质量检查器
        self.quality_reports = []  # 质检报告列表
        self.world_state_manager = world_state_manager  # 🔥 世界状态管理器
        
        # 质检配置
        if quality_config:
            self.QUALITY_CHECK_CONFIG.update(quality_config)
        
        # 提取小说基本信息
        self.novel_title = novel_data.get('title', '未命名')
        
        # 生成会话ID（包含书名前缀，便于识别）
        import uuid
        # 书名处理：取前10个字符，去除特殊字符
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
        
        # 初始化信息提取器（AI自动提取章节信息）
        self.info_extractor = None
        if HAS_INFO_EXTRACTOR:
            try:
                self.info_extractor = ChapterInfoExtractor(api_client)
                logging.info(f"[章节对话 {self.session_id}] 信息提取器已启动")
            except Exception as e:
                logging.warning(f"[章节对话 {self.session_id}] 信息提取器初始化失败: {e}")
        
        # 初始化主角名称
        self.protagonist_name = self._get_protagonist_name()
    
    def _sanitize_title(self, title: str) -> str:
        """清理书名，去除特殊字符，用于文件名"""
        import re
        # 保留中文、英文、数字
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
            provider="kimi",
            purpose_prefix=f"{self.session_id}"
        )
        # 设置历史限制
        session.max_history = 50  # 保留更多历史，支持多章连贯
        
        logger.info(f"[章节对话 {self.session_id}] 会话创建 | 小说: {self.novel_title} | 起始章: {start_chapter}")
        return session
    
    def _get_enforced_protagonist_name(self) -> str:
        """获取强制主角名（多层回退，确保有值）"""
        # 第一层：user_choices（用户填写的）
        user_choices = self.novel_data.get('user_choices', {})
        name = user_choices.get('protagonist_name', '')
        if name:
            return name
        
        # 第二层：character_design.protagonist.name
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
        
        # 第三层：plan.protagonist
        plan = self.novel_data.get('plan', {})
        plan_protagonist = plan.get('protagonist', {})
        if isinstance(plan_protagonist, dict):
            name = plan_protagonist.get('name', '')
            if name:
                return name
        
        # 最后回退
        logger.warning(f"[章节对话 {self.session_id}] 警告：未能找到主角名！")
        return '主角'
    
    def _build_system_prompt(self, start_chapter: int) -> str:
        """构建系统提示词（使用TropePromptBuilder分层架构）"""
        # 获取强制主角名
        protagonist_name = self._get_enforced_protagonist_name()
        
        # 使用TropePromptBuilder构建System Prompt（分层架构）
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
【角色设定 - 绝对不可更改】
主角姓名：{protagonist_name}
约束：
1. 必须使用此名字，禁止编造其他名字（如林枫、林霄等）
2. 每章正文必须多次出现主角名字，不能用"他"代替
3. 如果前文有错误名字，本章必须纠正回来
4. 违反此设定视为严重错误
"""
                return system_prompt + enforcement
                
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] TropePromptBuilder失败，回退到优化器: {e}")
        
        # 回退到原有优化器
        if HAS_OPTIMIZER:
            try:
                optimizer = ChapterPromptOptimizer(self.novel_data)
                system_prompt = optimizer.build_system_prompt()
                logger.info(f"[章节对话 {self.session_id}] 使用优化的System Prompt v2.0 | 主角: {protagonist_name}")
                
                enforcement = f"""【角色设定 - 绝对不可更改】
主角姓名：{protagonist_name}
约束：
1. 必须使用此名字，禁止编造其他名字（如林枫、林霄等）
2. 每章正文必须多次出现主角名字，不能用"他"代替
3. 如果前文有错误名字，本章必须纠正回来
4. 违反此设定视为严重错误

"""
                return enforcement + system_prompt
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 优化器失败，使用备用模式: {e}")
        
        # 使用简化版优化器（备用）
        optimizer = SimpleOptimizer(self.novel_data)
        return optimizer.build_system_prompt()
    
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
        total = end_chapter - start_chapter + 1
        logger.info(f"[章节对话 {self.session_id}] 开始生成第{start_chapter}-{end_chapter}章 | 共{total}章")
        
        # 创建会话
        self.session = self._create_session(start_chapter)
        
        chapters = []
        prev_chapter_summary = ""  # 上一章摘要
        
        for i, chapter_num in enumerate(range(start_chapter, end_chapter + 1)):
            logger.info(f"[章节对话 {self.session_id}] 生成第{chapter_num}章 ({i+1}/{total})")
            
            try:
                # 生成单章
                chapter = self._generate_single_chapter_in_session(
                    chapter_num=chapter_num,
                    blueprint=blueprint,
                    prev_summary=prev_chapter_summary
                )
                
                chapters.append(chapter)
                
                # 更新上一章摘要（用于上下文）
                prev_chapter_summary = self._summarize_chapter(chapter)
                
                # 进度回调
                if progress_callback:
                    progress_callback(chapter_num, total)
                
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章完成 | 字数: {chapter.get('word_count', 0)}")
                
            except Exception as e:
                logger.error(f"[章节对话 {self.session_id}] 第{chapter_num}章失败: {e}")
                # 记录失败但不中断
                chapters.append({
                    "chapter_number": chapter_num,
                    "title": f"第{chapter_num}章（生成失败）",
                    "content": f"生成失败: {str(e)}",
                    "word_count": 0,
                    "quality_score": 0,
                    "error": str(e)
                })
        
        logger.info(f"[章节对话 {self.session_id}] 生成完成 | 成功: {len([c for c in chapters if c.get('word_count', 0) > 0])}/{total}章 | 总轮次: {self.session.turn_count}")
        
        # 🔥 批量保存提取的信息到世界状态文件
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
            import os
            project_path = os.environ.get('NOVEL_PROJECT_PATH', '.')
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
    
    def _generate_single_chapter_in_session(self, chapter_num: int, 
                                            blueprint: Dict,
                                            prev_summary: str) -> Dict:
        """在会话中生成单章（集成质检）"""
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
        
        # ===== 质检环节（v3.0新增）=====
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
                            f"第{chapter_num}章提示词质量不达标（分数: {quality_report.score}），"
                            f"严重问题: {len(critical_issues)}个"
                        )
                
                # 检查分数
                if quality_report.score < self.QUALITY_CHECK_CONFIG["min_score"]:
                    logger.warning(
                        f"[章节对话 {self.session_id}] 第{chapter_num}章分数较低({quality_report.score})，"
                        f"但仍继续生成"
                    )
                
                # 自动修复
                if self.QUALITY_CHECK_CONFIG["auto_fix"] and quality_report.optimized_prompt:
                    original_score = quality_report.score
                    optimized_prompt = quality_report.optimized_prompt
                    
                    # 简单判断：如果优化后的提示词明显更长，可能添加了修复内容
                    if len(optimized_prompt) > len(prompt) * 1.1:
                        logger.info(
                            f"[章节对话 {self.session_id}] 第{chapter_num}章已自动优化提示词 "
                            f"({len(prompt)} → {len(optimized_prompt)} 字符)"
                        )
                        prompt = optimized_prompt
                        
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 质检过程出错: {e}")
                # 质检出错不阻断生成，继续执行
        
        # 在会话中发送消息
        logger.info(f"[章节对话 {self.session_id}] 发送第{chapter_num}章提示词 | 当前历史: {len(self.session.messages)}条")
        response = self.session.send_message(
            user_prompt=prompt,
            temperature=0.7,
            purpose=f"第{chapter_num}章"
        )
        logger.info(f"[章节对话 {self.session_id}] 接收第{chapter_num}章响应 | 总轮次: {self.session.turn_count}")
        
        # 记录对话日志（如果日志记录器可用）
        if self.logger and HAS_CONVERSATION_LOGGER:
            try:
                # 构建消息列表用于日志记录
                messages_for_log = []
                if hasattr(self.session, 'messages') and self.session.messages:
                    for msg in self.session.messages[-2:]:  # 记录最后两条（user + assistant）
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
        
        # 解析内容
        content = self._parse_response(response)
        
        # 🔥 校验1：检查是否只返回了自检报告而没有正文
        if self._is_only_self_check_report(content):
            logger.error(f"[章节对话 {self.session_id}] 第{chapter_num}章只返回了自检报告，没有正文！可能是token限制或上下文过长。")
            # 尝试重试一次
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章尝试重试...")
            
            # 简化提示词重试
            retry_prompt = f"请生成第{chapter_num}章正文，约2000-2500字。要求：快节奏爽文，强情绪流，章章有钩子。直接输出正文，不需要自检报告。"
            retry_response = self.session.send_message(
                user_prompt=retry_prompt,
                temperature=0.7,
                purpose=f"第{chapter_num}章(重试)"
            )
            content = self._parse_response(retry_response)
            
            # 再次校验
            if self._is_only_self_check_report(content):
                raise Exception(f"第{chapter_num}章重试后仍只返回自检报告，请检查token限制或减少每批章节数")
        
        # 🔥 校验2：检查和修复主角名
        content = self._validate_and_fix_protagonist_name(content, chapter_num)
        
        # 🔥 校验3：使用 WorldStateManager 校验剧情连贯性
        if self.world_state_manager:
            issues = self.world_state_manager.validate_chapter(chapter_num, content)
            if issues:
                logger.warning(f"[章节对话 {self.session_id}] 第{chapter_num}章剧情校验发现问题:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
            
            # 更新世界状态（用于下一章）
            self.world_state_manager.update_after_chapter(chapter_num, content)
        
        # 🔥 后处理：提取正文部分（根据分隔符）
        content = self._extract_main_content(content, chapter_num)
        
        # 🔥 字数强制检查（更严格）
        word_count = len(content)
        
        if word_count < 2000:
            # 低于2000字：必须扩写到2200+
            logger.warning(f"[章节对话 {self.session_id}] 第{chapter_num}章字数严重不足({word_count}<2000)，强制扩写...")
            content = self._expand_chapter(content, chapter_num, 2200 - word_count)
            word_count = len(content)
        elif word_count < 2200:
            # 2000-2200字：建议扩写
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章字数略低({word_count})，建议扩写到2200+...")
            content = self._expand_chapter(content, chapter_num, 2200 - word_count)
            word_count = len(content)
        
        # 🔥 AI信息提取：自动提取角色、钩子、世界设定等信息
        chapter_data = {
            "chapter_number": chapter_num,
            "title": self._extract_title(content, chapter_plan),
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
        格式：正文内容 + ---正文结束--- + 自检报告
        """
        # 尝试找到分隔符
        separators = [
            '---正文结束---',
            '【AI自检报告】',
            '自检报告：',
            '【自检报告】'
        ]
        
        for sep in separators:
            if sep in content:
                # 找到分隔符，提取前面的内容
                main_content = content.split(sep)[0].strip()
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章使用分隔符'{sep}'提取正文: {len(main_content)}字")
                return main_content
        
        # 没有找到分隔符，尝试其他方式
        # 如果包含"自检报告"字样，尝试提取前面部分
        if '自检' in content or '字数：' in content:
            # 找到最后一章标题的位置，之后通常是自检报告
            lines = content.split('\n')
            main_lines = []
            for line in lines:
                if '自检' in line or '字数：' in line or '番茄算法' in line:
                    break
                main_lines.append(line)
            if main_lines:
                main_content = '\n'.join(main_lines).strip()
                logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章通过关键词提取正文: {len(main_content)}字")
                return main_content
        
        # 没有找到任何标记，返回原内容
        return content.strip()
    
    def _expand_chapter(self, content: str, chapter_num: int, need_words: int) -> str:
        """
        强制扩写 - 确保字数达标
        """
        if need_words <= 0:
            return content
            
        try:
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章开始扩写，需要+{need_words}字")
            
            prompt = f"""请基于以下已有章节内容，**必须**补充{need_words}字以上。

**当前字数：{len(content)}字，需要扩写到{len(content) + need_words}字以上**

**扩写策略（按优先级）：**
1. **弹幕反应链**（推荐，+200-400字）
   - 现场围观者反应（表情、惊呼）
   - 直播间弹幕（5-8条具体弹幕内容）
   - 社交媒体发酵（热搜、朋友圈、论坛）

2. **震惊层级递进**（推荐，+200-400字）
   - 第一层：现场人物反应（反派/配角）
   - 第二层：暗处观战者反应（强者感应）
   - 第三层：大范围影响（全城/全网震动）

3. **数字可视化**（国运文适用，+100-200字）
   - 国运值变化的天空异象
   - 战力数值的气场表现
   - 奖励获得的具体展示

4. **情绪渲染链**（+100-200字）
   - 主角：微表情、小动作（非内心独白）
   - 配角：从质疑到震惊到跪服的转变
   - 反派：从嚣张到恐惧到绝望的过程

**扩写要求：**
- 必须增加{need_words}字以上
- 必须是有内容的扩写，不能水字数
- 优先使用弹幕和震惊层级（效果最明显）

**禁止（这些会被删除）：**
- 环境描写（天气、景色）
- 心理独白（超过1行的内心戏）
- 重复对话

已有内容（最后800字，请在此区域前/中插入扩写）：
...{content[-800:]}

请直接输出**完整章节**（原文+扩写内容合并），确保总字数达到{len(content) + need_words}字以上："""

            response = self.session.send_message(
                user_prompt=prompt,
                temperature=0.8,
                purpose=f"第{chapter_num}章强制扩写"
            )
            
            full_content = self._parse_response(response)
            
            # 验证扩写后字数
            final_count = len(full_content)
            if final_count < len(content) + need_words * 0.8:  # 允许20%误差
                logger.warning(f"[章节对话 {self.session_id}] 扩写后字数({final_count})仍不足，原始{len(content)}，需要+{need_words}")
                # 如果还不够，在末尾追加扩写标记提示
                return full_content + f"\n\n【注：当前{final_count}字，仍需扩写】"
            
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章扩写完成: {final_count}字 (原{len(content)}字)")
            return full_content
            
        except Exception as e:
            logger.warning(f"[章节对话 {self.session_id}] 扩写失败: {e}")
            return content
    
    def _insert_expansion(self, original: str, expansion: str) -> str:
        """
        将扩写内容智能插入到原文中
        优先插入到高潮/爽点段落，而不是末尾
        """
        # 查找高潮标记词位置
        climax_markers = ['"轰！"', '"砰！"', '"轰隆！"', '炸裂', '爆发', '震惊']
        
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
        
        # 如果只包含自检报告标记，没有正文
        if content.startswith("【AI自检报告") and "第" not in content[:50]:
            return True
        
        # 如果字数太少（少于300字），认为没有正文
        if len(content) < 300:
            return True
        
        # 检查是否只有自检报告部分
        lines = content.split('\n')
        report_lines = [l for l in lines if l.startswith("【AI自检报告") or l.startswith("总字数：") or l.startswith("番茄算法：")]
        if len(report_lines) >= 3 and len(content) < 500:
            return True
        
        return False
    
    def _validate_and_fix_protagonist_name(self, content: str, chapter_num: int) -> str:
        """校验并修复主角名"""
        protagonist_name = self._get_enforced_protagonist_name()
        
        # 常见错误名字映射（根据实际问题定制）
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
                fixes.append(f"{wrong_name}→{correct_name}({count}处)")
        
        if fixes:
            logger.warning(f"[章节对话 {self.session_id}] 第{chapter_num}章自动修复角色名: {', '.join(fixes)}")
        
        # 检查正文是否完全没有主角名（可能只用了"他"）
        if protagonist_name not in content:
            logger.error(f"[章节对话 {self.session_id}] 第{chapter_num}章警告：正文可能缺少主角名'{protagonist_name}'")
            # 不抛出异常，因为可能是正文还没展开
        
        return content
    
    def _build_protagonist_reminder(self) -> str:
        """构建主角设定提醒（防止AI忘记主角名）"""
        char_design = self.novel_data.get('character_design', {})
        if not char_design:
            return ""
        
        protagonist = char_design.get('protagonist', {})
        if not protagonist:
            return ""
        
        parts = []
        
        # 获取主角名（优先使用user_choices中的）
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
            parts.append(f"【主角名】{protagonist_name}（必须严格使用此名字，禁止用其他名字）")
        
        # 获取核心特质
        traits = protagonist.get('traits', [])
        if traits:
            parts.append(f"【核心特质】{', '.join(traits[:3])}")
        
        # 获取标志性细节
        sig = protagonist.get('signature_details', {})
        if isinstance(sig, dict):
            catchphrases = sig.get('catchphrase', [])
            if catchphrases:
                parts.append(f"【口头禅】{catchphrases[0]}")
            actions = sig.get('action', [])
            if actions:
                parts.append(f"【标志性动作】{actions[0]}")
        
        if parts:
            return "\n【角色设定提醒】\n" + "\n".join(parts) + "\n"
        return ""
    
    def _build_chapter_prompt(self, chapter_num: int, chapter_plan: Dict,
                             emotion_beat: Dict, prev_summary: str) -> str:
        """构建章节生成提示词（使用优化后的详细版本）"""
        # 构建主角设定提醒
        protagonist_reminder = self._build_protagonist_reminder()
        
        # 🔥 构建世界状态约束提示词
        world_state_constraint = ""
        if self.world_state_manager:
            world_state_constraint = self.world_state_manager.build_constraint_prompt(chapter_num)
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章已添加世界状态约束")
        
        # 记录主角设定提醒
        if protagonist_reminder:
            logger.info(f"[章节对话 {self.session_id}] 第{chapter_num}章已添加主角设定提醒")
        
        # 使用优化器构建详细的章节提示词
        if HAS_OPTIMIZER:
            try:
                optimizer = ChapterPromptOptimizer(self.novel_data)
                chapter_prompt = optimizer.build_chapter_prompt(chapter_num, chapter_plan, prev_summary)
                # 在章节提示词前添加主角设定提醒和世界状态约束
                return protagonist_reminder + world_state_constraint + chapter_prompt
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 优化器失败，使用备用模式: {e}")
        
        # 使用简化版优化器（备用）
        optimizer = SimpleOptimizer(self.novel_data)
        chapter_prompt = optimizer.build_chapter_prompt(chapter_num, chapter_plan, prev_summary)
        return protagonist_reminder + chapter_prompt
    
    def _parse_response(self, response) -> str:
        """解析响应"""
        if isinstance(response, str):
            return response
        elif isinstance(response, dict):
            return response.get("content", str(response))
        return str(response)
    
    def _extract_title(self, content: str, chapter_plan: Dict) -> str:
        """提取标题"""
        # 尝试从内容第一行提取
        lines = content.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if '第' in first_line and '章' in first_line:
                return first_line
        return chapter_plan.get('title', '章节')
    
    def _summarize_chapter(self, chapter: Dict) -> str:
        """生成章节摘要（用于上下文）"""
        # 简化：提取前200字作为摘要
        content = chapter.get('content', '')
        return content[:200] + "..." if len(content) > 200 else content
    
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
        critical_issues = sum(
            len([i for i in r.issues if i.severity.name == "CRITICAL"])
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


# 便捷函数
def generate_chapters_with_conversation(api_client, novel_data: Dict, 
                                       blueprint: Dict, tropes: Dict,
                                       start_chapter: int, end_chapter: int,
                                       progress_callback=None,
                                       quality_config: Dict = None) -> List[Dict]:
    """
    使用对话模式生成章节（支持质检配置）
    
    Args:
        api_client: API客户端
        novel_data: 小说数据
        blueprint: 章节规划
        tropes: 套路数据
        start_chapter: 起始章节
        end_chapter: 结束章节
        progress_callback: 进度回调
        quality_config: 质检配置（可选）
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
