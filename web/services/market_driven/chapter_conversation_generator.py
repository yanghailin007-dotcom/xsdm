"""
对话模式章节生成器
在一个连续对话中批量生成多章，保持上下文连贯
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ChapterConversationGenerator:
    """
    章节对话生成器
    
    特点：
    1. 创建一个长对话会话
    2. 连续生成多章，每章都基于前文上下文
    3. 利用 Kimi 256K 上下文窗口，可连续生成 10-20 章
    """
    
    def __init__(self, api_client, novel_data: Dict, tropes: Dict):
        self.api_client = api_client
        self.novel_data = novel_data
        self.tropes = tropes
        self.session = None
        
        # 生成会话ID
        import uuid
        self.session_id = f"CCG-{uuid.uuid4().hex[:8].upper()}"
        
        # 提取小说基本信息
        self.novel_title = novel_data.get('title', '未命名')
        self.protagonist_name = self._get_protagonist_name()
        
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
            purpose_prefix=f"CCG-{self.session_id}"
        )
        # 设置历史限制
        session.max_history = 50  # 保留更多历史，支持多章连贯
        
        logger.info(f"[章节对话 {self.session_id}] 会话创建 | 小说: {self.novel_title} | 起始章: {start_chapter}")
        return session
    
    def _build_system_prompt(self, start_chapter: int) -> str:
        """构建系统提示词"""
        # 获取世界观
        worldview = self.novel_data.get('core_worldview', {})
        faction_system = self.novel_data.get('faction_system', {})
        
        # 获取角色设计
        char_design = self.novel_data.get('character_design', {})
        
        # 获取成长路线
        growth_plan = self.novel_data.get('global_growth_plan', {})
        
        # 获取情绪曲线
        emotion_curve = self.novel_data.get('emotion_curve', [])
        
        return f"""# 角色：顶级网络小说作家

你正在为小说《{self.novel_title}》连续生成章节。这是一个多轮对话过程，你将基于前文上下文连续生成多章内容。

## 小说基础设定

### 世界观
```json
{json.dumps(worldview, ensure_ascii=False, indent=2)}
```

### 势力系统
```json
{json.dumps(faction_system, ensure_ascii=False, indent=2)}
```

### 角色设计
```json
{json.dumps(char_design, ensure_ascii=False, indent=2)}
```

### 成长路线
```json
{json.dumps(growth_plan, ensure_ascii=False, indent=2)}
```

## 写作规范
1. **番茄风格**：快节奏、强爽点、章章有钩子
2. **每章2000-2500字**：不要过长或过短
3. **第一人称**：主角视角，强代入感
4. **短段落**：每段不超过3行，适合手机阅读
5. **多对话**：对话推动剧情，少用旁白
6. **情绪连贯**：每章情绪必须符合情绪曲线设计

## 重要规则
1. **必须记住前文**：后续章节必须基于前文情节发展
2. **保持人设一致**：主角性格、能力必须前后一致
3. **承上启下**：每章结尾必须留下钩子，与下一章衔接
4. **不跳剧情**：严格按照剧情路线推进，不要跳过大事件

## 当前任务
从第{start_chapter}章开始连续生成。等待第1章指令...
"""
    
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
        """在会话中生成单章"""
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
        
        # 在会话中发送消息
        logger.info(f"[章节对话 {self.session_id}] 发送第{chapter_num}章提示词 | 当前历史: {len(self.session.messages)}条")
        response = self.session.send_message(
            user_prompt=prompt,
            temperature=0.7,
            purpose=f"第{chapter_num}章"
        )
        logger.info(f"[章节对话 {self.session_id}] 接收第{chapter_num}章响应 | 总轮次: {self.session.turn_count}")
        
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
        """构建章节生成提示词"""
        parts = [
            f"请生成第{chapter_num}章。",
            "",
            "## 本章规划",
            f"- 章节标题: {chapter_plan.get('title', f'第{chapter_num}章')}",
            f"- 高潮类型: {chapter_plan.get('climax_type', '推进')}",
            f"- 必须要素: {', '.join(chapter_plan.get('required_elements', []))}",
            "",
            "## 情绪设计",
            f"- 情绪类型: {emotion_beat.get('emotion', '期待')}",
            f"- 强度: {emotion_beat.get('intensity', 6)}/10",
            f"- 目的: {emotion_beat.get('purpose', '剧情推进')}",
            ""
        ]
        
        if prev_summary:
            parts.extend([
                "## 前文摘要（必须承接）",
                prev_summary,
                ""
            ])
        
        parts.extend([
            "## 写作要求",
            "1. 字数2000-2500字",
            "2. 承接前文，不要重复前文已发生的事",
            "3. 本章必须有明确的爽点或钩子",
            "4. 章尾必须留下悬念，让读者想看下一章",
            "5. 严格遵循情绪设计，不要偏离",
            "",
            "直接输出章节正文，不要解释。"
        ])
        
        return "\n".join(parts)
    
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


# 便捷函数
def generate_chapters_with_conversation(api_client, novel_data: Dict, 
                                       blueprint: Dict, tropes: Dict,
                                       start_chapter: int, end_chapter: int,
                                       progress_callback=None) -> List[Dict]:
    """
    使用对话模式生成章节
    
    Returns:
        生成的章节列表
    """
    generator = ChapterConversationGenerator(api_client, novel_data, tropes)
    return generator.generate_chapters(
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        blueprint=blueprint,
        progress_callback=progress_callback
    )
