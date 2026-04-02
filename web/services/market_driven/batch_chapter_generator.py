# -*- coding: utf-8 -*-
"""
Market Driven Batch Chapter Generator
市场导向批量章节生成器

基于BluePrint批量生成30万字（100-150章）
"""

import json
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 导入状态管理器和情绪管理器
try:
    from web.services.market_driven.burst_state_manager import BurstStateManager
    from web.services.market_driven.emotion_flow import EmotionFlow, create_emotion_flow
    HAS_STATE_MANAGER = True
except ImportError as e:
    HAS_STATE_MANAGER = False
    logger.warning(f"状态管理器导入失败: {e}，使用旧模式")

# 🔥 导入滑动窗口优化器
try:
    from web.services.market_driven.stage_review_optimizer import StageReviewOptimizer
    HAS_STAGE_OPTIMIZER = True
except ImportError as e:
    HAS_STAGE_OPTIMIZER = False
    logger.warning(f"滑动窗口优化器导入失败: {e}，禁用该功能")

# 🔥 导入批次总结器
try:
    from web.services.market_driven.batch_summarizer import BatchSummarizer
    HAS_BATCH_SUMMARIZER = True
except ImportError as e:
    HAS_BATCH_SUMMARIZER = False
    logger.warning(f"批次总结器导入失败: {e}，禁用该功能")


