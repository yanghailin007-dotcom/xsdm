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
    
# 定义备用的优化器（简化版）
class SimpleOptimizer:
    """简化版优化器（备用）"""
    def __init__(self, novel_data):
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
                 quality_config: Dict = None):
        self.api_client = api_client
        self.novel_data = novel_data
        self.tropes = tropes
        self.session = None
        self.logger = None  # 对话日志记录器
        self.quality_checker = None  # 质量检查器
        self.quality_reports = []  # 质检报告列表
        
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
    
    def _build_system_prompt(self, start_chapter: int) -> str:
        """构建系统提示词（使用优化后的v2.0版本）"""
        # 使用优化器构建精简的System Prompt
        if HAS_OPTIMIZER:
            try:
                optimizer = ChapterPromptOptimizer(self.novel_data)
                system_prompt = optimizer.build_system_prompt()
                logger.info(f"[章节对话 {self.session_id}] 使用优化的System Prompt v2.0（约1500字）")
                return system_prompt
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
        return chapters
    
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
        
        return {
            "chapter_number": chapter_num,
            "title": self._extract_title(content, chapter_plan),
            "content": content,
            "word_count": len(content),
            "quality_score": 8.0,  # 简化为固定分数，可后续评估
            "chapter_plan": chapter_plan,
            "generated_at": datetime.now().isoformat()
        }
    
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
    
    def _build_chapter_prompt(self, chapter_num: int, chapter_plan: Dict,
                             emotion_beat: Dict, prev_summary: str) -> str:
        """构建章节生成提示词（使用优化后的详细版本）"""
        # 使用优化器构建详细的章节提示词
        if HAS_OPTIMIZER:
            try:
                optimizer = ChapterPromptOptimizer(self.novel_data)
                return optimizer.build_chapter_prompt(chapter_num, chapter_plan, prev_summary)
            except Exception as e:
                logger.warning(f"[章节对话 {self.session_id}] 优化器失败，使用备用模式: {e}")
        
        # 使用简化版优化器（备用）
        optimizer = SimpleOptimizer(self.novel_data)
        return optimizer.build_chapter_prompt(chapter_num, chapter_plan, prev_summary)
    
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
