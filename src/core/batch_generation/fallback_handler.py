# -*- coding: utf-8 -*-
"""
批量生成错误回退策略
当批量生成失败时，自动降级到逐章生成
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """失败类型"""
    SCENE_GENERATION_FAILED = "scene_generation_failed"
    CONTENT_GENERATION_FAILED = "content_generation_failed"
    CONTENT_TRUNCATED = "content_truncated"
    QUALITY_UNACCEPTABLE = "quality_unacceptable"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class FallbackResult:
    """回退结果"""
    success: bool
    chapters_content: Optional[Dict[int, Dict]] = None
    scenes_by_chapter: Optional[Dict[int, List[Dict]]] = None
    fallback_level: str = ""  # 使用的回退层级
    api_calls_extra: int = 0   # 额外API调用次数
    warnings: List[str] = None
    error: str = ""
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class BatchFallbackHandler:
    """
    批量生成失败回退处理器
    
    提供多级回退策略：
    1. 重试（指数退避）
    2. 拆分为更小批次
    3. 逐章生成（最终保障）
    """
    
    def __init__(self, scene_generator, content_generator):
        self.scene_generator = scene_generator
        self.content_generator = content_generator
        self.logger = logging.getLogger(__name__)
        
        # 配置
        self.max_retries = 3
        self.retry_delay_base = 2  # 秒
    
    async def handle_failure(
        self,
        failure_type: FailureType,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        scenes_by_chapter: Optional[Dict[int, List[Dict]]] = None,
        consistency_guidance: str = "",
        novel_title: str = "",
        error_info: str = "",
        retry_count: int = 0
    ) -> FallbackResult:
        """
        处理批量生成失败
        
        Args:
            failure_type: 失败类型
            medium_event: 中型事件数据
            chapter_range: (start, end) 章节范围
            scenes_by_chapter: 已生成的场景（如果有）
            consistency_guidance: 一致性指导
            novel_title: 小说标题
            error_info: 错误信息
            retry_count: 当前重试次数
            
        Returns:
            FallbackResult: 回退结果
        """
        start_ch, end_ch = chapter_range
        span = end_ch - start_ch + 1
        
        self.logger.warning(
            f"[FallbackHandler] 批量生成失败[{failure_type.value}] "
            f"第{start_ch}-{end_ch}章，重试次数:{retry_count}"
        )
        
        # 策略选择
        if failure_type in [FailureType.API_ERROR, FailureType.TIMEOUT]:
            if retry_count < self.max_retries:
                return await self._retry_with_backoff(
                    medium_event, chapter_range, scenes_by_chapter,
                    consistency_guidance, novel_title, retry_count
                )
        
        elif failure_type == FailureType.CONTENT_TRUNCATED:
            # Token超长，拆分为更小的批次
            if span > 1:
                return await self._split_to_smaller_batches(
                    medium_event, chapter_range, scenes_by_chapter,
                    consistency_guidance, novel_title
                )
        
        elif failure_type == FailureType.QUALITY_UNACCEPTABLE:
            # 质量不合格，尝试逐章生成以获得更好质量
            return await self._fallback_to_chapter_by_chapter(
                medium_event, chapter_range, scenes_by_chapter,
                consistency_guidance, novel_title, quality_focus=True
            )
        
        # 默认回退：逐章生成
        return await self._fallback_to_chapter_by_chapter(
            medium_event, chapter_range, scenes_by_chapter,
            consistency_guidance, novel_title
        )
    
    async def _retry_with_backoff(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        scenes_by_chapter: Optional[Dict[int, List[Dict]]],
        consistency_guidance: str,
        novel_title: str,
        retry_count: int
    ) -> FallbackResult:
        """指数退避重试"""
        delay = self.retry_delay_base ** retry_count
        self.logger.info(f"[FallbackHandler] 指数退避重试，等待{delay}秒...")
        
        await asyncio.sleep(delay)
        
        try:
            # 尝试重新调用批量生成
            from .multi_chapter_generator import MultiChapterContentGenerator
            
            generator = MultiChapterContentGenerator(
                self.content_generator.api_client
            )
            
            result = generator.generate(
                medium_event=medium_event,
                chapter_range=chapter_range,
                scenes_by_chapter=scenes_by_chapter or {},
                consistency_guidance=consistency_guidance,
                novel_title=novel_title
            )
            
            # 转换为标准格式
            chapters_data = {}
            for ch_num, content in result.items():
                chapters_data[ch_num] = {
                    "chapter_number": ch_num,
                    "title": content.title,
                    "content": content.content,
                    "key_events": content.key_events,
                    "character_states": content.character_states,
                    "items_delta": content.items_delta,
                    "time_progression": content.time_progression
                }
            
            return FallbackResult(
                success=True,
                chapters_content=chapters_data,
                fallback_level=f"retry_{retry_count + 1}",
                api_calls_extra=retry_count + 1
            )
            
        except Exception as e:
            self.logger.error(f"[FallbackHandler] 重试失败: {e}")
            # 递归回退
            return await self._fallback_to_chapter_by_chapter(
                medium_event, chapter_range, scenes_by_chapter,
                consistency_guidance, novel_title
            )
    
    async def _split_to_smaller_batches(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        scenes_by_chapter: Optional[Dict[int, List[Dict]]],
        consistency_guidance: str,
        novel_title: str
    ) -> FallbackResult:
        """拆分为更小的批次生成"""
        start_ch, end_ch = chapter_range
        span = end_ch - start_ch + 1
        
        self.logger.info(f"[FallbackHandler] 拆分为小批次: {span}章 → 2批")
        
        # 计算分割点
        mid = start_ch + (span // 2)
        
        all_content = {}
        extra_calls = 0
        
        # 第一批
        batch1_scenes = {
            k: v for k, v in (scenes_by_chapter or {}).items()
            if start_ch <= k <= mid
        }
        
        try:
            from .multi_chapter_generator import MultiChapterContentGenerator
            generator = MultiChapterContentGenerator(
                self.content_generator.api_client
            )
            
            result1 = generator.generate(
                medium_event=medium_event,
                chapter_range=(start_ch, mid),
                scenes_by_chapter=batch1_scenes,
                consistency_guidance=consistency_guidance,
                novel_title=novel_title
            )
            
            for ch_num, content in result1.items():
                all_content[ch_num] = {
                    "chapter_number": ch_num,
                    "title": content.title,
                    "content": content.content,
                    "key_events": content.key_events,
                    "character_states": content.character_states,
                    "items_delta": content.items_delta,
                    "time_progression": content.time_progression
                }
            
            extra_calls += 1
            
        except Exception as e:
            self.logger.error(f"[FallbackHandler] 第一批生成失败: {e}")
            # 第一批失败，逐章生成
            batch1_content = await self._generate_chapter_by_chapter(
                medium_event, (start_ch, mid), batch1_scenes,
                consistency_guidance, novel_title
            )
            all_content.update(batch1_content)
            extra_calls += (mid - start_ch + 1)
        
        # 第二批
        if mid < end_ch:
            batch2_scenes = {
                k: v for k, v in (scenes_by_chapter or {}).items()
                if mid + 1 <= k <= end_ch
            }
            
            try:
                result2 = generator.generate(
                    medium_event=medium_event,
                    chapter_range=(mid + 1, end_ch),
                    scenes_by_chapter=batch2_scenes,
                    consistency_guidance=consistency_guidance,
                    novel_title=novel_title
                )
                
                for ch_num, content in result2.items():
                    all_content[ch_num] = {
                        "chapter_number": ch_num,
                        "title": content.title,
                        "content": content.content,
                        "key_events": content.key_events,
                        "character_states": content.character_states,
                        "items_delta": content.items_delta,
                        "time_progression": content.time_progression
                    }
                
                extra_calls += 1
                
            except Exception as e:
                self.logger.error(f"[FallbackHandler] 第二批生成失败: {e}")
                batch2_content = await self._generate_chapter_by_chapter(
                    medium_event, (mid + 1, end_ch), batch2_scenes,
                    consistency_guidance, novel_title
                )
                all_content.update(batch2_content)
                extra_calls += (end_ch - mid)
        
        return FallbackResult(
            success=True,
            chapters_content=all_content,
            fallback_level="split_batches",
            api_calls_extra=extra_calls,
            warnings=["内容已拆分为多批生成"]
        )
    
    async def _fallback_to_chapter_by_chapter(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        scenes_by_chapter: Optional[Dict[int, List[Dict]]],
        consistency_guidance: str,
        novel_title: str,
        quality_focus: bool = False
    ) -> FallbackResult:
        """
        回退到逐章生成（最终保障）
        
        Args:
            quality_focus: 是否重点关注质量（会额外调用优化）
        """
        start_ch, end_ch = chapter_range
        
        self.logger.info(
            f"[FallbackHandler] 回退到逐章生成: 第{start_ch}-{end_ch}章, "
            f"quality_focus={quality_focus}"
        )
        
        all_content = {}
        current_guidance = consistency_guidance
        
        for ch_num in range(start_ch, end_ch + 1):
            try:
                # 获取场景
                scenes = None
                if scenes_by_chapter and ch_num in scenes_by_chapter:
                    scenes = scenes_by_chapter[ch_num]
                
                if not scenes:
                    # 场景缺失，生成默认场景
                    self.logger.warning(f"[FallbackHandler] 第{ch_num}章场景缺失，使用默认")
                    scenes = self._create_default_scenes(medium_event, ch_num)
                
                # 逐章生成内容
                chapter_content = self.content_generator.generate_chapter_content(
                    chapter_params={
                        "chapter_number": ch_num,
                        "pre_designed_scenes": scenes,
                        "consistency_guidance": current_guidance,
                        "novel_title": novel_title,
                        "medium_event": medium_event
                    }
                )
                
                if chapter_content:
                    all_content[ch_num] = chapter_content
                    
                    # 更新一致性指导（包含新生成的内容）
                    current_guidance = self._update_guidance(
                        current_guidance, chapter_content
                    )
                else:
                    self.logger.error(f"[FallbackHandler] 第{ch_num}章生成返回空")
                    
            except Exception as e:
                self.logger.error(f"[FallbackHandler] 第{ch_num}章生成失败: {e}")
                # 继续生成下一章
        
        if not all_content:
            return FallbackResult(
                success=False,
                error="逐章生成完全失败",
                fallback_level="chapter_by_chapter_failed"
            )
        
        warnings = ["已回退到逐章生成模式"]
        if quality_focus:
            warnings.append("质量优先模式已启用")
        
        return FallbackResult(
            success=True,
            chapters_content=all_content,
            fallback_level="chapter_by_chapter",
            api_calls_extra=(end_ch - start_ch + 1),
            warnings=warnings
        )
    
    async def _generate_chapter_by_chapter(
        self,
        medium_event: Dict,
        chapter_range: Tuple[int, int],
        scenes_by_chapter: Optional[Dict[int, List[Dict]]],
        consistency_guidance: str,
        novel_title: str
    ) -> Dict[int, Dict]:
        """辅助方法：逐章生成指定范围"""
        result = await self._fallback_to_chapter_by_chapter(
            medium_event, chapter_range, scenes_by_chapter,
            consistency_guidance, novel_title
        )
        
        if result.success:
            return result.chapters_content
        return {}
    
    def _create_default_scenes(self, medium_event: Dict, chapter_num: int) -> List[Dict]:
        """创建默认场景（应急用）"""
        return [
            {
                "name": f"第{chapter_num}章开场",
                "position": "opening",
                "purpose": "建立情境，引入冲突",
                "emotional_intensity": "medium"
            },
            {
                "name": f"第{chapter_num}章发展",
                "position": "development",
                "purpose": "推进情节",
                "emotional_intensity": "medium"
            },
            {
                "name": f"第{chapter_num}章高潮",
                "position": "climax",
                "purpose": "情绪爆发",
                "emotional_intensity": "high"
            }
        ]
    
    def _update_guidance(self, guidance: str, chapter_content: Dict) -> str:
        """更新一致性指导"""
        # 简单实现：追加本章关键信息
        updates = []
        
        char_states = chapter_content.get("character_states", {})
        if char_states:
            updates.append(f"角色状态更新: {char_states}")
        
        items = chapter_content.get("items_delta", {})
        if items:
            updates.append(f"物品变化: {items}")
        
        time_prog = chapter_content.get("time_progression", "")
        if time_prog:
            updates.append(f"时间推进: {time_prog}")
        
        if updates:
            return guidance + "\n" + "; ".join(updates)
        
        return guidance
