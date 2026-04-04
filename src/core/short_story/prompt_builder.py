"""
短篇 Prompt 构建器
加载并填充短篇专用的 prompt 模板
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional, Any


class ShortStoryPromptBuilder:
    """短篇 Prompt 构建器"""
    
    CONFIG_DIR = Path(__file__).parent.parent.parent / "config" / "short_story_prompts"
    
    def __init__(self):
        self.system_prompts = self._load_json("system_prompts.json")
        self.deconstruction_prompts = self._load_json("deconstruction_prompts.json")
        self.creative_prompts = self._load_json("creative_prompts.json")
        self.chapter_prompts = self._load_json("chapter_prompts.json")
    
    def _load_json(self, filename: str) -> Dict:
        """加载 JSON 配置文件"""
        filepath = self.CONFIG_DIR / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def get_system_prompt(self, genre: str) -> str:
        """获取指定题材的 system prompt"""
        default = self.system_prompts.get("default", {}).get("template", "")
        genre_specific = self.system_prompts.get("by_genre", {}).get(genre, {})
        genre_template = genre_specific.get("template", "")
        return default + "\n" + genre_template if genre_template else default
    
    def get_temperature(self) -> float:
        """获取默认 temperature"""
        return self.system_prompts.get("default", {}).get("temperature", 0.95)
    
    def get_max_history(self) -> int:
        """获取默认历史长度"""
        return self.system_prompts.get("default", {}).get("max_history", 50)
    
    def get_deconstruction_prompt(self, round_name: str, **kwargs) -> str:
        """获取仿写拆解 prompt"""
        template = self.deconstruction_prompts.get(round_name, {}).get("prompt", "")
        return self._fill_template(template, **kwargs)
    
    def get_creative_prompt(self, stage: str, **kwargs) -> str:
        """获取创意模式策划 prompt"""
        template = self.creative_prompts.get(stage, {}).get("prompt", "")
        return self._fill_template(template, **kwargs)
    
    def get_chapter_prompt(self, chapter_number: int, total_chapters: int, 
                          blueprint: Dict, prev_summary: str = "",
                          character_states: Optional[Dict] = None) -> str:
        """获取逐章生成 prompt"""
        is_first = chapter_number == 1
        if is_first:
            template = self.chapter_prompts.get("chapter_generation", {}).get("first_chapter_override", {}).get("template", "")
        else:
            template = self.chapter_prompts.get("chapter_generation", {}).get("template", "")
        
        if not template:
            template = self.chapter_prompts.get("chapter_generation", {}).get("template", "")
        
        key_events = "\n".join(f"- {e}" for e in blueprint.get("key_events", []))
        visual_scenes = "\n".join(f"- {s}" for s in blueprint.get("visual_scenes", []))
        char_states = character_states or {}
        char_states_str = "\n".join(f"- {k}: {v}" for k, v in char_states.items()) if char_states else "按人设设定"
        
        return self._fill_template(
            template,
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            chapter_purpose=blueprint.get("purpose", ""),
            word_count=blueprint.get("word_count", 2000),
            crisis_hook=blueprint.get("crisis_hook", ""),
            payoff_hook=blueprint.get("payoff_hook", ""),
            cliffhanger=blueprint.get("cliffhanger", ""),
            emotion_start=blueprint.get("emotion_start", ""),
            emotion_peak=blueprint.get("emotion_peak", ""),
            emotion_end=blueprint.get("emotion_end", ""),
            key_events=key_events or "按蓝图推进",
            character_states=char_states_str,
            prev_summary=prev_summary or "（本章为开篇）"
        )
    
    def get_title_synopsis_prompt(self, story_summary: str, core_payoff: str,
                                  character_tags: str) -> str:
        """获取书名简介生成 prompt"""
        template = self.chapter_prompts.get("title_synopsis_generation", {}).get("template", "")
        return self._fill_template(
            template,
            story_summary=story_summary,
            core_payoff=core_payoff,
            character_tags=character_tags
        )
    
    def _fill_template(self, template: str, **kwargs) -> str:
        """安全填充模板变量"""
        if not template:
            return ""
        result = template
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))
        return result