class BatchChapterGenerator:
    """
    批量章节生成器
    基于BluePrint和套路，连续生成大量章节
    """
    
    def __init__(self, api_client=None, state_manager: Optional['BurstStateManager'] = None,
                 emotion_flow: Optional['EmotionFlow'] = None,
                 project_path: str = None):
        self.api_client = api_client
        self.generated_chapters = []
        self.failed_chapters = []
        self.state_manager = state_manager  # 状态管理器（情绪/剧情）
        self.emotion_flow = emotion_flow  # 情绪流
        
        # 🔥 项目路径处理
        if project_path:
            self.project_path = Path(project_path)
            logger.info(f"[BatchGenerator] 初始化，项目路径: {self.project_path}")
        else:
            self.project_path = None
            logger.warning(f"[BatchGenerator] 初始化，项目路径为空！")
        
        # 🔥 角色状态管理器（跨批次保持角色设定）
        self.character_state_manager = None
        self.world_state_manager = None  # 世界状态管理器
        self.stage_review_optimizer = None  # 滑动窗口优化器
        self.batch_summarizer = None  # 批次总结器
        self.optimized_windows = set()  # 已优化的窗口，避免重复优化
        self.current_batch_summary = None  # 当前批次总结
        
        if self.project_path:
            from .character_state_manager import CharacterStateManager
            from .world_state_manager import WorldStateManager
            
            self.character_state_manager = CharacterStateManager(str(self.project_path))
            self.world_state_manager = WorldStateManager(str(self.project_path))
            
            # 🔥 初始化滑动窗口优化器
            if HAS_STAGE_OPTIMIZER and api_client:
                self.stage_review_optimizer = StageReviewOptimizer(
                    project_path=str(self.project_path),
                    api_client=api_client
                )
                logger.info(f"[BatchGenerator] 滑动窗口优化器已启用")
            
            # 🔥 初始化批次总结器
            if HAS_BATCH_SUMMARIZER and api_client:
                self.batch_summarizer = BatchSummarizer(api_client)
                logger.info(f"[BatchGenerator] 批次总结器已启用")
            
            logger.info(f"[BatchGenerator] 状态管理器已启用: {self.project_path}")
    
    def generate_batch(self, novel_title: str, start_chapter: int, end_chapter: int,
                       blueprint: Dict, tropes: Dict, novel_data: Dict,
                       use_conversation: bool = True) -> Dict:
        """
        批量生成一批章节
        
        Args:
            novel_title: 小说标题
            start_chapter: 起始章节
            end_chapter: 结束章节
            blueprint: 章节规划
            tropes: 套路分析
            novel_data: 小说数据（包含世界观、角色等）
            use_conversation: 是否使用对话模式（默认启用）
            
        Returns:
            批量生成结果
        """
        logger.info(f"[BatchGenerator] 开始生成第{start_chapter}-{end_chapter}章 | 对话模式: {use_conversation}")
        
        # 🔥 使用对话模式生成
        if use_conversation and self.api_client:
            try:
                return self._generate_batch_conversation(
                    novel_title, start_chapter, end_chapter, 
                    blueprint, tropes, novel_data
                )
            except Exception as e:
                logger.error(f"[BatchGenerator] 对话模式失败: {e}，回退到独立模式")
        
        # 传统模式：每章独立调用
        return self._generate_batch_individual(
            novel_title, start_chapter, end_chapter,
            blueprint, tropes, novel_data
        )
    
    def _generate_batch_conversation(self, novel_title: str, start_chapter: int, end_chapter: int,
                                     blueprint: Dict, tropes: Dict, novel_data: Dict) -> Dict:
        """使用对话模式批量生成"""
        from web.services.market_driven.chapter_conversation_generator import (
            ChapterConversationGenerator
        )
        
        logger.info(f"[BatchGenerator] 🚀 使用对话模式生成第{start_chapter}-{end_chapter}章")
        
        # 确保 novel_data 中包含书名（处理 None、空字符串、"未命名" 等情况）
        if novel_title:
            current_title = novel_data.get('title')
            if not current_title or current_title == '未命名' or current_title.strip() == '':
                novel_data['title'] = novel_title
                logger.info(f"[BatchGenerator] 设置书名为: {novel_title}")
        
        # 🔥 校验并修正 novel_data 中的角色设定（跨批次一致性）
        if self.character_state_manager:
            novel_data = self.character_state_manager.validate_novel_data(novel_data)
            logger.info(f"[BatchGenerator] {self.character_state_manager.get_summary()}")
        
        # 🔥 初始化世界状态管理器（如果是第一批）
        if self.world_state_manager and start_chapter <= 1:
            self.world_state_manager.initialize_from_novel_data(novel_data)
            logger.info(f"[BatchGenerator] {self.world_state_manager.get_summary()}")
        
        # 创建对话生成器
        generator = ChapterConversationGenerator(
            api_client=self.api_client,
            novel_data=novel_data,
            tropes=tropes,
            world_state_manager=self.world_state_manager,  # 🔥 传递世界状态管理器
            project_path=str(self.project_path) if self.project_path else None  # 🔥 传递项目路径
        )
        
        # 生成章节
        chapters = generator.generate_chapters(
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            blueprint=blueprint
        )
        
        # 处理结果
        results = {
            "generated": [],
            "failed": [],
            "total_words": 0,
            "avg_quality": 0,
            "generation_mode": "conversation"
        }
        
        for chapter in chapters:
            chapter_num = chapter.get("chapter_number")
            word_count = chapter.get("word_count", 0)
            
            logger.info(f"[BatchGenerator] 处理第{chapter_num}章，字数: {word_count}")
            
            if word_count > 0:
                # 保存
                logger.info(f"[BatchGenerator] 准备保存第{chapter_num}章...")
                self._save_chapter(novel_title, chapter)
                
                # 🔥 修复：包含完整的章节数据，包括 content 和 extracted_info 用于批次总结
                results["generated"].append({
                    "chapter_number": chapter_num,
                    "chapter": chapter_num,  # 保持向后兼容
                    "title": chapter.get("title", ""),
                    "word_count": word_count,
                    "quality_score": chapter.get("quality_score", 8.0),
                    "content": chapter.get("content", ""),  # 用于批次总结分析
                    "extracted_info": chapter.get("extracted_info", {})  # 用于批次总结分析
                })
                results["total_words"] += word_count
            else:
                logger.error(f"[BatchGenerator] 第{chapter_num}章字数为0，标记为失败")
                results["failed"].append({
                    "chapter_number": chapter_num,
                    "chapter": chapter_num,  # 保持向后兼容
                    "error": chapter.get("error", "生成失败")
                })
        
        # 计算平均质量
        if results["generated"]:
            results["avg_quality"] = sum(
                c["quality_score"] for c in results["generated"]
            ) / len(results["generated"])
        
        # 🔥 批次总结：更新角色状态
        if self.character_state_manager and chapters:
            try:
                # 收集批次信息
                batch_info = self._collect_batch_info(start_chapter, end_chapter, chapters)
                self.character_state_manager.update_after_batch(batch_info)
                self.character_state_manager.sync_to_world_state()
                logger.info(f"[BatchGenerator] 角色状态已更新并同步到 world_state")
            except Exception as e:
                logger.error(f"[BatchGenerator] 批次总结失败: {e}")
        
        # 🔥 生成批次总结报告（JSON + MD）
        if self.batch_summarizer and chapters:
            try:
                self._generate_batch_summary(start_chapter, end_chapter, chapters)
            except Exception as e:
                logger.error(f"[BatchGenerator] 生成批次总结报告失败: {e}")
        
        # 🔥 触发滑动窗口优化（批次完成后，章节已保存到磁盘）
        self._trigger_sliding_window_review(start_chapter, end_chapter)
        
        logger.info(f"[BatchGenerator] 对话模式完成: 成功{len(results['generated'])}章, 失败{len(results['failed'])}章")
        return results
    
    def _collect_batch_info(self, start_chapter: int, end_chapter: int, chapters: List[Dict]) -> Dict:
        """
        收集批次信息用于角色状态更新
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节
            chapters: 生成的章节列表
            
        Returns:
            批次信息字典
        """
        batch_info = {
            "chapter_start": start_chapter,
            "chapter_end": end_chapter,
            "new_characters": [],
            "character_changes": []
        }
        
        # 从章节提取信息
        for chapter in chapters:
            extracted = chapter.get('extracted_info', {})
            
            # 收集新角色
            new_chars = extracted.get('new_characters', [])
            for char in new_chars:
                if char not in batch_info["new_characters"]:
                    batch_info["new_characters"].append(char)
            
            # 收集角色变化
            changes = extracted.get('character_changes', [])
            for change in changes:
                batch_info["character_changes"].append(change)
        
        return batch_info
    
    def _generate_batch_summary(self, start_chapter: int, end_chapter: int, chapters: List[Dict]):
        """
        🔥 生成批次总结报告（JSON + Markdown双格式）
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节
            chapters: 生成的章节列表
        """
        if not self.batch_summarizer or not self.project_path:
            return
        
        try:
            logger.info(f"[BatchGenerator] 生成批次总结: 第{start_chapter}-{end_chapter}章")
            
            # 调用批次总结器
            new_summary = self.batch_summarizer.summarize_batch(
                chapters=chapters,
                stage_goal=None,  # 可以从blueprint获取
                previous_summary=self.current_batch_summary
            )
            
            # 🔥 防御：确保 new_summary 不为 None
            if new_summary is None:
                logger.warning("[BatchGenerator] summarize_batch 返回 None，使用空总结")
                new_summary = {"notes": "空总结", "chapter_count": len(chapters)}
            
            # 合并总结（累积多批次信息）
            if self.current_batch_summary:
                self.current_batch_summary = self.batch_summarizer.merge_summaries(
                    self.current_batch_summary,
                    new_summary
                )
            else:
                self.current_batch_summary = new_summary
            
            # 保存到文件
            import json
            from datetime import datetime
            
            summary_dir = self.project_path / "batch_summaries"
            summary_dir.mkdir(exist_ok=True)
            
            # JSON格式
            summary_report = {
                "batch_info": {
                    "start_chapter": start_chapter,
                    "end_chapter": end_chapter,
                    "chapter_count": len(chapters),
                    "generated_at": datetime.now().isoformat()
                },
                "summary": self.current_batch_summary,
                "chapters": [
                    {
                        "chapter_number": c.get('chapter_number') or c.get('chapter'),
                        "title": c.get('title', ''),
                        "word_count": c.get('word_count', 0),
                        "quality_score": c.get('quality_score', 0)
                    }
                    for c in chapters
                ]
            }
            
            json_path = summary_dir / f"batch_summary_{start_chapter:03d}_{end_chapter:03d}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, ensure_ascii=False, indent=2)
            
            # Markdown格式（人工可读）
            md_lines = [
                f"# 📦 批次总结报告：第{start_chapter}-{end_chapter}章",
                "",
                f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**章节数**: {len(chapters)}章",
                "",
                "## 📊 章节统计",
                "",
                "| 章节 | 标题 | 字数 | 质量分 |",
                "|------|------|------|--------|"
            ]
            
            for c in chapters:
                ch_num = c.get('chapter_number') or c.get('chapter', 0)
                title = c.get('title', '')[:30]
                word_count = c.get('word_count', 0)
                quality = c.get('quality_score', 0)
                md_lines.append(f"| {ch_num} | {title} | {word_count} | {quality} |")
            
            md_lines.extend([
                "",
                "## 📝 AI分析总结",
                ""
            ])
            
            if self.current_batch_summary:
                ai_analysis = self.current_batch_summary.get('ai_analysis', {})
                if ai_analysis:
                    md_lines.append(f"**核心事件**: {ai_analysis.get('core_events', '无')}")
                    md_lines.append("")
                    md_lines.append(f"**角色发展**: {ai_analysis.get('character_development', '无')}")
                    md_lines.append("")
                    md_lines.append(f"**下章预告**: {ai_analysis.get('next_chapter_preview', '无')}")
                    md_lines.append("")
                
                # 新增钩子
                new_hooks = self.current_batch_summary.get('new_hooks', [])
                if new_hooks:
                    md_lines.append("### 🪝 新增钩子")
                    for hook in new_hooks:
                        md_lines.append(f"- {hook}")
                    md_lines.append("")
                
                # 待解决钩子
                pending_hooks = self.current_batch_summary.get('pending_hooks', [])
                if pending_hooks:
                    md_lines.append("### ⏳ 待解决钩子")
                    for hook in pending_hooks:
                        md_lines.append(f"- {hook}")
                    md_lines.append("")
            
            md_path = summary_dir / f"batch_summary_{start_chapter:03d}_{end_chapter:03d}.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines))
            
            # 同时保存最新版本（用于传递给下一个会话）
            latest_json = self.project_path / "batch_summary_latest.json"
            with open(latest_json, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[BatchGenerator] 批次总结已保存: {json_path} 和 {md_path}")
            
        except Exception as e:
            logger.error(f"[BatchGenerator] 生成批次总结失败: {e}")
    
    def _trigger_sliding_window_review(self, start_chapter: int, end_chapter: int):
        """
        🔥 触发滑动窗口阶段性复盘（批次完成后）
        
        滑动窗口配置：
        - 窗口大小：10章
        - 重叠：2章（保证连贯性）
        - 步长：8章
        
        触发时机：
        - 窗口1: 第1-10章（第10章生成后触发）
        - 窗口2: 第8-17章（第17章生成后触发）
        - 窗口3: 第16-25章（第25章生成后触发）
        
        与原来的区别：
        - 原来：在生成过程中触发（章节还没保存）
        - 现在：批次完成后触发（章节已保存到磁盘）
        """
        if not self.stage_review_optimizer or not self.project_path:
            return
        
        try:
            # 计算哪些滑动窗口已完整且未优化过
            # 窗口大小10章，重叠2章
            window_size = 10
            overlap = 2
            
            # 找到当前批次可能覆盖的所有窗口
            # 正确的窗口结束点应该是: 10, 18, 26, 34... (步长8)，以及最后的200
            step = window_size - overlap  # 8
            
            for window_end in range(end_chapter, start_chapter - 1, -1):
                # 检查是否是有效的窗口结束点
                # 窗口序列: 1-10, 8-17, 16-25, 24-33... 结束于 10, 18, 26, 34... 194, 200
                # 规律1: (window_end - 10) % 8 == 0  → 10, 18, 26, ... 194
                # 规律2: window_end == 200 (最后一个特殊窗口)
                is_standard_window = (window_end >= 10) and ((window_end - 10) % step == 0)
                is_final_window = (window_end == 200)
                
                if not (is_standard_window or is_final_window):
                    continue
                    
                # 计算窗口起始点
                if is_final_window:
                    window_start = 192  # 最后一个窗口特殊处理: 192-200
                else:
                    window_index = (window_end - 10) // step
                    window_start = 1 + window_index * step
                
                # 检查窗口是否已优化过
                window_key = f"{window_start}-{window_end}"
                if window_key in self.optimized_windows:
                    continue
                
                # 检查窗口是否完整（所有章节都已保存）
                chapters_dir = self.project_path / "chapters"
                all_exist = True
                for ch_num in range(window_start, window_end + 1):
                    json_path = chapters_dir / f"chapter_{ch_num:03d}.json"
                    if not json_path.exists():
                        all_exist = False
                        break
                
                if not all_exist:
                    logger.info(f"[BatchGenerator] 窗口 {window_start}-{window_end} 不完整，跳过优化")
                    continue
                
                # 触发滑动窗口优化
                logger.info(f"[BatchGenerator] 🔥🔥🔥 触发滑动窗口优化: {window_start}-{window_end} 🔥🔥🔥")
                
                try:
                    report = self.stage_review_optimizer.optimize_window(window_start, window_end)
                    
                    issues_found = len(report.get('issues', []))
                    fixes_applied = len(report.get('fixes_applied', []))
                    
                    logger.info(f"[BatchGenerator] ✅ 窗口 {window_start}-{window_end} 优化完成 | 问题: {issues_found} | 修复: {fixes_applied}")
                    
                    # 标记为已优化
                    self.optimized_windows.add(window_key)
                    
                except Exception as e:
                    logger.error(f"[BatchGenerator] ❌ 窗口 {window_start}-{window_end} 优化失败: {e}")
                    # 失败不重试，下次批次可能再次尝试
                    
        except Exception as e:
            logger.error(f"[BatchGenerator] 滑动窗口优化触发失败: {e}")
    
    def _generate_batch_individual(self, novel_title: str, start_chapter: int, end_chapter: int,
                                   blueprint: Dict, tropes: Dict, novel_data: Dict) -> Dict:
        """传统模式：每章独立生成"""
        logger.info(f"[BatchGenerator] 使用独立模式生成第{start_chapter}-{end_chapter}章")
        
        results = {
            "generated": [],
            "failed": [],
            "total_words": 0,
            "avg_quality": 0,
            "generation_mode": "individual"
        }
        
        for chapter_num in range(start_chapter, end_chapter + 1):
            try:
                logger.info(f"  生成第{chapter_num}章...")
                
                # 生成单章
                chapter = self._generate_single_chapter(
                    chapter_num=chapter_num,
                    novel_title=novel_title,
                    blueprint=blueprint,
                    tropes=tropes,
                    novel_data=novel_data
                )
                
                # 保存
                self._save_chapter(novel_title, chapter)
                
                # 更新统计数据
                results["generated"].append({
                    "chapter": chapter_num,
                    "title": chapter["title"],
                    "word_count": chapter["word_count"],
                    "quality_score": chapter["quality_score"]
                })
                results["total_words"] += chapter["word_count"]
                
                logger.info(f"  ✅ 第{chapter_num}章完成 ({chapter['word_count']}字)")
                
                # 短暂休息，避免API限流
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ 第{chapter_num}章失败: {e}")
                results["failed"].append({
                    "chapter": chapter_num,
                    "error": str(e)
                })
                self.failed_chapters.append(chapter_num)
                continue
        
        # 计算平均质量
        if results["generated"]:
            results["avg_quality"] = sum(
                c["quality_score"] for c in results["generated"]
            ) / len(results["generated"])
        
        # 🔥 批次总结：更新角色状态（独立模式暂无提取信息）
        if self.character_state_manager:
            try:
                # 独立模式下没有 extracted_info，只更新章节统计
                batch_info = {
                    "chapter_start": start_chapter,
                    "chapter_end": end_chapter,
                    "new_characters": [],
                    "character_changes": []
                }
                self.character_state_manager.update_after_batch(batch_info)
                logger.info(f"[BatchGenerator] 角色状态已更新（独立模式）")
            except Exception as e:
                logger.error(f"[BatchGenerator] 批次总结失败: {e}")
        
        logger.info(f"[BatchGenerator] 独立模式完成: 成功{len(results['generated'])}章, 失败{len(results['failed'])}章")
        return results
    
    def _generate_single_chapter(self, chapter_num: int, novel_title: str,
                                  blueprint: Dict, tropes: Dict, novel_data: Dict) -> Dict:
        """
        生成单章
        严格按BluePrint执行
        """
        # 获取本章规划
        chapter_plan = self._get_chapter_plan(chapter_num, blueprint)
        
        # 构建上下文（智能压缩）
        context = self._build_chapter_context(chapter_num, novel_title, novel_data)
        
        # 构建Prompt
        prompt = self._build_chapter_prompt(
            chapter_num=chapter_num,
            chapter_plan=chapter_plan,
            context=context,
            novel_data=novel_data,
            tropes=tropes
        )
        
        # 生成内容
        if self.api_client:
            content = self._call_ai_generation(prompt, chapter_num)
        else:
            # 模拟模式
            content = self._mock_chapter_content(chapter_num, chapter_plan)
        
        # 质量评估
        quality_score = self._assess_chapter_quality(content, chapter_plan, tropes)
        
        # 如果质量低，尝试优化
        if quality_score < 7.0:
            logger.warning(f"  第{chapter_num}章质量偏低({quality_score})，尝试优化...")
            content = self._optimize_chapter(content, chapter_plan, tropes)
            quality_score = self._assess_chapter_quality(content, chapter_plan, tropes)
        
        # 确保 content 是字符串后再计算字数
        content_str = content if isinstance(content, str) else str(content) if content else ""
        
        return {
            "chapter_number": chapter_num,
            "title": self._extract_title(content_str, chapter_plan),
            "content": content_str,
            "word_count": len(content_str),
            "quality_score": quality_score,
            "chapter_plan": chapter_plan,
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_chapter_plan(self, chapter_num: int, blueprint: Dict) -> Dict:
        """获取本章规划"""
        # 从blueprint中获取本章规划
        chapters = blueprint.get("chapters", [])
        
        for ch in chapters:
            if ch.get("chapter_number") == chapter_num:
                return ch
        
        # 如果没有精确匹配，根据套路推断
        return self._infer_chapter_plan(chapter_num, blueprint)
    
    def _infer_chapter_plan(self, chapter_num: int, blueprint: Dict) -> Dict:
        """根据套路推断章节规划"""
        # 根据章节数推断
        if chapter_num == 1:
            return {"climax_type": "转折", "required_elements": ["系统出现", "被羞辱"]}
        elif chapter_num == 3:
            return {"climax_type": "小爽点", "required_elements": ["第一次花钱"]}
        elif chapter_num == 5:
            return {"climax_type": "爽点", "required_elements": ["第一次打脸"]}
        elif chapter_num % 10 == 0:
            return {"climax_type": "大爽点", "required_elements": ["身份升级"]}
        elif chapter_num % 5 == 0:
            return {"climax_type": "爽点", "required_elements": ["打脸"]}
        else:
            return {"climax_type": "过渡", "required_elements": ["推进剧情"]}
    
    def _build_chapter_context(self, chapter_num: int, novel_title: str, novel_data: Dict) -> str:
        """
        构建章节上下文（智能压缩）
        只给AI最必要的信息
        """
        context_parts = []
        
        # 1. 基础设定（始终保留）
        context_parts.append(f"""
【小说基础设定】
- 标题：{novel_title}
- 世界观：{novel_data.get('core_worldview', {}).get('world_overview', '现代都市')}
- 力量体系：{novel_data.get('core_worldview', {}).get('power_system', {}).get('name', '资金等级')}
""")
        
        # 2. 主角当前状态
        protagonist = novel_data.get('character_design', {}).get('main_character', {})
        current_stage = self._get_current_growth_stage(chapter_num)
        context_parts.append(f"""
【主角状态】
- 姓名：{protagonist.get('basic_info', {}).get('name', '主角')}
- 当前阶段：{current_stage}
- 当前身份：{self._get_current_identity(chapter_num)}
- 性格：{protagonist.get('personality', {}).get('core_traits', '隐忍但不怂')}
""")
        
        # 3. 最近剧情（最近3章摘要）
        recent_chapters = self._get_recent_chapters(novel_title, chapter_num, count=3)
        if recent_chapters:
            context_parts.append("【最近剧情】")
            for ch in recent_chapters:
                context_parts.append(f"- 第{ch['chapter_number']}章：{ch.get('summary', '剧情推进')}")
        
        # 4. 当前反派
        current_antagonist = self._get_current_antagonist(chapter_num)
        context_parts.append(f"""
【当前主要反派】
- {current_antagonist}
""")
        
        # 5. 未回收伏笔（前5章内）
        active_hooks = self._get_active_hooks(novel_title, chapter_num, lookback=5)
        if active_hooks:
            context_parts.append("【待回收伏笔】")
            for hook in active_hooks:
                context_parts.append(f"- {hook}")
        
        return "\n".join(context_parts)
    
    def _get_current_growth_stage(self, chapter_num: int) -> str:
        """获取主角当前成长阶段"""
        if chapter_num <= 30:
            return "初期崛起"
        elif chapter_num <= 80:
            return "地方霸主"
        elif chapter_num <= 150:
            return "全国知名"
        else:
            return "全球巅峰"
    
    def _get_current_identity(self, chapter_num: int) -> str:
        """获取主角当前身份"""
        if chapter_num <= 10:
            return "刚获得系统的普通人"
        elif chapter_num <= 30:
            return "小有资产的富豪"
        elif chapter_num <= 50:
            return "地方知名富豪"
        elif chapter_num <= 100:
            return "全国级别富豪"
        else:
            return "顶级富豪/全球首富"
    
    def _get_recent_chapters(self, novel_title: str, current: int, count: int = 3) -> List[Dict]:
        """获取最近章节"""
        recent = []
        for i in range(max(1, current - count), current):
            chapter_data = self._load_chapter_data(novel_title, i)
            if chapter_data:
                recent.append({
                    "chapter_number": i,
                    "summary": self._summarize_chapter(chapter_data)
                })
        return recent
    
    def _summarize_chapter(self, chapter_data: Dict) -> str:
        """生成章节摘要"""
        # 简化版：返回标题
        return chapter_data.get("title", "剧情推进")
    
    def _get_current_antagonist(self, chapter_num: int) -> str:
        """获取当前反派"""
        if chapter_num <= 30:
            return "势利眼小人物（前女友、宝马男等）"
        elif chapter_num <= 80:
            return "地方富二代集团"
        elif chapter_num <= 150:
            return "资本大佬"
        else:
            return "神秘组织"
    
    def _get_active_hooks(self, novel_title: str, current: int, lookback: int = 5) -> List[str]:
        """获取未回收伏笔"""
        # 简化版：返回固定列表
        return ["更大的势力在观察主角", "神秘组织的线索"]
    
    def _build_chapter_prompt(self, chapter_num: int, chapter_plan: Dict,
                               context: str, novel_data: Dict, tropes: Dict) -> str:
        """构建章节生成Prompt"""
        
        return f"""
你是一位深谙番茄小说套路的资深写手。

{context}

【本章要求】
- 第{chapter_num}章
- 本章类型：{chapter_plan.get('climax_type', '过渡')}
- 必须包含：{', '.join(chapter_plan.get('required_elements', ['推进剧情']))}
- 情绪走向：{chapter_plan.get('emotion', '根据类型调整')}

【写作要求】
1. 严格按本章类型写，{chapter_plan.get('climax_type')}章节必须有相应强度
2. 必须包含所有要求的要素
3. 节奏要快，直接进入正题，不要铺垫
4. 对话直白有力，少用形容词
5. 每段不超过3行，适合手机阅读
6. 字数2500字左右
7. 结尾必须有钩子（悬念、转折或期待）

【风格指南】
- 快节奏、直白、爽点密集
- 主角杀伐果断，不圣母
- 打脸要干脆，不要拖泥带水
- 周围人的震惊反应要写足

请直接创作第{chapter_num}章内容。
"""
    
    def _call_ai_generation(self, prompt: str, chapter_num: int) -> str:
        """调用AI生成"""
        response = self.api_client.generate_content_with_retry(
            content_type="chapter_content",
            user_prompt=prompt,
            temperature=0.7,
            purpose=f"生成第{chapter_num}章"
        )
        
        if isinstance(response, str):
            return response
        elif isinstance(response, dict):
            return response.get("content", str(response))
        elif isinstance(response, list):
            # 如果是列表，尝试提取内容或拼接
            if len(response) > 0:
                if isinstance(response[0], dict):
                    return response[0].get("content", str(response))
                elif isinstance(response[0], str):
                    return "\n\n".join(response)
            return str(response)
        else:
            return str(response)
    
    def _mock_chapter_content(self, chapter_num: int, chapter_plan: Dict) -> str:
        """模拟章节内容（测试用）"""
        return f"""
第{chapter_num}章 {chapter_plan.get('climax_type', '剧情推进')}

（模拟内容：这是第{chapter_num}章的模拟内容，实际使用时会被AI生成内容替换）

本章类型：{chapter_plan.get('climax_type')}
必须要素：{', '.join(chapter_plan.get('required_elements', []))}

主角继续他的神豪之路...
（此处省略2500字）

结尾留下悬念，让读者想看下一章...
"""
    
    def _assess_chapter_quality(self, content, chapter_plan: Dict, tropes: Dict) -> float:
        """评估章节质量"""
        # 确保 content 是字符串
        if not isinstance(content, str):
            content = str(content) if content else ""
        
        # 基础检查
        score = 8.0  # 基础分
        
        # 字数检查
        word_count = len(content)
        if word_count < 2000:
            score -= 1.0
        elif word_count > 3000:
            score += 0.5
        
        # 检查必要要素
        required = chapter_plan.get('required_elements', [])
        for elem in required:
            if elem in content:
                score += 0.2
        
        # 检查爽点（如果是爽点章节）
        if '爽点' in chapter_plan.get('climax_type', ''):
            if '震惊' in content or '后悔' in content:
                score += 0.5
            else:
                score -= 0.5
        
        # 检查钩子
        if chapter_num := self._extract_chapter_number_from_content(content):
            pass  # 这里可以检查结尾钩子
        
        return min(10.0, max(1.0, score))
    
    def _extract_chapter_number_from_content(self, content: str) -> Optional[int]:
        """从内容中提取章节号"""
        import re
        match = re.search(r'第(\d+)章', content)
        if match:
            return int(match.group(1))
        return None
    
    def _optimize_chapter(self, content, chapter_plan: Dict, tropes: Dict) -> str:
        """优化章节"""
        # 确保 content 是字符串
        if not isinstance(content, str):
            content = str(content) if content else ""
        
        # 简化版：添加必要要素
        optimized = content
        
        # 确保有足够字数
        if len(optimized) < 2000:
            optimized += "\n\n（补充内容，确保达到字数要求...）\n"
        
        return optimized
    
    def _extract_title(self, content, chapter_plan: Dict) -> str:
        """
        提取或生成章节标题
        
        策略：
        1. 优先从chapter_plan获取（战术规划中定义的标题）
        2. 其次从chapter_plan的event/purpose字段生成
        3. 最后从内容分析提取
        """
        import re
        
        # 确保 content 是字符串
        if not isinstance(content, str):
            content = str(content) if content else ""
        
        # 1. 优先从chapter_plan获取标题
        if chapter_plan:
            # 直接标题字段
            title = chapter_plan.get('title', '').strip()
            if title and title != '章节' and not title.startswith('第'):
                return title
            
            # 从event字段生成（事件描述通常是核心剧情）
            event = chapter_plan.get('event', '').strip()
            if event and len(event) <= 30:
                return event
            elif event:
                return event[:20] + ('...' if len(event) > 20 else '')
            
            # 从purpose字段生成（战术企图）
            purpose = chapter_plan.get('purpose', '').strip()
            if purpose and len(purpose) <= 30:
                return purpose
            elif purpose:
                return purpose[:20] + ('...' if len(purpose) > 20 else '')
            
            # 从hook_content获取（钩子内容往往有吸引力）
            hook = chapter_plan.get('hook_content', '').strip()
            if hook and len(hook) <= 30:
                return hook
            elif hook:
                return hook[:20] + ('...' if len(hook) > 20 else '')
        
        # 2. 尝试从内容中提取（备用方案）
        match = re.search(r'第\d+章\s*([^\n]+)', content)
        if match:
            extracted = match.group(1).strip()
            if extracted and not extracted.startswith('【'):
                return extracted
        
        # 3. 默认标题
        chapter_num = chapter_plan.get('chapter_number', 0) if chapter_plan else 0
        return f'第{chapter_num}章'
    
    def _save_chapter(self, novel_title: str, chapter: Dict):
        """保存章节"""
        try:
            # 🔥 使用项目路径（支持用户子目录）
            if self.project_path:
                base_path = Path(self.project_path) / "chapters"
                logger.info(f"[BatchGenerator] 使用项目路径保存: {base_path}")
            else:
                # 兼容旧版：直接放在根目录
                base_path = Path("小说项目") / novel_title / "chapters"
                logger.warning(f"[BatchGenerator] project_path为空，使用兼容路径: {base_path}")
            
            # 确保目录存在
            base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"[BatchGenerator] 目录确保存在: {base_path}")
            
            chapter_num = chapter.get('chapter_number', 0)
            file_path = base_path / f"chapter_{chapter_num:03d}.json"
            
            logger.info(f"[BatchGenerator] 准备保存到: {file_path}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chapter, f, ensure_ascii=False, indent=2)
            
            # 验证文件是否真正写入
            if file_path.exists():
                file_size = file_path.stat().st_size
                logger.info(f"[BatchGenerator] ✅ 章节已保存: {file_path} | 大小: {file_size}字节 | 字数: {chapter.get('word_count', 0)}")
            else:
                logger.error(f"[BatchGenerator] ❌ 文件保存后不存在: {file_path}")
                
        except Exception as e:
            logger.error(f"[BatchGenerator] ❌ 保存章节失败: {e} | chapter_number: {chapter.get('chapter_number')}", exc_info=True)
    
    def _load_chapter_data(self, novel_title: str, chapter_num: int) -> Optional[Dict]:
        """加载章节数据"""
        # 🔥 使用项目路径（支持用户子目录）
        if self.project_path:
            file_path = self.project_path / "chapters" / f"chapter_{chapter_num:03d}.json"
        else:
            # 兼容旧版
            file_path = Path("小说项目") / novel_title / "chapters" / f"chapter_{chapter_num:03d}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def generate_with_state_manager(self, novel_title: str, start_chapter: int, 
                                     end_chapter: int, blueprint: Dict, 
                                     tropes: Dict, plan: Dict) -> Dict:
        """
        使用状态管理器和情绪流批量生成章节
        保持核心设定一致，管理动态状态和情绪心电图
        """
        if not HAS_STATE_MANAGER:
            logger.warning("StateManager不可用，回退到旧模式")
            return self.generate_batch(novel_title, start_chapter, end_chapter, 
                                      blueprint, tropes, plan)
        
        # 初始化状态管理器
        if self.state_manager is None:
            self.state_manager = BurstStateManager(novel_title)
        
        # 如果核心设定未初始化，从plan初始化
        if self.state_manager.core_identity is None:
            logger.info(f"从plan初始化核心设定...")
            self.state_manager.init_from_plan(plan, tropes)
        
        # 初始化情绪流
        if self.emotion_flow is None:
            total_chapters = plan.get('total_chapters', 100)
            genre = plan.get('genre', '神豪文-花钱返利类')
            
            # 尝试从一阶段产物获取AI生成的情绪曲线
            phase_one_products = plan.get('phase_one_products') or {}
            
            self.emotion_flow = create_emotion_flow(
                novel_title=novel_title,
                genre=genre,
                total_chapters=total_chapters,
                phase_one_products=phase_one_products
            )
            
            if phase_one_products.get('emotion_curve'):
                logger.info(f"已加载AI生成的个性化情绪曲线: {total_chapters}章")
            else:
                logger.info(f"使用固定模板情绪曲线: {total_chapters}章")
            
            logger.info("\n" + self.emotion_flow.get_curve_visualization())
        
        # 检查连续低强度章节
        low_chapters = self.emotion_flow.check_continuous_low(window=3)
        if low_chapters:
            logger.warning(f"情绪流警告: 第{low_chapters}章开始连续低强度!")
        
        results = {
            "generated": [],
            "failed": [],
            "total_words": 0,
            "avg_quality": 0
        }
        
        for chapter_num in range(start_chapter, end_chapter + 1):
            try:
                logger.info(f"  生成第{chapter_num}章（使用状态管理+情绪流）...")
                
                # 获取本章情绪节拍
                beat = self.emotion_flow.get_beat(chapter_num)
                if beat:
                    logger.info(f"    情绪节拍: {beat.emotion}(强度{beat.intensity}) | {beat.beat_type} | {beat.purpose}")
                
                # 构建情绪节拍字典
                beat_dict = {
                    "emotion": beat.emotion,
                    "intensity": beat.intensity,
                    "beat_type": beat.beat_type,
                    "event": beat.event,
                    "purpose": beat.purpose
                } if beat else None
                
                # 使用状态管理器构建system prompt（传入情绪节拍）
                system_prompt = self.state_manager.build_system_prompt(chapter_num, beat_dict)
                
                # 调用AI生成
                chapter_data = self._call_ai_with_state(system_prompt, chapter_num)
                
                if chapter_data:
                    # 记录实际情绪
                    actual_emotion = chapter_data.get('emotion_result', {})
                    self.emotion_flow.record_actual(
                        ch=chapter_num,
                        emotion=actual_emotion.get('actual_emotion', '未知'),
                        intensity=actual_emotion.get('intensity', 5),
                        note=actual_emotion.get('hook', '')
                    )
                    
                    # 更新状态
                    self.state_manager.update_after_chapter(chapter_num, chapter_data)
                    
                    # 保存章节
                    self._save_chapter(novel_title, {
                        "chapter_number": chapter_num,
                        "title": chapter_data.get("chapter_title", f"第{chapter_num}章"),
                        "content": chapter_data.get("content", ""),
                        "word_count": len(chapter_data.get("content", "")),
                        "quality_score": actual_emotion.get("intensity", 5),
                        "emotion_beat": {
                            "planned": {"emotion": beat.emotion, "intensity": beat.intensity, "type": beat.beat_type} if beat else None,
                            "actual": actual_emotion
                        },
                        "state_snapshot": self.state_manager.get_state_for_session_switch(),
                        "generated_at": datetime.now().isoformat()
                    })
                    
                    results["generated"].append({
                        "chapter": chapter_num,
                        "title": chapter_data.get("chapter_title", f"第{chapter_num}章"),
                        "word_count": len(chapter_data.get("content", "")),
                        "quality_score": chapter_data.get("emotion_result", {}).get("intensity", 5)
                    })
                    
                    logger.info(f"  ✅ 第{chapter_num}章完成 ({len(chapter_data.get('content', ''))}字)")
                else:
                    raise ValueError("生成返回空数据")
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ 第{chapter_num}章失败: {e}")
                results["failed"].append({
                    "chapter": chapter_num,
                    "error": str(e)
                })
                continue
        
        # 计算平均质量
        if results["generated"]:
            results["avg_quality"] = sum(
                c["quality_score"] for c in results["generated"]
            ) / len(results["generated"])
        
        # 输出情绪流摘要
        if self.emotion_flow:
            logger.info("\n" + self.emotion_flow.get_curve_visualization())
            low_chapters = self.emotion_flow.check_continuous_low(window=3)
            if low_chapters:
                logger.warning(f"[情绪流警告] 第{low_chapters}章开始连续低强度，建议调整!")
        
        logger.info(f"[BatchGenerator] 批量生成完成: 成功{len(results['generated'])}章")
        return results
    
    def _call_ai_with_state(self, system_prompt: str, chapter_num: int) -> Optional[Dict]:
        """使用状态管理器的prompt调用AI"""
        if not self.api_client:
            return None
        
        response = self.api_client.generate_content_with_retry(
            content_type="chapter_content_structured",
            system_prompt=system_prompt,
            user_prompt=f"请生成第{chapter_num}章内容，严格按照系统提示中的格式要求返回JSON。",
            temperature=0.7,
            purpose=f"生成第{chapter_num}章（结构化）"
        )
        
        # 解析JSON响应
        if isinstance(response, dict):
            return response
        elif isinstance(response, str):
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # 尝试从文本中提取JSON
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(0))
                    except:
                        pass
                # 如果提取失败，包装成简单格式
                return {
                    "chapter_title": f"第{chapter_num}章",
                    "content": response,
                    "state_updates": {},
                    "emotion_result": {"actual_emotion": "未知", "intensity": 5, "hook": "待续"}
                }
        elif isinstance(response, list) and len(response) > 0:
            if isinstance(response[0], dict):
                return response[0]
        
        return None


