"""
短篇生成主入口
统筹创意策划、仿写拆解、逐章生成、完本优化全流程
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, List

from src.core.APIClient import APIClient, ConversationSession
from .models import (
    ShortStoryConfig, ChapterBlueprint, ShortStoryResult,
    TropeTemplate, StoryMode
)
from .prompt_builder import ShortStoryPromptBuilder
from .deconstructor import ShortStoryDeconstructor
from .conversation_generator import ShortStoryConversationGenerator
from .quality_checker import ShortStoryQualityChecker

logger = logging.getLogger(__name__)


class ShortStoryGenerator:
    """短篇生成器"""
    
    def __init__(self, config: ShortStoryConfig):
        self.config = config
        self.api_client = config.api_client
        self.prompt_builder = ShortStoryPromptBuilder()
        self.deconstructor = ShortStoryDeconstructor(self.api_client)
        self.quality_checker = ShortStoryQualityChecker(self.api_client)
        self.result = ShortStoryResult()
        
        # 检查点路径（用户隔离）
        safe_title = self._sanitize_filename(config.title or "未命名短篇")
        if config.username:
            self.checkpoint_dir = Path(config.project_path or ".") / "小说项目" / config.username / safe_title / ".short_story"
            self.project_dir = Path(config.project_path or ".") / "小说项目" / config.username / safe_title
        else:
            self.checkpoint_dir = Path(config.project_path or ".") / "小说项目" / safe_title / ".short_story"
            self.project_dir = Path(config.project_path or ".") / "小说项目" / safe_title
        self.checkpoint_file = self.checkpoint_dir / "checkpoint.json"
        
        # 初始化统一 ConversationSession，全程使用拼接会话模式
        self.conversation_session = self._init_conversation_session()
        
        # 状态
        self.blueprint = None
        self.trope_template = None
        self.generated_chapters = {}
        self.prev_summary = ""
        self.character_states = {}
        self.api_calls_used = 0
    
    def _init_conversation_session(self) -> ConversationSession:
        """初始化统一的对话会话"""
        system_prompt = self.prompt_builder.get_system_prompt(self.config.genre.value)
        session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            provider=getattr(self.api_client, 'default_provider', None),
            purpose_prefix="ShortStory"
        )
        session.max_history = self.prompt_builder.get_max_history()
        logger.info("[ShortStoryGenerator] 初始化统一 ConversationSession")
        return session
    
    def _rebuild_conversation_session(self):
        """重建会话并注入已生成上下文摘要（控制 token 长度）"""
        system_prompt = self.prompt_builder.get_system_prompt(self.config.genre.value)
        
        # 注入上下文摘要
        context_parts = ["【短篇生成上下文】"]
        if self.blueprint:
            context_parts.append(f"书名候选: {self.blueprint.get('title_candidates', [])}")
            context_parts.append(f"故事简介: {self.blueprint.get('synopsis', '')}")
            context_parts.append(f"主角: {json.dumps(self.blueprint.get('protagonist', {}), ensure_ascii=False)}")
        if self.prev_summary:
            context_parts.append(f"前文摘要: {self.prev_summary}")
        if self.character_states:
            context_parts.append("人物状态:")
            for k, v in self.character_states.items():
                context_parts.append(f"  - {k}: {v}")
        
        if len(context_parts) > 1:
            system_prompt += "\n\n" + "\n".join(context_parts[1:])
        
        self.conversation_session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            provider=getattr(self.api_client, 'default_provider', None),
            purpose_prefix="ShortStory"
        )
        self.conversation_session.max_history = self.prompt_builder.get_max_history()
        logger.info("[ShortStoryGenerator] 重建 ConversationSession 并注入上下文摘要")
    
    def generate(self, progress_callback=None) -> ShortStoryResult:
        """
        短篇生成主入口
        """
        start_time = time.time()
        logger.info(f"[ShortStoryGenerator] 开始生成短篇 | 模式={self.config.mode.value} | 目标字数={self.config.target_word_count}")
        
        try:
            # 1. 尝试恢复检查点
            if self._load_checkpoint():
                logger.info("[ShortStoryGenerator] 已从检查点恢复")
            
            # 2. 生成/获取套路模板和蓝图
            if not self.blueprint:
                self._generate_blueprint()
                self._save_checkpoint()
            
            # 3. 生成正文
            if len(self.generated_chapters) < len(self.blueprint.get("chapters", [])):
                self._generate_chapters(progress_callback)
                self._save_checkpoint()
            
            # 4. 生成书名和简介
            if not self.result.title:
                self._generate_title_synopsis()
                self._save_checkpoint()
            
            # 5. 组装结果
            self.result.success = True
            self.result.chapters = self.generated_chapters
            self.result.total_word_count = sum(
                ch.get("word_count", 0) for ch in self.generated_chapters.values()
            )
            self.result.api_calls_used = self.api_calls_used
            
            # 6. 持久化最终产物到用户隔离目录
            self._save_final_result()
            
            elapsed = time.time() - start_time
            logger.info(f"[ShortStoryGenerator] 短篇生成完成 | 总字数={self.result.total_word_count} | 耗时={elapsed:.1f}s")
            
            return self.result
            
        except Exception as e:
            logger.error(f"[ShortStoryGenerator] 生成失败: {e}")
            import traceback
            traceback.print_exc()
            self.result.success = False
            self.result.error_message = str(e)
            return self.result
    
    def _generate_blueprint(self):
        """生成短篇蓝图"""
        if self.config.mode == StoryMode.IMITATE:
            # 仿写模式：拆解 → 模板 → 蓝图
            self.trope_template = self.deconstructor.deconstruct(
                self.config.reference_text,
                self.config.protagonist_replacement,
                self.config.era_replacement
            )
            self.blueprint = self._build_blueprint_from_template(self.trope_template)
        else:
            # 创意模式：直接调用 API 生成蓝图
            self.blueprint = self._create_blueprint_from_seed()
        
        logger.info(f"[ShortStoryGenerator] 蓝图生成完成 | 共 {len(self.blueprint.get('chapters', []))} 章")
    
    def _create_blueprint_from_seed(self) -> Dict:
        """创意模式：从种子生成蓝图"""
        # 使用 trope_template 的中间格式存储创意结果
        selected_variant = {
            "direction": self.config.creative_seed,
            "title_idea": "",
            "synopsis": self.config.creative_seed,
            "opening": self.config.creative_seed,
            "payoff_scenes": [],
            "ending_type": self.config.ending_type
        }
        
        prompt = self.prompt_builder.get_creative_prompt(
            "blueprint",
            selected_variant=json.dumps(selected_variant, ensure_ascii=False),
            target_word_count=self.config.target_word_count,
            chapter_count=self.config.chapter_count,
            words_per_chapter=self.config.target_word_count // self.config.chapter_count,
            ending_type=self.config.ending_type
        )
        
        response = self._call_api(prompt, "短篇蓝图生成")
        data = self._parse_json(response)
        
        # 如果返回的数据结构不完整，进行补全
        if "chapters" not in data:
            data["chapters"] = self._generate_default_chapters()
        
        return data
    
    def _build_blueprint_from_template(self, template: TropeTemplate) -> Dict:
        """从套路模板构建蓝图"""
        prompt = f"""请基于以下套路模板，生成详细的短篇创作蓝图。\n\n套路模板：\n{json.dumps(template.__dict__, ensure_ascii=False, indent=2)}\n\n目标规格：\n- 总字数：{self.config.target_word_count} 字\n- 章节数：{self.config.chapter_count} 章\n- 结局偏好：{self.config.ending_type}\n\n请按以下 JSON 格式返回：\n{{\n  \"title_candidates\": [\"书名候选1\", \"书名候选2\", \"书名候选3\"],\n  \"synopsis\": \"300字内简介\",\n  \"protagonist\": {{\"name\":\"\", \"identity\":\"\", \"core_trait\":\"\", \"goal\":\"\"}},\n  \"antagonist\": {{\"name\":\"\", \"identity\":\"\", \"core_trait\":\"\"}},\n  \"chapters\": [\n    {{\n      \"chapter_number\": 1,\n      \"purpose\": \"\",\n      \"word_count\": 2000,\n      \"crisis_hook\": \"\",\n      \"payoff_hook\": \"\",\n      \"cliffhanger\": \"\",\n      \"emotion_start\": \"\",\n      \"emotion_peak\": \"\",\n      \"emotion_end\": \"\",\n      \"key_events\": [],\n      \"visual_scenes\": []\n    }}\n  ],\n  \"famous_scenes\": []\n}}\n\n只输出 JSON。"""
        
        response = self._call_api(prompt, "仿写蓝图生成")
        data = self._parse_json(response)
        
        if "chapters" not in data:
            data["chapters"] = self._generate_default_chapters()
        
        return data
    
    def _generate_default_chapters(self) -> List[Dict]:
        """生成默认章节结构（备用）"""
        chapters = []
        words_per_chapter = self.config.target_word_count // self.config.chapter_count
        for i in range(1, self.config.chapter_count + 1):
            chapters.append({
                "chapter_number": i,
                "purpose": "推进剧情" if i > 1 else "死亡开局",
                "word_count": words_per_chapter,
                "crisis_hook": "突发危机",
                "payoff_hook": "" if i == 1 else "情绪爽点",
                "cliffhanger": "悬念待解",
                "emotion_start": "紧张",
                "emotion_peak": "愤怒",
                "emotion_end": "期待",
                "key_events": ["情节推进"],
                "visual_scenes": []
            })
        return chapters
    
    def _generate_chapters(self, progress_callback=None):
        """逐章生成正文"""
        chapters = self.blueprint.get("chapters", [])
        total = len(chapters)
        genre = self.config.genre.value
        
        # 每 6 章重建一次 session，防止 token 过长，但始终使用拼接会话模式
        conv_gen = ShortStoryConversationGenerator(self.api_client, genre, session=self.conversation_session)
        
        for bp in chapters:
            ch_num = bp.get("chapter_number", 1)
            
            # 跳过已生成的章节
            if str(ch_num) in self.generated_chapters or ch_num in self.generated_chapters:
                continue
            
            if progress_callback:
                progress_callback(ch_num, total, "generating")
            
            # 检查是否需要重建 session（每 6 章）
            if ch_num > 1 and (ch_num - 1) % 6 == 0:
                self._rebuild_conversation_session()
                conv_gen = ShortStoryConversationGenerator(self.api_client, genre, session=self.conversation_session)
            
            # 最多重试 2 次
            chapter_data = None
            for attempt in range(3):
                try:
                    chapter_data = conv_gen.generate_chapter(
                        chapter_number=ch_num,
                        total_chapters=total,
                        blueprint=bp,
                        prev_summary=self.prev_summary,
                        character_states=self.character_states
                    )
                    
                    # 质检
                    report = self.quality_checker.check_chapter(chapter_data, bp)
                    if report["passed"]:
                        break
                    
                    logger.warning(f"[ShortStoryGenerator] 第 {ch_num} 章质检未通过（尝试 {attempt+1}/3），问题：{report['issues']}")
                    
                    # 如果最后一次也失败，仍然使用但标记问题
                    if attempt == 2:
                        chapter_data["quality_issues"] = report["issues"]
                        
                except Exception as e:
                    logger.error(f"[ShortStoryGenerator] 第 {ch_num} 章生成异常（尝试 {attempt+1}/3）: {e}")
                    if attempt == 2:
                        raise
            
            self.generated_chapters[ch_num] = chapter_data
            self.prev_summary = chapter_data.get("summary", "")
            
            # 更新人物状态（简单提取，后续可细化）
            self.character_states[f"第{ch_num}章后"] = "剧情推进中"
            
            if progress_callback:
                progress_callback(ch_num, total, "completed")
            
            logger.info(f"[ShortStoryGenerator] 第 {ch_num} 章完成 | 字数={chapter_data.get('word_count', 0)}")
        
        # 统计 API 调用次数（从主 session 读取 turn_count）
        if self.conversation_session:
            self.api_calls_used += self.conversation_session.get_stats().get("turn_count", 0)
    
    def _generate_title_synopsis(self):
        """生成书名和简介"""
        # 构建故事梗概
        summaries = []
        for ch_num in sorted(self.generated_chapters.keys()):
            ch = self.generated_chapters[ch_num]
            summaries.append(ch.get("summary", ""))
        story_summary = "\n".join(summaries[:3])  # 取前3章摘要
        
        # 核心爽点
        core_payoff = "主角逆袭，打脸反派"
        if self.blueprint and "famous_scenes" in self.blueprint:
            famous = self.blueprint.get("famous_scenes", [])
            if famous:
                core_payoff = famous[0].get("scene_name", core_payoff)
        
        # 人设标签
        character_tags = ""
        if self.blueprint and "protagonist" in self.blueprint:
            pro = self.blueprint.get("protagonist", {})
            character_tags = f"{pro.get('identity', '')} {pro.get('core_trait', '')}"
        
        prompt = self.prompt_builder.get_title_synopsis_prompt(
            story_summary=story_summary,
            core_payoff=core_payoff,
            character_tags=character_tags
        )
        
        response = self._call_api(prompt, "书名简介生成")
        
        # 解析书名和简介
        title = self._extract_section(response, "书名")
        synopsis = self._extract_section(response, "简介")
        
        # 如果解析失败，取前3行
        if not title:
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            title = lines[0] if lines else "未命名短篇"
        if not synopsis:
            synopsis = response[:300]
        
        # 从书名候选中提取第一个
        title_candidates = [l.strip('- ') for l in title.split('\n') if l.strip()]
        final_title = title_candidates[0] if title_candidates else title.split('\n')[0]
        
        self.result.title = final_title
        self.result.synopsis = synopsis
        
        logger.info(f"[ShortStoryGenerator] 书名生成: {final_title}")
    
    def _call_api(self, prompt: str, purpose: str) -> str:
        """调用 API 并统计次数 —— 统一使用 ConversationSession 拼接会话模式"""
        if not self.conversation_session:
            self.conversation_session = self._init_conversation_session()
        
        result = self.conversation_session.send_message(prompt, purpose=purpose)
        self.api_calls_used += 1
        return result or ""
    
    def _parse_json(self, text: str) -> Dict:
        """解析 JSON"""
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        import re
        for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        
        return {"raw_text": text}
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """提取章节内容"""
        pattern = rf'---{section_name}---\s*(.*?)\s*(?=---|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _save_final_result(self):
        """保存最终产物到用户隔离的项目目录"""
        try:
            os.makedirs(self.project_dir, exist_ok=True)
            
            # 1. 保存完整结果 JSON
            result_path = self.project_dir / "short_story_result.json"
            result_data = {
                "novel_title": self.result.title or self.config.title,
                "synopsis": self.result.synopsis,
                "genre": self.config.genre.value,
                "mode": self.config.mode.value,
                "target_word_count": self.config.target_word_count,
                "total_word_count": self.result.total_word_count,
                "chapter_count": len(self.generated_chapters),
                "api_calls_used": self.api_calls_used,
                "username": self.config.username,
                "created_at": time.time(),
                "chapters": self.generated_chapters,
                "blueprint": self.blueprint,
            }
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            # 2. 保存 overview.json（供"我的作品"页面快速扫描）
            overview_path = self.project_dir / "overview.json"
            overview_data = {
                "novel_title": self.result.title or self.config.title,
                "synopsis": self.result.synopsis,
                "category": self.config.genre.value,
                "current_progress": {
                    "completed_chapters": len(self.generated_chapters),
                    "total_chapters": self.config.chapter_count,
                    "stage": "已完成",
                    "current_stage": "短篇完成"
                },
                "total_word_count": self.result.total_word_count,
                "username": self.config.username,
                "created_at": time.time(),
                "is_short_story": True,
            }
            with open(overview_path, 'w', encoding='utf-8') as f:
                json.dump(overview_data, f, ensure_ascii=False, indent=2)
            
            # 3. 保存分章 TXT 到 chapters 目录
            chapters_dir = self.project_dir / "chapters"
            os.makedirs(chapters_dir, exist_ok=True)
            for ch_num, ch_data in sorted(self.generated_chapters.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else x[0]):
                safe_num = str(ch_num).zfill(2)
                chapter_file = chapters_dir / f"chapter_{safe_num}.txt"
                title = ch_data.get("title", f"第{ch_num}章")
                content = ch_data.get("content", "")
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    f.write(f"{title}\n\n{content}")
            
            logger.info(f"[ShortStoryGenerator] 最终产物已保存到: {self.project_dir}")
        except Exception as e:
            logger.warning(f"[ShortStoryGenerator] 保存最终产物失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_checkpoint(self):
        """保存检查点"""
        try:
            os.makedirs(self.checkpoint_dir, exist_ok=True)
            data = {
                "config": {
                    "mode": self.config.mode.value,
                    "title": self.config.title,
                    "genre": self.config.genre.value,
                    "target_word_count": self.config.target_word_count,
                    "chapter_count": self.config.chapter_count,
                    "ending_type": self.config.ending_type,
                },
                "blueprint": self.blueprint,
                "generated_chapters": self.generated_chapters,
                "prev_summary": self.prev_summary,
                "character_states": self.character_states,
                "result_title": self.result.title,
                "result_synopsis": self.result.synopsis,
                "api_calls_used": self.api_calls_used,
                "timestamp": time.time()
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[ShortStoryGenerator] 检查点已保存: {self.checkpoint_file}")
        except Exception as e:
            logger.warning(f"[ShortStoryGenerator] 保存检查点失败: {e}")
    
    def _load_checkpoint(self) -> bool:
        """加载检查点"""
        if not self.checkpoint_file.exists():
            return False
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.blueprint = data.get("blueprint")
            self.generated_chapters = data.get("generated_chapters", {})
            # 兼容 str/int key
            self.generated_chapters = {
                int(k) if k.isdigit() else k: v 
                for k, v in self.generated_chapters.items()
            }
            self.prev_summary = data.get("prev_summary", "")
            self.character_states = data.get("character_states", {})
            self.result.title = data.get("result_title", "")
            self.result.synopsis = data.get("result_synopsis", "")
            self.api_calls_used = data.get("api_calls_used", 0)
            
            logger.info(f"[ShortStoryGenerator] 检查点已加载 | 已生成 {len(self.generated_chapters)} 章")
            return True
        except Exception as e:
            logger.warning(f"[ShortStoryGenerator] 加载检查点失败: {e}")
            return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        import re
        return re.sub(r'[\\/:*?"<>|]', '_', filename)
    
    def get_progress(self) -> Dict:
        """获取当前进度"""
        total_chapters = self.config.chapter_count
        generated = len(self.generated_chapters)
        percentage = int((generated / total_chapters) * 100) if total_chapters > 0 else 0
        
        return {
            "total_chapters": total_chapters,
            "generated_chapters": generated,
            "percentage": percentage,
            "title": self.result.title,
            "current_word_count": sum(
                ch.get("word_count", 0) for ch in self.generated_chapters.values()
            )
        }
