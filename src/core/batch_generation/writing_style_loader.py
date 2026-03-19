# -*- coding: utf-8 -*-
"""
写作风格指南加载器
从JSON文件加载风格指南并格式化为Prompt可用格式
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FormattedStyleGuide:
    """格式化后的风格指南，可直接用于Prompt"""
    core_style: str
    key_principles: str
    language_characteristics: str
    narration_techniques: str
    chapter_techniques: str
    dialogue_style: str
    interaction_design: str


class WritingStyleGuideLoader:
    """
    写作风格指南加载器
    支持从文件加载并格式化为Prompt片段
    """
    
    # 单例缓存
    _cache: Dict[str, FormattedStyleGuide] = {}
    
    @classmethod
    def load_and_format(
        cls, 
        novel_title: str, 
        username: str = None,
        use_cache: bool = True
    ) -> FormattedStyleGuide:
        """
        加载并格式化风格指南
        
        Args:
            novel_title: 小说标题
            username: 用户名（用于用户隔离）
            use_cache: 是否使用缓存
            
        Returns:
            FormattedStyleGuide: 格式化后的风格指南
        """
        cache_key = f"{username}:{novel_title}" if username else novel_title
        
        # 检查缓存
        if use_cache and cache_key in cls._cache:
            logger.info(f"[WritingStyleGuideLoader] 使用缓存的风格指南: {novel_title}")
            return cls._cache[cache_key]
        
        # 从文件加载
        style_guide = cls._load_from_file(novel_title, username)
        
        if not style_guide:
            logger.warning(f"[WritingStyleGuideLoader] 未找到风格指南，使用番茄默认风格: {novel_title}")
            style_guide = cls._get_fanqie_default_style()
        
        # 格式化为Prompt片段
        formatted = cls._format_to_prompt(style_guide)
        
        # 🔥 调试：检查 formatted 类型
        if not isinstance(formatted, FormattedStyleGuide):
            logger.error(f"[DEBUG] formatted 类型错误: {type(formatted)}, 值: {formatted}")
            # 如果缓存中有错误的数据，清除缓存
            if cache_key in cls._cache:
                logger.error(f"[DEBUG] 清除缓存中错误的数据: {cache_key}")
                del cls._cache[cache_key]
        
        # 缓存
        if use_cache:
            cls._cache[cache_key] = formatted
        
        return formatted
    
    @classmethod
    def clear_cache(cls, novel_title: str = None, username: str = None):
        """清除缓存"""
        if novel_title:
            cache_key = f"{username}:{novel_title}" if username else novel_title
            cls._cache.pop(cache_key, None)
        else:
            cls._cache.clear()
    
    @classmethod
    def _load_from_file(cls, novel_title: str, username: str = None) -> Optional[Dict]:
        """从JSON文件加载风格指南"""
        try:
            from src.utils.path_manager import path_manager
            
            style_data = path_manager.load_writing_style_guide(novel_title, username)
            
            if style_data:
                # 有些版本包装在writing_style_guide键内
                if "writing_style_guide" in style_data:
                    return style_data["writing_style_guide"]
                return style_data
                
        except Exception as e:
            logger.warning(f"[WritingStyleGuideLoader] 加载风格指南失败: {e}")
        
        return None
    
    @classmethod
    def _format_to_prompt(cls, style_guide: Dict) -> FormattedStyleGuide:
        """将风格指南格式化为Prompt片段"""
        return FormattedStyleGuide(
            core_style=cls._format_core_style(style_guide.get("core_style", "")),
            key_principles=cls._format_key_principles(style_guide.get("key_principles", [])),
            language_characteristics=cls._format_language_characteristics(
                style_guide.get("language_characteristics", {})
            ),
            narration_techniques=cls._format_narration_techniques(
                style_guide.get("narration_techniques", {})
            ),
            chapter_techniques=cls._format_chapter_techniques(
                style_guide.get("chapter_techniques", {})
            ),
            dialogue_style=cls._format_dialogue_style(
                style_guide.get("dialogue_style", {})
            ),
            interaction_design=cls._format_interaction_design(
                style_guide.get("interaction_design", {})
            ),
        )
    
    @classmethod
    def _format_core_style(cls, core_style: str) -> str:
        """格式化核心风格"""
        if not core_style:
            core_style = "专业番茄网络小说作家，擅长快节奏、强情绪、高爽点的移动端阅读内容"
        return core_style
    
    @classmethod
    def _format_key_principles(cls, principles: List[str]) -> str:
        """格式化关键原则"""
        if not principles:
            principles = [
                "爽点前置，快速进入核心冲突",
                "情绪外显，通过动作对话体现心理",
                "段落短小，适合手机阅读",
                "章章卡点，引导连续阅读",
                "减少铺垫，加快叙事节奏"
            ]
        
        lines = ["## 核心写作原则", ""]
        for i, principle in enumerate(principles, 1):
            lines.append(f"{i}. {principle}")
        lines.append("")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_language_characteristics(cls, chars) -> str:
        """格式化语言特点（番茄向）"""
        # 类型检查
        if isinstance(chars, str):
            return f"### 语言特点\n\n{chars}\n"
        
        if not chars:
            chars = {}
        
        lines = ["### 语言特点", ""]
        
        # 句式结构
        sentence = chars.get("sentence_structure", "短句为主，段落精悍，每段不超过手机4行显示")
        lines.append(f"**句式结构**: {sentence}")
        
        # 词汇风格
        vocab = chars.get("vocabulary_style", "口语化表达，避免过于文雅的书面语")
        lines.append(f"**词汇风格**: {vocab}")
        
        # 节奏控制
        rhythm = chars.get("rhythm_control", "快节奏推进，紧张场景加快，过渡场景精简")
        lines.append(f"**节奏控制**: {rhythm}")
        
        lines.append("")
        
        # 番茄平台必遵规则
        lines.extend([
            "### 番茄风格必遵规则",
            "- **短段落**: 手机显示每段不超过4行",
            "- **快节奏**: 3章内必须有小爽点，快速推进",
            "- **强情绪**: 情绪外显，通过动作、对话、表情体现",
            "- **爽点前置**: 每章前300字必须有吸引力",
            "- **口语化**: 避免文绉绉的书面语和AI痕迹词汇",
            ""
        ])
        
        return "\n".join(lines)
    
    @classmethod
    def _format_narration_techniques(cls, techniques) -> str:
        """格式化叙事技巧"""
        # 类型检查
        if isinstance(techniques, str):
            return f"### 叙事技巧\n\n{techniques}\n"
        
        if not techniques:
            techniques = {
                "perspective": "第三人称有限视角，紧贴主角心理",
                "description": "环境描写服务于情绪，人物描写突出特征",
                "transition": "直接切换，减少过渡句"
            }
        
        lines = ["### 叙事技巧", ""]
        
        perspective = techniques.get("perspective", "第三人称有限视角")
        lines.append(f"**视角**: {perspective}")
        
        description = techniques.get("description", "")
        if description:
            lines.append(f"**描写方法**: {description}")
        
        transition = techniques.get("transition", "")
        if transition:
            lines.append(f"**过渡技巧**: {transition}")
        
        lines.append("")
        return "\n".join(lines)
    
    @classmethod
    def _format_chapter_techniques(cls, techniques) -> str:
        """格式化章节技巧（卡点重点）"""
        # 类型检查
        if isinstance(techniques, str):
            return f"### 章节技巧\n\n{techniques}\n"
        
        if not techniques:
            techniques = {}
        
        lines = ["### 章节技巧", ""]
        
        # 开篇
        opening = techniques.get("opening", "快速进入情境，15秒内抓住注意力")
        lines.append(f"**开篇**: {opening}")
        
        # 发展
        development = techniques.get("development", "保持推进速度，穿插节奏调剂")
        lines.append(f"**发展**: {development}")
        
        # 结尾（卡点最重要）
        ending = techniques.get("ending", "强力卡点，引导点击下一章")
        lines.append(f"**结尾（卡点）**: {ending}")
        
        lines.extend([
            "",
            "**卡点类型**:",
            "1. **悬念型**: 留下未解之谜，如'他到底是谁？'",
            "2. **情绪型**: 强烈情绪未释放，如'怒火在胸中燃烧'",
            "3. **冲突型**: 冲突即将爆发，如'下一刻，两人同时动了'",
            "4. **期待型**: 读者期待的事情即将发生，如'门开了'",
            ""
        ])
        
        return "\n".join(lines)
    
    @classmethod
    def _format_dialogue_style(cls, style) -> str:
        """格式化对话风格"""
        if not style:
            return ""
        
        # 类型检查：如果 style 是字符串，返回默认值
        if isinstance(style, str):
            return "### 对话风格\n\n对话要符合角色身份，避免千人一面\n"
        
        lines = ["### 对话风格", ""]
        
        protagonist = style.get("protagonist", "")
        if protagonist:
            lines.append(f"**主角**: {protagonist}")
        
        supporting = style.get("supporting_chars", "")
        if supporting:
            lines.append(f"**配角**: {supporting}")
        
        antagonists = style.get("antagonists", "")
        if antagonists:
            lines.append(f"**反派**: {antagonists}")
        
        lines.extend([
            "",
            "**对话规范**:",
            "- 每句对话独立成段",
            "- 对话要体现角色性格，避免千人一面",
            "- 避免长篇说教式对话",
            "- 使用口语化表达，符合角色身份",
            ""
        ])
        
        return "\n".join(lines)
    
    @classmethod
    def _format_interaction_design(cls, design) -> str:
        """格式化互动设计"""
        if not design:
            return ""
        
        # 类型检查
        if isinstance(design, str):
            return f"### 互动设计\n\n{design}\n"
        
        lines = ["### 读者互动设计", ""]
        
        triggers = design.get("comment_triggers", "")
        if triggers:
            lines.append(f"**评论引导**: {triggers}")
        
        meme = design.get("meme_embedding", "")
        if meme:
            lines.append(f"**名场面设计**: {meme}")
        
        lines.append("")
        return "\n".join(lines)
    
    @classmethod
    def _get_fanqie_default_style(cls) -> Dict:
        """番茄小说默认风格"""
        return {
            "core_style": "专业番茄网络小说作家，擅长快节奏、强情绪、高爽点的移动端阅读内容",
            "language_characteristics": {
                "sentence_structure": "短句为主，段落精悍，每段不超过手机4行显示，关键信息独立成段",
                "vocabulary_style": "口语化表达，避免'首先、其次、总而言之'等AI痕迹词汇",
                "rhythm_control": "快节奏推进，3章内必须有小爽点，紧张场景加快，过渡场景精简"
            },
            "narration_techniques": {
                "perspective": "第三人称有限视角，紧贴主角心理活动，强化代入感",
                "description": "环境描写服务于情绪，人物描写突出特征，战斗描写强调动作和结果",
                "transition": "直接切换，减少过渡句，保持阅读流畅性"
            },
            "dialogue_style": {
                "protagonist": "符合身份的语言风格，有辨识度",
                "supporting_chars": "不同角色有不同语言特点，避免千人一面",
                "antagonists": "拉仇恨但不脸谱化，语言体现动机"
            },
            "chapter_techniques": {
                "opening": "快速进入状态，15秒内通过冲突/悬念/情绪抓住读者",
                "development": "保持推进速度，穿插节奏调剂，每3章一个小高潮",
                "ending": "强力卡点，悬念/情绪/冲突/期待四种类型，引导点击下一章"
            },
            "interaction_design": {
                "comment_triggers": "战力对比、角色选择、剧情预测等可引发讨论的点",
                "meme_embedding": "设计可供传播的金句和名场面"
            },
            "key_principles": [
                "爽点前置，快速进入核心冲突",
                "情绪外显，通过动作对话体现心理",
                "段落短小，适合手机阅读",
                "章章卡点，引导连续阅读",
                "减少铺垫，加快叙事节奏",
                "消除AI痕迹，语言自然口语化"
            ]
        }


# 便捷函数
def get_writing_style_for_prompt(
    novel_title: str, 
    username: str = None
) -> FormattedStyleGuide:
    """
    获取用于Prompt的写作风格指南
    
    使用示例:
    style = get_writing_style_for_prompt("凡人修仙传", "user1")
    prompt = f"""
    # 角色: {style.core_style}
    {style.key_principles}
    {style.language_characteristics}
    ...
    """
    """
    return WritingStyleGuideLoader.load_and_format(novel_title, username)