class ChapterBluePrintGenerator:
    """
    章节规划生成器
    为30万字生成完整的章节规划（BluePrint）
    """
    
    def generate_blueprint(self, total_words: int, tropes: Dict, plan: Dict) -> Dict:
        """
        生成完整章节规划
        
        Args:
            total_words: 目标字数
            tropes: 套路分析
            plan: 方案
            
        Returns:
            BluePrint
        """
        chapters = total_words // 2500
        
        blueprint = {
            "total_chapters": chapters,
            "total_words_target": total_words,
            "chapters": []
        }
        
        for ch_num in range(1, chapters + 1):
            chapter_plan = self._generate_chapter_plan(ch_num, tropes, plan)
            blueprint["chapters"].append(chapter_plan)
        
        return blueprint
    
    def _generate_chapter_plan(self, chapter_num: int, tropes: Dict, plan: Dict) -> Dict:
        """生成单章规划"""
        # 基于套路和章节位置生成规划
        
        # 确定爽点类型
        climax_type = self._determine_climax_type(chapter_num, tropes)
        
        # 确定必须要素
        required_elements = self._determine_required_elements(chapter_num, tropes)
        
        # 确定情绪
        emotion = self._determine_emotion(chapter_num, climax_type)
        
        return {
            "chapter_number": chapter_num,
            "title": f"第{chapter_num}章",  # 占位，实际生成时填充
            "climax_type": climax_type,
            "required_elements": required_elements,
            "emotion": emotion,
            "target_words": 2500
        }
    
    def _determine_climax_type(self, chapter_num: int, tropes: Dict) -> str:
        """确定爽点类型"""
        pacing = tropes.get("pacing", {})
        
        # 特殊章节
        if chapter_num == 1:
            return "转折"
        elif chapter_num in [3, 5]:
            return "爽点"
        elif chapter_num % 30 == 0:
            return "大高潮"
        elif chapter_num % 10 == 0:
            return "大爽点"
        elif chapter_num % 5 == 0:
            return "爽点"
        else:
            return "过渡"
    
    def _determine_required_elements(self, chapter_num: int, tropes: Dict) -> List[str]:
        """确定必须要素"""
        elements = []
        
        if chapter_num == 1:
            elements = ["系统出现", "被羞辱"]
        elif chapter_num == 3:
            elements = ["第一次花钱"]
        elif chapter_num == 5:
            elements = ["第一次打脸"]
        elif chapter_num % 10 == 0:
            elements = ["身份升级", "打脸"]
        elif chapter_num % 5 == 0:
            elements = ["打脸", "震惊众人"]
        else:
            elements = ["推进剧情", "铺垫"]
        
        return elements
    
    def _determine_emotion(self, chapter_num: int, climax_type: str) -> str:
        """确定情绪"""
        emotion_map = {
            "转折": "震惊→希望",
            "爽点": "压抑→爽快",
            "大爽点": "紧张→爆发→爽快",
            "大高潮": "积累→爆发→满足",
            "过渡": "推进→期待"
        }
        return emotion_map.get(climax_type, "推进")


# 便捷函数
def generate_300k_words(novel_title: str, genre: str, tropes: Dict, plan: Dict, 
                       products: Dict, api_client=None, project_path: str = None,
                       username: str = None) -> Dict:
    """
    便捷函数：生成30万字
    
    Args:
        novel_title: 小说标题
        genre: 题材
        tropes: 套路
        plan: 计划
        products: 产物
        api_client: API客户端
        project_path: 项目路径（如果提供，章节将保存在此路径下）
        username: 用户名（如果不提供，尝试从project_path推断）
    """
    # 生成BluePrint
    blueprint_gen = ChapterBluePrintGenerator()
    # 使用配置默认50万字
    from web.services.market_driven.config import get_target_words
    target_words = get_target_words()
    blueprint = blueprint_gen.generate_blueprint(target_words, tropes, plan)
    
    # 准备novel_data
    # 🔥 优先使用传入的username，如果没有则从project_path推断
    if not username and project_path:
        # 从lixiaoshuo项目/{username}/{title} 或 小说项目/{title} 推断
        path_parts = Path(project_path).parts
        if len(path_parts) >= 2 and path_parts[-2] != "小说项目":
            username = path_parts[-2]
        else:
            username = 'anonymous'
    elif not username:
        username = 'anonymous'
    
    # 🔥 获取用户选择的主角名（优先使用用户填写的，覆盖AI生成的）
    character_design = products.get("character_design", {})
    user_choices = products.get("user_choices", {})
    user_protagonist_name = user_choices.get("protagonist_name")
    
    # 如果用户填写了主角名，覆盖AI生成的角色设计中的名字
    if user_protagonist_name and character_design.get("protagonist"):
        character_design["protagonist"]["name"] = user_protagonist_name
        logger.info(f"[章节生成] 使用用户填写的主角名: {user_protagonist_name}")
    
    novel_data = {
        "title": novel_title,
        "username": username,
        "_username": username,
        "core_worldview": products.get("core_worldview", {}),
        "character_design": character_design,
        "faction_system": products.get("faction_system", {}),
        "plan": products.get("plan", {}),
        "emotion_curve": products.get("emotion_curve", {}),
        "user_choices": user_choices  # 🔥 保存用户选择，供后续使用
    }
    
    # 批量生成
    batch_gen = BatchChapterGenerator(api_client=api_client, project_path=project_path)
    
    all_results = []
    chapters_per_batch = 6  # 🔥 每批6章，避免token限制
    total_chapters = 120
    batches = (total_chapters + chapters_per_batch - 1) // chapters_per_batch
    
    for batch_num in range(1, batches + 1):
        start = (batch_num - 1) * chapters_per_batch + 1
        end = min(batch_num * chapters_per_batch, total_chapters)
        
        logger.info(f"生成第{batch_num}/{batches}批: 第{start}-{end}章")
        
        result = batch_gen.generate_batch(
            novel_title=novel_title,
            start_chapter=start,
            end_chapter=end,
            blueprint=blueprint,
            tropes=tropes,
            novel_data=novel_data
        )
        
        all_results.append(result)
    
    # 汇总
    total_words = sum(r["total_words"] for r in all_results)
    total_generated = sum(len(r["generated"]) for r in all_results)
    total_failed = sum(len(r["failed"]) for r in all_results)
    avg_quality = sum(r["avg_quality"] for r in all_results) / len(all_results)
    
    return {
        "total_chapters": total_generated,
        "total_words": total_words,
        "failed_chapters": total_failed,
        "avg_quality": avg_quality,
        "blueprint": blueprint
    }
