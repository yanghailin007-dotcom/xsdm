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

# 🔥 导入 V2 章节对话生成器
try:
    from web.services.market_driven.v2_architecture.chapter_conversation_v2 import (
        ChapterConversationV2
    )
    HAS_V2_GENERATOR = True
    logger.info("[BatchGenerator] V2 章节生成器已加载")
except ImportError as e:
    HAS_V2_GENERATOR = False
    logger.warning(f"[BatchGenerator] V2 章节生成器导入失败: {e}")



class BatchChapterGenerator:
    """
    批量章节生成器
    基于BluePrint和套路，连续生成大量章节
    """
    
    def __init__(self, api_client=None, state_manager: Optional['BurstStateManager'] = None,
                 emotion_flow: Optional['EmotionFlow'] = None,
                 project_path: str = None,
                 stop_checker=None):  # 🔥 新增：停止检查函数
        self.api_client = api_client
        self.generated_chapters = []
        self.failed_chapters = []
        self.state_manager = state_manager  # 状态管理器（情绪/剧情）
        self.emotion_flow = emotion_flow  # 情绪流
        self._stop_checker = stop_checker  # 🔥 停止检查函数
        
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
        self.v2_last_batch_summary = None  # 🔥 V2对话内生成的批次总结
        self._chapter_titles = set()  # 本批次已生成的标题，用于唯一性检查
        
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
                self.batch_summarizer = BatchSummarizer(
                    api_client,
                    project_path=str(self.project_path)
                )
                logger.info(f"[BatchGenerator] 批次总结器已启用")
            
            logger.info(f"[BatchGenerator] 状态管理器已启用: {self.project_path}")
    
    def generate_batch(self, novel_title: str, start_chapter: int, end_chapter: int,
                       blueprint: Dict, tropes: Dict, novel_data: Dict,
                       use_conversation: bool = True, progress_callback=None) -> Dict:
        """
        批量生成一批章节
        
        Args:
            novel_title: 小说标题
            start_chapter: 起始章节
            end_chapter: 结束章节
            blueprint: 章节规划
            tropes: 爆款分析
            novel_data: 小说数据（包含世界观、角色等）
            use_conversation: 是否使用对话模式（默认启用）
            
        Returns:
            批量生成结果
        """
        logger.info(f"[BatchGenerator] 开始生成第{start_chapter}-{end_chapter}章 | 对话模式: {use_conversation}")
        
        results = None
        
        # 🔥 使用对话模式生成
        if use_conversation and self.api_client:
            try:
                results = self._generate_batch_conversation(
                    novel_title, start_chapter, end_chapter,
                    blueprint, tropes, novel_data,
                    progress_callback=progress_callback
                )
            except Exception as e:
                logger.error(f"[BatchGenerator] 对话模式失败: {e}，回退到独立模式")
        
        # 传统模式：每章独立调用
        if results is None:
            results = self._generate_batch_individual(
                novel_title, start_chapter, end_chapter,
                blueprint, tropes, novel_data,
                progress_callback=progress_callback
            )
        
        # 🔥 批次结束后自动修复缺失/损坏章节
        try:
            self._repair_missing_chapters_in_range(
                novel_title, start_chapter, end_chapter,
                blueprint, tropes, novel_data, results
            )
        except Exception as e:
            logger.error(f"[BatchGenerator] 自动修复缺失章节失败: {e}")
        
        return results
    
    def _should_stop(self) -> bool:
        """检查是否应该停止生成"""
        if self._stop_checker and self._stop_checker():
            logger.warning("[BatchGenerator] 检测到停止信号，准备停止生成")
            return True
        return False
    
    def _generate_batch_conversation(self, novel_title: str, start_chapter: int, end_chapter: int,
                                     blueprint: Dict, tropes: Dict, novel_data: Dict,
                                     progress_callback=None) -> Dict:
        """使用对话模式批量生成"""
        # 🔥 检查停止信号
        if self._should_stop():
            logger.warning(f"[BatchGenerator] 第{start_chapter}-{end_chapter}批开始前检测到停止信号")
            return {
                "generated": [],
                "failed": [],
                "total_words": 0,
                "avg_quality": 0,
                "generation_mode": "conversation",
                "stopped": True
            }
        
        logger.info(f"[BatchGenerator] 🚀 使用对话模式生成第{start_chapter}-{end_chapter}章")
        
        # 每批对话开始前重置 V2 状态更新标记
        self._v2_states_updated = False
        
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
        
        # 🔥 从战术规划预加载新角色（番茄细纲会话第3轮生成）
        if self.character_state_manager and blueprint:
            self._preload_characters_from_blueprint(blueprint)
        
        # 🔥 初始化世界状态管理器（如果是第一批）
        if self.world_state_manager and start_chapter <= 1:
            self.world_state_manager.initialize_from_novel_data(novel_data)
            logger.info(f"[BatchGenerator] {self.world_state_manager.get_summary()}")
        
        # 🔥 获取文风设置
        writing_style = novel_data.get('writing_style')
        if writing_style:
            logger.info(f"[BatchGenerator] 使用文风: {writing_style.get('name', '未命名')}")
        
        # 🔥 尝试读取战术规划，优先使用 V2 生成器
        use_v2 = False
        relevant_chapters = []
        if HAS_V2_GENERATOR and self.project_path:
            # 优先使用传入的 blueprint（调用方已经加载了正确的战术规划）
            chapters_plan = blueprint.get("chapters", []) if blueprint else []
            if chapters_plan:
                relevant_chapters = [
                    c for c in chapters_plan
                    if start_chapter <= c.get("chapter_number", 0) <= end_chapter
                ]
            
            # 如果 blueprint 中没有，再尝试从磁盘读取对应文件
            if not relevant_chapters:
                # 按批次找文件：tactical_plan_1.json, tactical_plan_31.json, tactical_plan_61.json...
                batch_start = ((start_chapter - 1) // 30) * 30 + 1
                tactical_plan_path = self.project_path / f"tactical_plan_{batch_start}.json"
                if not tactical_plan_path.exists() and batch_start != 1:
                    # 兜底1：尝试 tactical_plan_1.json
                    tactical_plan_path = self.project_path / "tactical_plan_1.json"
                
                # 兜底2：尝试精确匹配当前批次起始章（兼容续写场景的非对齐保存）
                if not tactical_plan_path.exists():
                    fallback_path = self.project_path / f"tactical_plan_{start_chapter}.json"
                    if fallback_path.exists():
                        tactical_plan_path = fallback_path
                
                if tactical_plan_path.exists():
                    try:
                        with open(tactical_plan_path, 'r', encoding='utf-8') as f:
                            tactical_data = json.load(f)
                        chapters_plan = tactical_data.get("chapters", [])
                        relevant_chapters = [
                            c for c in chapters_plan
                            if start_chapter <= c.get("chapter_number", 0) <= end_chapter
                        ]
                    except Exception as e:
                        logger.error(f"[BatchGenerator] 读取战术规划失败: {e}")
            
            if relevant_chapters:
                use_v2 = True
                logger.info(f"[BatchGenerator] 检测到战术规划，启用 V2 生成器 ({len(relevant_chapters)}章)")
            else:
                logger.warning(f"[BatchGenerator] 战术规划中无第{start_chapter}-{end_chapter}章数据，回退旧版")
        
        chapters = []
        if use_v2:
            # 🔥 V2 模式：基于战术规划逐章生成
            chapters = self._generate_with_v2(
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                novel_data=novel_data,
                relevant_chapters=relevant_chapters,
                progress_callback=progress_callback
            )
        else:
            # 🔥 旧版回退
            from web.services.market_driven.chapter_conversation_generator import (
                ChapterConversationGenerator
            )
            generator = ChapterConversationGenerator(
                api_client=self.api_client,
                novel_data=novel_data,
                tropes=tropes,
                world_state_manager=self.world_state_manager,
                project_path=str(self.project_path) if self.project_path else None,
                writing_style=writing_style
            )
            chapters = generator.generate_chapters(
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                blueprint=blueprint,
                progress_callback=progress_callback
            )
        
        # 处理结果
        results = {
            "generated": [],
            "failed": [],
            "total_words": 0,
            "avg_quality": 0,
            "generation_mode": "conversation_v2" if use_v2 else "conversation"
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
        # 如果 V2 对话内总结已经更新了状态（在 _generate_with_v2 中完成），则跳过旧的 _collect_batch_info
        v2_already_updated = (
            hasattr(self, '_v2_states_updated') and self._v2_states_updated and
            getattr(self, 'v2_last_batch_summary', None) is None  # 已被消费或已在 _generate_with_v2 中处理
        )
        if not v2_already_updated and self.character_state_manager and chapters:
            try:
                # 如果 V2 总结有 character_states，优先用它；否则 fallback 到旧逻辑
                if getattr(self, 'v2_last_batch_summary', None) and self.v2_last_batch_summary.get('character_states'):
                    self._update_states_from_v2_summary(
                        start_chapter, end_chapter, self.v2_last_batch_summary
                    )
                else:
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
    
    def _load_layer_1_4_bible(self, max_chars: int = 3000) -> Optional[str]:
        """如果存在 layer_1_4_core_settings.md，优先读取作为 Layer 1 核心设定"""
        if not self.project_path:
            return None
        bible_path = self.project_path / "layer_1_4_core_settings.md"
        if not bible_path.exists():
            return None
        try:
            with open(bible_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 裁剪：保留 Layer 1、Layer 3、Layer 4，去掉 Layer 2 战术规划索引（避免与每章具体战术冲突）
            filtered = self._filter_bible_layers(content)
            if len(filtered) > max_chars:
                filtered = filtered[:max_chars] + "\n...（核心设定已截断）"
            logger.info(f"[BatchGenerator] 已从圣经加载核心设定: {len(filtered)} 字符")
            return filtered
        except Exception as e:
            logger.warning(f"[BatchGenerator] 读取核心设定圣经失败: {e}")
            return None

    def _filter_bible_layers(self, content: str) -> str:
        """从 MD 中提取 Layer 1 + Layer 3 + Layer 4，去掉 Layer 2"""
        lines = content.splitlines()
        result = []
        skip_layer = None
        for line in lines:
            if line.startswith("## Layer 2:"):
                skip_layer = 2
                continue
            if line.startswith("## Layer 3:"):
                skip_layer = None
            if skip_layer is None:
                result.append(line)
        return "\n".join(result)

    def _format_core_setting_md(self, novel_data: Dict, character_state: Dict = None, world_state: Dict = None) -> str:
        """将核心设定格式化为结构化、叙事化的 Markdown（替代裸 JSON）"""
        nd = novel_data or {}
        cs = character_state or {}
        ws = world_state or {}
        lines = ["## 【Layer 1】核心设定"]
        
        # 辅助函数：安全取值
        def _get(d, *keys, default=''):
            for k in keys:
                if isinstance(d, dict) and k in d:
                    d = d[k]
                else:
                    return default
            return d if d is not None else default
        
        # 优先从 plan 和 novel_info 取高层信息
        plan = nd.get("plan", {}) if isinstance(nd.get("plan"), dict) else {}
        info = nd.get("novel_info", {}) if isinstance(nd.get("novel_info"), dict) else {}
        genre = nd.get("genre", "")
        synopsis = _get(info, 'synopsis') or _get(plan, 'synopsis') or _get(nd, 'storyline') or ""
        core_conflict = _get(plan, 'core_conflict') or _get(plan, 'main_conflict') or ""
        worldview_text = _get(plan, 'worldview') or ""
        
        # 1. 一句话钩子 + 核心卖点
        lines.extend([
            "",
            "### 核心卖点（写作时必须时刻对照）",
            f"- **一句话钩子**: {synopsis.split(chr(10))[0] if synopsis else '（待补充）'}",
            f"- **核心冲突**: {core_conflict or '（待补充）'}",
            f"- **题材定位**: {genre or '都市'}",
        ])
        
        # 2. 主角档案（合并 character_design / plan.protagonist / character_state）
        cd = nd.get("character_design", {}) if isinstance(nd.get("character_design"), dict) else {}
        protagonist_design = _get(cd, 'protagonist') or _get(cd, 'main_character') or _get(plan, 'protagonist') or _get(nd, 'protagonist') or {}
        protagonist_state = cs.get('protagonist', {}) if isinstance(cs, dict) else {}
        ws_protagonist = ws.get('protagonist', {}) if isinstance(ws, dict) else {}
        
        if isinstance(protagonist_design, dict) and protagonist_design:
            name = protagonist_design.get('name', '主角')
            bg = protagonist_design.get('background', '') or protagonist_design.get('surface_identity', '') or protagonist_design.get('identity', '')
            tags = protagonist_design.get('personality_tags', []) or protagonist_design.get('traits', []) or protagonist_state.get('traits', [])
            personality_desc = protagonist_design.get('personality_description', '')
            actions = protagonist_design.get('signature_actions', [])
            phrases = protagonist_design.get('catchphrases', [])
            motivation = protagonist_design.get('core_motivation', '') or protagonist_design.get('growth_arc', '')
            forbidden = protagonist_design.get('forbidden_behaviors', [])
            health = protagonist_state.get('health', '') or ws_protagonist.get('health', '')
            abilities = ws_protagonist.get('abilities_unlocked', []) or protagonist_state.get('abilities', [])
            location = ws_protagonist.get('current_location', '') or protagonist_state.get('location', '')
            lines.extend([
                "",
                f"### 主角档案 - {name}",
                f"- **姓名**: {name}",
            ])
            if bg:
                lines.append(f"- **表面身份/背景**: {bg}")
            if tags:
                lines.append(f"- **核心性格标签**: {', '.join([str(t) for t in tags])}（写作时必须时刻对照，严禁偏离）")
            if personality_desc:
                lines.append(f"- **性格画像**: {personality_desc}")
            if motivation:
                lines.append(f"- **核心动机/成长弧光**: {motivation}")
            if actions:
                lines.append(f"- **招牌动作**: {', '.join([str(a) for a in actions])}")
            if phrases:
                lines.append(f"- **口头禅**: {', '.join([str(p) for p in phrases])}")
            if forbidden:
                lines.append(f"- **绝对禁止行为**: {', '.join([str(f) for f in forbidden])}")
            if health:
                lines.append(f"- **当前健康状态**: {health}")
            if location:
                lines.append(f"- **当前位置**: {location}")
            if abilities:
                lines.append(f"- **已解锁能力**: {', '.join([str(a) for a in abilities])}")
        
        # 3. 金手指 / 系统（优先 world_state.system_rules，其次 novel_data.golden_finger）
        sr = ws.get('system_rules', {}) if isinstance(ws, dict) else {}
        gf = nd.get("golden_finger", {}) if isinstance(nd.get("golden_finger"), dict) else {}
        
        gf_name = sr.get('system_name', '') or gf.get('name', '') or gf.get('system_name', '')
        mechanism = gf.get('core_mechanism', '') or gf.get('mechanism', '') or gf.get('description', '')
        level = sr.get('current_level', '') or gf.get('current_level', '')
        ability = sr.get('current_power', '') or gf.get('current_ability', '')
        growth = gf.get('growth_path', [])
        limits = gf.get('limitations', [])
        reward_sound = gf.get('reward_sound', '')
        synergy = gf.get('protagonist_synergy', {}) if isinstance(gf.get('protagonist_synergy'), dict) else {}
        plot_role = gf.get('plot_role', {}) if isinstance(gf.get('plot_role'), dict) else {}
        unlocked = sr.get('unlocked_abilities', []) or sr.get('unlocked_skills', []) or []
        
        if gf_name or mechanism or level or unlocked:
            lines.extend([
                "",
                f"### 金手指 / 系统{' - ' + str(gf_name) if gf_name else ''}",
            ])
            if mechanism:
                lines.append(f"- **核心机制**: {mechanism}")
            if level or ability:
                lines.append(f"- **当前等级/能力边界**: {level or '未知'} | {ability or '未知'}")
            if unlocked:
                lines.append(f"- **当前已解锁能力**: {', '.join([str(u) for u in unlocked])}")
            if growth:
                lines.append(f"- **升级路径**: {' → '.join([str(g) for g in growth])}")
            if limits:
                lines.append(f"- **限制条件**: {', '.join([str(l) for l in limits])}")
            if synergy and synergy.get('compatibility'):
                lines.append(f"- **主角契合度**: {synergy['compatibility']}")
            if plot_role and plot_role.get('twist_potential'):
                lines.append(f"- **剧情爆点潜力**: {plot_role['twist_potential']}")
            if reward_sound:
                lines.append(f"- **系统提示音规范**: {reward_sound}（必须在对应爽点后按此格式插入）")
            else:
                lines.append("- **系统提示音规范**: 【叮！神级万倍返现系统激活！】（必须在主角获得返利/奖励时插入）")
        
        # 4. 叙事世界观
        worldview = nd.get("core_worldview", {}) if isinstance(nd.get("core_worldview"), dict) else {}
        wo = _get(worldview, 'world_overview') if isinstance(_get(worldview, 'world_overview'), dict) else {}
        era = wo.get('era', '') or ''
        background = wo.get('background', '') or worldview_text or ''
        main_conflict = wo.get('main_conflict', '') or core_conflict or ''
        
        lines.extend([
            "",
            "### 叙事世界观",
        ])
        if era:
            lines.append(f"- **时代背景**: {era}")
        if background:
            lines.append(f"- **世界背景**: {background}")
        if main_conflict:
            lines.append(f"- **主要冲突**: {main_conflict}")
        
        # 社会阶层
        ss = worldview.get("social_structure", {}) if isinstance(worldview.get("social_structure"), dict) else {}
        if ss:
            parts = [f"{k}={v}" for k, v in ss.items()]
            lines.append(f"- **社会阶层**: {'; '.join(parts)}")
        
        # 势力
        factions = worldview.get("factions", []) if isinstance(worldview.get("factions"), list) else []
        if factions:
            faction_parts = []
            for f in factions:
                if isinstance(f, dict):
                    faction_parts.append(f"{f.get('name', '未知')}({f.get('type', '未知')}): {f.get('description', '')}")
            if faction_parts:
                lines.append(f"- **势力格局**: {'; '.join(faction_parts)}")
        
        # 世界规则
        rules = worldview.get("world_rules", []) if isinstance(worldview.get("world_rules"), list) else []
        if rules:
            lines.append("- **世界规则（不可违背）**:")
            for rule in rules:
                lines.append(f"  - {rule}")
        
        # 力量体系
        ps = worldview.get("power_system", {}) if isinstance(worldview.get("power_system"), dict) else {}
        if ps:
            ps_name = ps.get('name', '')
            levels = ps.get("levels", [])
            mechanics = ps.get("mechanics", {}) if isinstance(ps.get("mechanics"), dict) else {}
            core_rules = mechanics.get("core_rules", [])
            limitations = mechanics.get("limitations", [])
            if ps_name or levels or core_rules:
                lines.append(f"- **力量体系{' - ' + str(ps_name) if ps_name else ''}**:")
                if levels:
                    lines.append(f"  - 等级: {' → '.join([str(l) for l in levels])}")
                for rule in core_rules:
                    lines.append(f"  - 规则: {rule}")
                for lim in limitations:
                    lines.append(f"  - 限制: {lim}")
        
        # 神豪专属
        if worldview.get("shen_lang_exclusive"):
            lines.append(f"- **神豪专属设定**: {worldview['shen_lang_exclusive']}")
        
        # 5. 关键地点与符号
        locations = worldview.get("key_locations", []) if isinstance(worldview.get("key_locations"), list) else []
        if locations:
            lines.extend(["", "### 关键地点与符号"])
            for loc in locations:
                if isinstance(loc, dict):
                    loc_name = loc.get('name', '未知')
                    loc_desc = loc.get('description', '')
                    loc_pos = loc.get('location', '')
                    symbol = loc.get('symbolism', '')
                    s = f"- **{loc_name}**"
                    if loc_pos:
                        s += f" ({loc_pos})"
                    s += f": {loc_desc}"
                    if symbol:
                        s += f" [象征意义: {symbol}]"
                    lines.append(s)
        
        # 6. 开篇锚点（如果 plan 里有 opening_design，提供给第1章附近参照）
        opening = plan.get("opening_design", {}) if isinstance(plan.get("opening_design"), dict) else {}
        if opening:
            lines.extend([
                "",
                "### 开篇锚点（第1章附近必须严格遵循）",
                f"- **场景**: {_get(opening, 'scene')}",
                f"- **触发动作**: {_get(opening, 'action')}",
            ])
            dialogues = opening.get("dialogue", [])
            if dialogues:
                lines.append(f"- **关键对话（可直接化用）**:")
                for d in dialogues:
                    lines.append(f"  - \"{d}\"")
            if opening.get("hook"):
                lines.append(f"- **开篇钩子**: {opening['hook']}")
        
        return "\n".join(lines)
    
    def _format_assigned_characters_md(self, assigned_chars: Dict, character_state: Dict, world_state: Dict, novel_data: Dict = None) -> str:
        """根据战术规划中的出场角色名单，从状态文件+角色设计中提取详细档案"""
        if not assigned_chars:
            return ""
        
        cs = character_state or {}
        ws = world_state or {}
        nd = novel_data or {}
        cd = nd.get("character_design", {}) if isinstance(nd.get("character_design"), dict) else {}
        
        # 构建角色查找表（来自状态文件）
        char_lookup = {}
        # 主角
        protagonist = cs.get('protagonist', {})
        if protagonist and protagonist.get('name'):
            char_lookup[protagonist['name']] = ('主角', protagonist)
        # 盟友
        for name, data in cs.get('allies', {}).items():
            char_lookup[name] = ('盟友', data)
        # 敌人
        for name, data in cs.get('enemies', {}).items():
            char_lookup[name] = ('敌人', data)
        # 中立
        for name, data in cs.get('neutral', {}).items():
            char_lookup[name] = ('中立', data)
        
        # 构建辅助查找表（来自 character_design / plan）
        design_lookup = {}
        # 主角信息
        if isinstance(cd, dict) and cd.get('protagonist'):
            p = cd['protagonist']
            design_lookup[p.get('name', '')] = ('主角', p)
            if p.get('ex_girlfriend'):
                design_lookup[p['ex_girlfriend']] = ('前女友/反派', {'description': '主角的前女友，拜金势利'})
        # 盟友
        if isinstance(cd, dict) and cd.get('core_allies'):
            for ally in cd['core_allies']:
                if isinstance(ally, dict) and ally.get('name'):
                    design_lookup[ally['name']] = ('盟友', ally)
        # 敌人（按阶段）
        if isinstance(cd, dict) and cd.get('main_antagonists'):
            for stage, enemies in cd['main_antagonists'].items():
                if isinstance(enemies, list):
                    for e in enemies:
                        if isinstance(e, dict) and e.get('name'):
                            design_lookup[e['name']] = ('敌人', e)
        # plan 中的角色
        plan = nd.get('plan', {}) if isinstance(nd.get('plan'), dict) else {}
        if isinstance(plan, dict) and plan.get('protagonist'):
            p = plan['protagonist']
            if isinstance(p, dict) and p.get('name'):
                design_lookup[p['name']] = ('主角', p)
        
        # 通用群体/功能角色映射
        generic_roles = {
            '全网网友': '舆论群体',
            '网友': '舆论群体',
            '路人': '围观群众',
            '群众': '围观群众',
            '围观群众': '围观群众',
            '保安': '服务人员',
            '服务员': '服务人员',
            '经理': '服务人员',
            '销售员': '服务人员',
            '店员': '服务人员',
            '主播': '职业角色',
            '女主播': '职业角色',
            '富二代': '反派群体',
            '豪门公子': '反派群体',
            '前女友': '情感反派',
            '前任': '情感反派',
        }
        
        # world_state 中补充主角和盟友状态
        ws_protagonist = ws.get('protagonist', {})
        ws_allies = ws.get('allies', {})
        
        lines = ["", "### 本章出场角色档案（必须严格对照，禁止随意更改人设）"]
        
        for role_type in ['core', 'major', 'minor']:
            names = assigned_chars.get(role_type, [])
            type_label = {'core': '核心角色', 'major': '重要角色', 'minor': '次要角色'}.get(role_type, role_type)
            for name in names:
                role, data = char_lookup.get(name, (None, None))
                
                # 状态文件没找到，尝试 character_design / plan 兜底
                if role is None:
                    role, data = design_lookup.get(name, (None, None))
                
                # 还是没找到，检查是否是通用群体/功能角色
                if role is None:
                    mapped_role = generic_roles.get(name)
                    if mapped_role:
                        role = mapped_role
                        data = {'description': f'本章出现的{name}群体/角色'}
                    else:
                        # 模糊匹配：在 design_lookup 中搜索 role/description 包含 name
                        for d_name, (d_role, d_data) in design_lookup.items():
                            if name in d_name or name in str(d_data.get('role', '')) or name in str(d_data.get('description', '')):
                                role = d_role
                                data = d_data
                                break
                
                if role is None:
                    role = '未知'
                    data = {}
                
                # 尝试从 world_state 补全状态
                ws_data = {}
                if name == ws_protagonist.get('name'):
                    ws_data = ws_protagonist
                elif name in ws_allies:
                    ws_data = ws_allies[name]
                
                health = ws_data.get('health', '') or (data.get('health', '') if isinstance(data, dict) else '')
                abilities = ws_data.get('abilities_unlocked', []) or (data.get('abilities', []) if isinstance(data, dict) else [])
                traits = data.get('traits', []) if isinstance(data, dict) else []
                location = ws_data.get('current_location', '') or (data.get('location', '') if isinstance(data, dict) else '')
                description = data.get('description', '') if isinstance(data, dict) else ''
                
                parts = [f"- **{name}** ({type_label}/{role})"]
                details = []
                if health:
                    details.append(f"健康={health}")
                if location:
                    details.append(f"位置={location}")
                if traits:
                    details.append(f"性格={', '.join([str(t) for t in traits])}")
                if abilities:
                    details.append(f"能力={', '.join([str(a) for a in abilities])}")
                if description:
                    details.append(f"简介={description}")
                if details:
                    parts.append(" | ".join(details))
                lines.append(" ".join(parts))
        
        return "\n".join(lines)
    
    def _format_tactical_planning_summary_md(self, chapters: List[Dict]) -> str:
        """将战术规划格式化为极简批次标识（用于 Layer 2 System Prompt，避免未来视）"""
        if not chapters:
            return "## 【Layer 2】战术规划\n当前批次信息待补充"
        nums = [c.get("chapter_number", 0) for c in chapters if c.get("chapter_number")]
        start = min(nums) if nums else 0
        end = max(nums) if nums else 0
        return f"## 【Layer 2】战术规划\n当前生成批次涵盖第 {start}-{end} 章。详细战术指令将在每章 User Prompt 中动态注入。"
    
    def _format_tactical_planning_md(self, chapters: List[Dict]) -> str:
        """将战术规划格式化为结构化 Markdown（替代裸 JSON）"""
        lines = ["## 【Layer 2】战术规划"]
        for ch in chapters:
            ch_num = ch.get("chapter_number", 0)
            emotion = ch.get("emotion", "待定")
            intensity = ch.get("intensity", 5)
            beat = ch.get("beat_type", "普通章")
            event = ch.get("event", "")
            hook = ch.get("hook_content", "")
            lines.append("")
            lines.append(f"### 第{ch_num}章 ({beat} | {emotion} 强度{intensity})")
            lines.append(f"**事件**: {event}")
            if hook:
                lines.append(f"**钩子**: {hook}")
            sp = ch.get("satisfaction_point")
            if sp:
                lines.append(f"**爽点**: {sp}")
            fp = ch.get("face_slapping")
            if fp:
                lines.append(f"**打脸**: {fp}")
        return "\n".join(lines)
    
    def _generate_with_v2(self, start_chapter: int, end_chapter: int,
                          novel_data: Dict, relevant_chapters: List[Dict],
                          progress_callback=None) -> List[Dict]:
        """使用 V2 架构基于战术规划逐章生成"""
        # 🔥 补全 novel_data：如果关键字段缺失，尝试从 project_info.json 读取
        enriched_novel_data = dict(novel_data) if novel_data else {}
        if self.project_path:
            project_info_path = self.project_path / "project_info.json"
            if project_info_path.exists():
                try:
                    with open(project_info_path, 'r', encoding='utf-8') as f:
                        project_info = json.load(f)
                    # 兼容 mode_specific 的两种嵌套位置
                    mode_specific = project_info.get('mode_specific') or {}
                    if not mode_specific and isinstance(project_info.get('generation_metadata'), dict):
                        mode_specific = project_info['generation_metadata'].get('mode_specific') or {}
                    mode_info = mode_specific.get('info', {}) if isinstance(mode_specific, dict) else {}
                    plan_from_info = mode_info.get('plan', {}) if isinstance(mode_info, dict) else {}
                    
                    # 从 mode_info 取深层数据（优先），顶层做 fallback
                    char_design = mode_info.get('character_design') or project_info.get('character_design', {})
                    golden_finger = mode_info.get('golden_finger') or project_info.get('golden_finger', {})
                    core_worldview = mode_info.get('core_worldview') or project_info.get('core_worldview', {})
                    
                    # 只补全缺失的字段
                    if not enriched_novel_data.get('plan'):
                        enriched_novel_data['plan'] = plan_from_info
                    if not enriched_novel_data.get('novel_info'):
                        enriched_novel_data['novel_info'] = {
                            'title': project_info.get('novel_title', ''),
                            'synopsis': project_info.get('novel_synopsis', ''),
                            'selected_plan': plan_from_info,
                        }
                    if not enriched_novel_data.get('character_design'):
                        enriched_novel_data['character_design'] = char_design
                    if not enriched_novel_data.get('golden_finger'):
                        enriched_novel_data['golden_finger'] = golden_finger
                    if not enriched_novel_data.get('core_worldview'):
                        enriched_novel_data['core_worldview'] = core_worldview
                    if not enriched_novel_data.get('writing_style'):
                        enriched_novel_data['writing_style'] = project_info.get('writing_style', {})
                    if not enriched_novel_data.get('genre'):
                        enriched_novel_data['genre'] = project_info.get('genre', '') or mode_info.get('genre', '')
                except Exception as e:
                    logger.warning(f"[BatchGenerator] 读取 project_info.json 补全 novel_data 失败: {e}")
        
        # 🔥 读取角色状态和世界状态文件
        character_state = {}
        world_state = {}
        if self.project_path:
            cs_path = self.project_path / ".character_state.json"
            if cs_path.exists():
                try:
                    with open(cs_path, 'r', encoding='utf-8') as f:
                        character_state = json.load(f)
                except Exception as e:
                    logger.warning(f"[BatchGenerator] 读取 .character_state.json 失败: {e}")
            ws_path = self.project_path / ".world_state.json"
            if ws_path.exists():
                try:
                    with open(ws_path, 'r', encoding='utf-8') as f:
                        world_state = json.load(f)
                except Exception as e:
                    logger.warning(f"[BatchGenerator] 读取 .world_state.json 失败: {e}")
        
        # 构建 Layer1 核心设定：优先读取圣经 MD，fallback 到旧 JSON 格式化逻辑
        core_setting = self._load_layer_1_4_bible(max_chars=3500)
        if core_setting is None:
            logger.info("[BatchGenerator] 未找到核心设定圣经，fallback 到 JSON 格式化逻辑")
            core_setting = self._format_core_setting_md(enriched_novel_data, character_state, world_state)
        
        # 构建 Layer2 战术规划（仅当前批次摘要，防止未来视）
        tactical_planning = self._format_tactical_planning_summary_md(relevant_chapters)
        
        # Genre 健壮性兜底
        genre = enriched_novel_data.get("genre")
        if not genre or not str(genre).strip():
            title = enriched_novel_data.get("title", "")
            synopsis = ""
            plan = enriched_novel_data.get("plan", {})
            if isinstance(plan, dict):
                synopsis = plan.get("synopsis", "")
            if not synopsis:
                info = enriched_novel_data.get("novel_info", {})
                if isinstance(info, dict):
                    synopsis = info.get("synopsis", "")
            combined = f"{title} {synopsis}"
            if any(k in combined for k in ["返利","神豪","签到","百倍","花钱","返现","万倍","消费","首富"]):
                genre = "god-tier-spending"
            elif any(k in combined for k in ["国运","禁地","扮演","直播","国战","怪谈","诡异"]):
                genre = "nation-live"
            else:
                genre = "都市"
            logger.info(f"[BatchGenerator] Genre 为空，已自动推断为: {genre}")
        
        # 🔥 提取文风设置（从 enriched_novel_data 读取）
        writing_style = enriched_novel_data.get('writing_style')
        if writing_style:
            logger.info(f"[BatchGenerator] V2生成器使用文风: {writing_style.get('name', '未命名')}")
        
        generator = ChapterConversationV2(
            api_client=self.api_client,
            genre=genre,
            core_setting=core_setting,
            tactical_planning=tactical_planning,
            provider='kimi',
            writing_style=writing_style
        )
        
        # 🔥 读取跨批次总结（如果有的话），作为上下文注入
        cross_batch_context = ""
        if self.project_path:
            latest_summary_path = self.project_path / "batch_summary_latest.json"
            if latest_summary_path.exists():
                try:
                    with open(latest_summary_path, "r", encoding="utf-8") as f:
                        latest_data = json.load(f)
                    summary = latest_data.get("summary", {})
                    completed = summary.get("completed_events", [])
                    pending = summary.get("pending_hooks", [])
                    direction = summary.get("plot_direction", "")
                    if completed or pending:
                        cross_batch_context = f"""### 上一批次剧情状态（本章必须承接，禁止重启剧情）
□ 已完成关键事件：{'; '.join([e.get('event','') for e in completed[:5] if e.get('event')]) or '无'}
□ 待解决钩子：{'; '.join([h.get('content','') for h in pending[:5] if h.get('content')]) or '无'}
□ 后续剧情方向：{direction or '继续推进当前阶段目标'}
"""
                        logger.info(f"[BatchGenerator] 已加载跨批次总结: 已完成{len(completed)}件, 待解决钩子{len(pending)}个")
                except Exception as e:
                    logger.warning(f"[BatchGenerator] 读取跨批次总结失败: {e}")
            
            # 追加剧情线索（从 world_state）
            plot_threads = world_state.get("plot_threads", {})
            if plot_threads:
                thread_lines = []
                for t_name, t_info in plot_threads.items():
                    if not isinstance(t_info, dict):
                        continue
                    status = t_info.get("status", "")
                    if status in ["active", "paused"]:
                        desc = t_info.get("description", "")
                        next_trigger = t_info.get("next_trigger", "")
                        priority = t_info.get("priority", 0)
                        thread_lines.append(f"□ [{t_name}] 状态={status} 优先级={priority} | {desc} | 下次触发: {next_trigger}")
                if thread_lines:
                    cross_batch_context += "\n### 当前剧情线索（必须承接或埋设）\n" + "\n".join(thread_lines) + "\n"
        
        chapters = []
        for chapter_num in range(start_chapter, end_chapter + 1):
            chapter_plan = next(
                (c for c in relevant_chapters if c.get("chapter_number") == chapter_num), None
            )
            if not chapter_plan:
                logger.warning(f"[BatchGenerator] 第{chapter_num}章无战术规划，跳过")
                chapters.append({
                    "chapter_number": chapter_num,
                    "title": "",
                    "content": "",
                    "word_count": 0,
                    "quality_score": 0.0,
                    "extracted_info": {},
                    "error": "无战术规划"
                })
                continue
            
            # 🔥 构建战术规划执行自检清单
            assigned_chars = chapter_plan.get("assigned_characters", {})
            core_chars = ", ".join(assigned_chars.get("core", [])) or "主角"
            major_chars = ", ".join(assigned_chars.get("major", [])) or "无"
            minor_chars = ", ".join(assigned_chars.get("minor", [])) or "无"
            
            # 动态注入出场角色详细档案
            character_context = self._format_assigned_characters_md(assigned_chars, character_state, world_state, enriched_novel_data)
            
            custom_selfcheck = f"""### 战术规划执行自检清单（输出前必须逐项确认）
{character_context}
{cross_batch_context}
□ **人物名字一致性**：本章出现的所有有名角色必须严格等于以下名单，禁止发明新名字——核心角色：[{core_chars}]；重要角色：[{major_chars}]；次要角色：[{minor_chars}]
□ **事件对齐**：本章核心情节必须围绕"{chapter_plan.get('event', '')}"展开，不能偏离到无关场景
□ **情绪对齐**：本章整体情绪必须是"{chapter_plan.get('emotion', '期待')}"(强度{chapter_plan.get('intensity', 5)})，正文情绪走向必须与该设定一致
□ **钩子落实**：章尾必须留有与"{chapter_plan.get('hook_content', '')}"对应的悬念/钩子，且位于章节最后50字内
□ **爽点对齐**：如果本章规划有爽点("{chapter_plan.get('satisfaction_point', '无')}")，正文中必须有明确的打脸/收获/反转交付
□ **金手指/能力合规**：本章主角使用的系统能力或消费金额必须符合当前阶段设定，严禁提前使用后期才解锁的能力或社会关系
□ **人设不崩**：主角行为必须符合其性格标签（冷静果断、不圣母等），禁止出现降智、冲动、圣母行为
□ **格式合规**：字数必须严格控制在2000-2500字之间，绝对禁止超过2500字；段落不超过3行，适合手机阅读
□ **字数超限处罚**：如果输出超过2500字，系统会自动判定为不合格并拒绝接收，你必须在生成过程中主动压缩场景和描写
□ **结尾硬切断**：本章最后 50 字内必须是且只能是钩子，钩子出现后禁止有任何后续场景、对话、解释或心理描写
□ **禁止滑翔**：人物在钩子触发时必须停留在当前位置，禁止进入新房间、上车、展开新剧情
□ **元文本禁令**：绝对禁止出现「下一章预告」「本章完」「未完待续」等字样
□ **字数急救**：如果内容超过 2300 字，必须主动删除环境描写和重复震惊，确保最终输出≤2500 字
"""
            
            # 获取上一章战术规划（用于承接）
            prev_chapter_plan = None
            if chapter_num > start_chapter:
                prev_chapter_plan = next(
                    (c for c in relevant_chapters if c.get("chapter_number") == chapter_num - 1), None
                )
            
            # 获取下一章战术规划（用于预埋钩子）
            next_chapter_plan = None
            next_chapter_plan = next(
                (c for c in relevant_chapters if c.get("chapter_number") == chapter_num + 1), None
            )
            
            try:
                content = generator.generate_chapter(
                    chapter_number=chapter_num,
                    chapter_title="",  # 标题由AI生成，不预传
                    outline_summary=chapter_plan.get("event", ""),
                    chapter_type=chapter_plan.get("beat_type", "普通章"),
                    emotion_config={
                        "emotion": chapter_plan.get("emotion", "期待"),
                        "intensity": chapter_plan.get("intensity", 5),
                        "emotion_type": chapter_plan.get("emotion_type", "")
                    },
                    custom_selfcheck=custom_selfcheck,
                    current_plan=chapter_plan,
                    prev_plan=prev_chapter_plan,
                    next_plan=next_chapter_plan
                )
                
                if content and isinstance(content, str) and len(content) > 100:
                    parsed = self._parse_response(content)
                    ai_title = parsed.get('title', '')
                    clean_content = parsed.get('content', content)
                    
                    # 🔥 清理超长章节中的拼接/重复问题
                    clean_content = self._sanitize_chapter_content(clean_content)
                    
                    # 标题兜底：标准格式未返回title时，单独补生成
                    if not ai_title and clean_content:
                        ai_title = self._generate_title_from_content(clean_content)
                    if not ai_title:
                        ai_title = self._extract_title(clean_content)
                    final_title = self._ensure_unique_title(ai_title)
                    
                    # 🔥 修复：从 chapter_plan 中提取结构化信息，不再传空字典
                    extracted_info = {
                        "key_event": {
                            "event": chapter_plan.get("event", ""),
                            "chapter": chapter_num
                        },
                        "new_characters": [
                            {"name": name, "role": "core"} for name in assigned_chars.get("core", [])
                        ] + [
                            {"name": name, "role": "major"} for name in assigned_chars.get("major", [])
                        ] + [
                            {"name": name, "role": "minor"} for name in assigned_chars.get("minor", [])
                        ],
                        "new_hooks": [chapter_plan.get("hook_content", "")] if chapter_plan.get("hook_content") else [],
                        "character_changes": []
                    }
                    chapters.append({
                        "chapter_number": chapter_num,
                        "title": final_title,
                        "content": clean_content,
                        "word_count": len(clean_content),
                        "quality_score": 8.0,
                        "extracted_info": extracted_info
                    })
                    logger.info(f"[BatchGenerator] V2 生成第{chapter_num}章成功 ({len(content)}字)")
                else:
                    logger.error(f"[BatchGenerator] V2 生成第{chapter_num}章内容异常，标记失败")
                    chapters.append({
                        "chapter_number": chapter_num,
                        "title": "",
                        "content": "",
                        "word_count": 0,
                        "quality_score": 0.0,
                        "extracted_info": {},
                        "error": "V2 生成内容异常"
                    })
            except Exception as e:
                logger.error(f"[BatchGenerator] V2 生成第{chapter_num}章失败: {e}")
                chapters.append({
                    "chapter_number": chapter_num,
                    "title": "",
                    "content": "",
                    "word_count": 0,
                    "quality_score": 0.0,
                    "extracted_info": {},
                    "error": str(e)
                })
            
            if progress_callback:
                try:
                    progress_callback(chapter_num, end_chapter - start_chapter + 1, chapters[-1] if chapters else None)
                except Exception as cb_err:
                    logger.warning(f"[BatchGenerator] V2 进度回调失败: {cb_err}")
        
        # 🔥 在对话中生成批次总结（利用完整对话记忆）
        if chapters and any(c.get("word_count", 0) > 0 for c in chapters):
            try:
                logger.info(f"[BatchGenerator] V2 对话内生成批次总结: 第{start_chapter}-{end_chapter}章")
                summary_response = generator.generate_batch_summary(start_chapter, end_chapter)
                if summary_response:
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', str(summary_response))
                    if json_match:
                        try:
                            self.v2_last_batch_summary = json.loads(json_match.group())
                            logger.info(f"[BatchGenerator] V2 对话内总结解析成功")
                        except Exception as parse_err:
                            logger.warning(f"[BatchGenerator] V2 对话内总结解析失败: {parse_err}，尝试重试")
                            # fallback：重新调用一次 V2 批次总结
                            retry_response = generator.generate_batch_summary(start_chapter, end_chapter)
                            if retry_response:
                                retry_match = re.search(r'\{[\s\S]*\}', str(retry_response))
                                if retry_match:
                                    try:
                                        self.v2_last_batch_summary = json.loads(retry_match.group())
                                        logger.info(f"[BatchGenerator] V2 对话内总结重试解析成功")
                                    except Exception:
                                        self.v2_last_batch_summary = {"summary_text": str(retry_response)[:200]}
                                else:
                                    self.v2_last_batch_summary = {"summary_text": str(retry_response)[:200]}
                            else:
                                self.v2_last_batch_summary = {"summary_text": str(summary_response)[:200]}
                    else:
                        self.v2_last_batch_summary = {"summary_text": str(summary_response)[:200]}
                else:
                    self.v2_last_batch_summary = None
            except Exception as e:
                logger.error(f"[BatchGenerator] V2 对话内总结生成异常: {e}")
                self.v2_last_batch_summary = None
            
            # 🔥 关键新增：直接用 V2 对话内总结更新角色状态和世界状态
            if self.v2_last_batch_summary:
                try:
                    self._update_states_from_v2_summary(
                        start_chapter, end_chapter, self.v2_last_batch_summary
                    )
                    self._v2_states_updated = True
                except Exception as state_err:
                    logger.error(f"[BatchGenerator] V2 总结更新状态失败: {state_err}")
                    self._v2_states_updated = False
        
        return chapters
    
    def _update_states_from_v2_summary(self, start_chapter: int, end_chapter: int, v2_summary: Dict):
        """
        根据 V2 对话内批次总结直接更新角色状态和世界状态
        """
        char_states = v2_summary.get("character_states", {})
        
        # 1. 更新角色状态
        if self.character_state_manager:
            batch_info = {
                "chapter_start": start_chapter,
                "chapter_end": end_chapter,
                "new_characters": char_states.get("new_characters", []),
                "character_changes": char_states.get("character_changes", [])
            }
            self.character_state_manager.update_after_batch(batch_info)
            self.character_state_manager.sync_to_world_state()
            logger.info(f"[BatchGenerator] V2 总结已更新角色状态并同步到 world_state")
        
        # 2. 更新世界状态（直接读写 .world_state.json）
        if self.project_path:
            import json
            ws_path = self.project_path / ".world_state.json"
            world_state = {}
            if ws_path.exists():
                try:
                    with open(ws_path, "r", encoding="utf-8") as f:
                        world_state = json.load(f)
                except Exception:
                    world_state = {}
            
            # 安全默认值
            if "protagonist" not in world_state:
                world_state["protagonist"] = {"name": "", "health": "健康", "injuries": [], "abilities_unlocked": [], "current_location": "", "relationships": {}}
            if "allies" not in world_state:
                world_state["allies"] = {}
            if "enemies" not in world_state:
                world_state["enemies"] = {}
            if "plot_threads" not in world_state:
                world_state["plot_threads"] = {}
            if "system_rules" not in world_state:
                world_state["system_rules"] = {"current_playing_degree": 0.0, "max_playing_degree": 0.0, "cooldown_end_chapter": 0, "special_states": [], "unlocked_skills": []}
            if "important_items" not in world_state:
                world_state["important_items"] = []
            if "global_events" not in world_state:
                world_state["global_events"] = []
            
            # 合并 world_changes
            for change in v2_summary.get("world_changes", []):
                change_type = change.get("type", "")
                if change_type == "力量体系":
                    # 更新 system_rules
                    desc = change.get("description", "")
                    # 简单启发式：如果描述里提到等级/LV，更新 current_level
                    import re
                    lv_match = re.search(r'LV\.(\d+)|等级提升至(\d+)|提升至LV(\d+)|升级到(\d+)', desc, re.IGNORECASE)
                    if lv_match:
                        lv = next((g for g in lv_match.groups() if g is not None), None)
                        if lv:
                            world_state["system_rules"]["current_level"] = f"LV{lv}"
                    # 更新解锁技能
                    if "new_abilities" in change:
                        for ability in change["new_abilities"]:
                            if ability not in world_state["system_rules"].get("unlocked_skills", []):
                                world_state["system_rules"].setdefault("unlocked_skills", []).append(ability)
                elif change_type == "道具":
                    item = change.get("description", "")
                    if item and item not in world_state.get("important_items", []):
                        world_state.setdefault("important_items", []).append(item)
                elif change_type == "势力":
                    world_state.setdefault("global_events", []).append({
                        "chapter": change.get("chapter", end_chapter),
                        "title": change.get("description", "")[:20],
                        "description": change.get("description", ""),
                        "impact": "high"
                    })
                
                world_state.setdefault("global_events", []).append({
                    "chapter": change.get("chapter", end_chapter),
                    "title": change.get("description", "")[:20],
                    "description": change.get("description", ""),
                    "impact": "medium"
                })
            
            # 同步扮演度
            protagonist = char_states.get("protagonist", {})
            if protagonist and protagonist.get("playing_degree"):
                world_state["protagonist"]["playing_degree"] = protagonist["playing_degree"]
            
            # 保存
            with open(ws_path, "w", encoding="utf-8") as f:
                json.dump(world_state, f, ensure_ascii=False, indent=2)
            logger.info(f"[BatchGenerator] V2 总结已更新 .world_state.json")
    
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
            
            # 🔥 优先使用 V2 对话内生成的总结（有完整对话记忆）
            if hasattr(self, 'v2_last_batch_summary') and self.v2_last_batch_summary:
                logger.info("[BatchGenerator] 使用 V2 对话内生成的批次总结（含完整记忆）")
                new_summary = self.v2_last_batch_summary
                # 清空，避免重复使用
                self.v2_last_batch_summary = None
            else:
                # 不再回退到旧版独立总结器（它无法利用对话记忆，且格式与 V2 不一致）
                logger.warning("[BatchGenerator] V2 对话内总结不可用，使用空总结")
                new_summary = {"notes": "V2总结未生成", "chapter_count": len(chapters)}
            
            # 🔥 防御：确保 new_summary 不为 None
            if new_summary is None:
                logger.warning("[BatchGenerator] 总结返回 None，使用空总结")
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
                                   blueprint: Dict, tropes: Dict, novel_data: Dict,
                                   progress_callback=None) -> Dict:
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

                # 🔥 进度回调
                if progress_callback:
                    try:
                        progress_callback(chapter_num, end_chapter - start_chapter + 1, chapter)
                    except Exception as cb_err:
                        logger.warning(f"[BatchGenerator] 进度回调失败: {cb_err}")

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
        """生成单章，强制标准格式，失败则补标题并保证唯一性"""
        chapter_plan = self._get_chapter_plan(chapter_num, blueprint)
        context = self._build_chapter_context(chapter_num, novel_title, novel_data)
        prompt = self._build_chapter_prompt(
            chapter_num=chapter_num,
            chapter_plan=chapter_plan,
            context=context,
            novel_data=novel_data,
            tropes=tropes
        )
        
        if self.api_client:
            parsed_response = self._call_ai_generation(prompt, chapter_num)
            ai_title = parsed_response.get('title', '')
            content = parsed_response.get('content', '')
        else:
            content = self._mock_chapter_content(chapter_num, chapter_plan)
            ai_title = ''
        
        # 确保 content 有效
        content_str = content if isinstance(content, str) else str(content) if content else ""
        
        # 🔥 清理超长章节中的拼接/重复问题
        content_str = self._sanitize_chapter_content(content_str)
        
        # 标题兜底：如果没标题但有正文，单独补生成
        if not ai_title and content_str and len(content_str) > 100:
            ai_title = self._generate_title_from_content(content_str)
        
        # 确保唯一性
        final_title = self._ensure_unique_title(ai_title)
        
        # 质量评估
        quality_score = self._assess_chapter_quality(content_str, chapter_plan, tropes)
        if quality_score < 7.0:
            logger.warning(f"  第{chapter_num}章质量偏低({quality_score})，尝试优化...")
            content_str = self._optimize_chapter(content_str, chapter_plan, tropes)
            quality_score = self._assess_chapter_quality(content_str, chapter_plan, tropes)
        
        return {
            "chapter_number": chapter_num,
            "title": final_title,
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
        character_design = novel_data.get('character_design', {})
        
        # 🔥 调试日志：记录接收到的 character_design
        logger.info(f"[BatchChapterGenerator] 接收到的 character_design 类型: {type(character_design)}")
        if isinstance(character_design, dict):
            logger.info(f"[BatchChapterGenerator] 接收到的 character_design 键: {list(character_design.keys())}")
            if 'protagonist' in character_design:
                prot = character_design['protagonist']
                logger.info(f"[BatchChapterGenerator] protagonist 类型: {type(prot)}, 内容: {prot if not isinstance(prot, dict) else 'dict with keys ' + str(list(prot.keys()) if prot else 'EMPTY')}")
            if 'main_character' in character_design:
                mc = character_design['main_character']
                logger.info(f"[BatchChapterGenerator] main_character 类型: {type(mc)}")
        
        # 🔥 修复：同时支持 main_character 和 protagonist 两种字段名
        protagonist = character_design.get('main_character') or character_design.get('protagonist', {})
        
        # 提取主角名字（多种可能的位置）
        protagonist_name = (
            protagonist.get('basic_info', {}).get('name') or
            protagonist.get('name') or
            novel_data.get('protagonist_name')
        )
        
        # 🔥 关键修复：如果没有主角名字，报错而不是使用默认值
        if not protagonist_name:
            logger.error(f"[BatchChapterGenerator] 无法提取主角名字，novel_data: {novel_data}")
            raise ValueError("缺少主角名字！必须在 novel_data.character_design 中提供 protagonist.name 或 main_character.basic_info.name")
        
        current_stage = self._get_current_growth_stage(chapter_num)
        context_parts.append(f"""
【主角状态】
- 姓名：{protagonist_name}
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

## 【强制输出格式 - 使用分隔符】
必须按以下格式返回，使用 ---标题--- 和 ---正文--- 分隔：

---标题---
章节标题（8-14字，不要'第X章'前缀）
---正文---
第{chapter_num}章正文内容（2000-2500字，直接从场景开始）

⚠️ **重要警告**：
- 必须严格按照上述分隔符格式返回
- 标题只放在---标题---后面，不要重复放在正文里
- 正文开头绝对禁止写"第X章：XXX"
- 禁止在正文中包含 `---正文结束---` 等分隔符
"""
    
    def _parse_response(self, response) -> Dict:
        """
        严格解析响应，只认两种标准格式：
        1. 分隔符格式 ---标题---\n标题\n---正文---\n正文
        2. JSON 格式 {"title": "...", "content": "..."}
        非标准格式返回空title，由上层决定重试或补标题
        """
        import re
        result = {'title': '', 'content': ''}
        
        if isinstance(response, dict):
            result['title'] = response.get('title', '')
            result['content'] = response.get('content', str(response))
            return self._clean_result(result)
        
        if not isinstance(response, str):
            result['content'] = str(response)
            return self._clean_result(result)
        
        cleaned_response = response.strip()
        
        # 策略1: 分隔符格式
        title_match = re.search(r'---\s*[标標][题題]\s*---\s*\n?(.*?)\n?---\s*[正正][文文]\s*---', cleaned_response, re.DOTALL | re.IGNORECASE)
        if title_match:
            result['title'] = title_match.group(1).strip()
            # 使用正则匹配的结束位置作为内容起点，避免 find() 错位或重复标记
            content_start = title_match.end()
            result['content'] = cleaned_response[content_start:].strip()
            logger.info(f"[BatchGenerator] 分隔符格式,标题: '{result['title']}'")
            return self._clean_result(result)
        
        # 策略2: JSON 格式
        json_content = cleaned_response
        if json_content.startswith('```'):
            first_newline = json_content.find('\n')
            if first_newline != -1:
                json_content = json_content[first_newline:].strip()
            if json_content.endswith('```'):
                json_content = json_content[:-3].strip()
        
        try:
            parsed = json.loads(json_content)
            if isinstance(parsed, dict):
                # 兼容中文JSON键名
                result['title'] = parsed.get('title', '') or parsed.get('标题', '')
                result['content'] = parsed.get('content', '') or parsed.get('正文', '')
                logger.info(f"[BatchGenerator] JSON格式,标题: '{result['title']}'")
                return self._clean_result(result)
        except Exception:
            pass
        
        # 非标准格式：原样返回content，title留空，由上层处理
        result['content'] = cleaned_response
        logger.warning(f"[BatchGenerator] 响应不符合标准格式(分隔符/JSON)，title置空待补")
        return self._clean_result(result)
    
    def _sanitize_chapter_content(self, content: str) -> str:
        """
        🔥 清理超长章节中的拼接/重复问题
        当字数>4000或检测到多个---正文---分隔符时，取内容最多的那段
        """
        if not content or len(content) < 500:
            return content
        
        import re
        
        # 触发条件：字数过多 或 存在多个格式分隔符
        if len(content) > 4000 or content.count('---正文---') > 1 or content.count('---标题---') > 1:
            # 策略1: 按分隔符拆分，取最长段落
            parts = re.split(r'\n?---+\s*(?:标题|正文)\s*---+\n?', content)
            parts = [p.strip() for p in parts if len(p.strip()) > 100]
            if len(parts) > 1:
                best = max(parts, key=len)
                if len(best) < len(content):
                    logger.warning(f"[BatchGenerator] 检测到正文拼接，取最长段 {len(best)} 字 / 原 {len(content)} 字")
                return best
            
            # 策略2: 段落级重复检测（后半段是前半段的复制）
            paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
            if len(paragraphs) > 50:
                first_para = paragraphs[0]
                for dup_idx in range(20, len(paragraphs) - 10):
                    if paragraphs[dup_idx] == first_para:
                        match_len = 0
                        max_check = min(dup_idx, len(paragraphs) - dup_idx)
                        for i in range(max_check):
                            if paragraphs[i] == paragraphs[dup_idx + i]:
                                match_len += 1
                            else:
                                break
                        if match_len > 30:
                            truncated = '\n'.join(paragraphs[:dup_idx])
                            logger.warning(f"[BatchGenerator] 检测到段落重复，截断为 {len(truncated)} 字 / 原 {len(content)} 字")
                            return truncated
        
        return content

    def _clean_result(self, result: Dict) -> Dict:
        """清理content中的章节号行和已知标题"""
        import re
        if result['content']:
            patterns = [
                r'^第\s*[一二三四五六七八九十百千万零\d]+\s*章[：: ]*[^\n]*\n*',
                r'^Chapter\s*\d+[：: ]*[^\n]*\n*',
                r'^Chapter\d+[：: ]*[^\n]*\n*',
            ]
            for pattern in patterns:
                result['content'] = re.sub(pattern, '', result['content'], flags=re.IGNORECASE)
            result['content'] = result['content'].lstrip('\n')
            if result.get('title'):
                escaped = re.escape(result['title'].strip())
                result['content'] = re.sub(rf'^\s*{escaped}\s*\n+', '', result['content'], count=1)
            # 钩子后硬截断，防止AI继续滑翔
            result['content'] = self._truncate_at_hook(result['content'])
        return result
    
    def _truncate_at_hook(self, content: str) -> str:
        """如果正文在钩子后继续滑翔，硬斩断"""
        glide_markers = [
            "---下一章预告---",
            "下一章预告",
            "本章完",
            "未完待续",
            "偏厅的门缓缓打开",
            "就在这时，门开了",
            "他大步走向",
            "林墨挑了挑眉",
            "林墨冷笑一声",
            "林墨淡淡道",
        ]
        # 只在内容后 15% 处寻找滑翔标记
        threshold = int(len(content) * 0.85)
        earliest_idx = -1
        for marker in glide_markers:
            idx = content.find(marker)
            if idx != -1 and idx >= threshold:
                if earliest_idx == -1 or idx < earliest_idx:
                    earliest_idx = idx
        if earliest_idx != -1:
            content = content[:earliest_idx].strip()
        return content
    
    def _call_ai_generation(self, prompt: str, chapter_num: int) -> Dict:
        """调用AI生成，格式异常时自动重试1次"""
        response = self.api_client.generate_content_with_retry(
            content_type="chapter_content",
            user_prompt=prompt,
            temperature=0.7,
            purpose=f"生成第{chapter_num}章"
        )
        result = self._parse_response(response)
        
        # 格式检查：必须有content且字数>500，title非空
        if (not result.get('content') or len(result['content']) < 500 or not result.get('title')):
            logger.warning(f"[BatchGenerator] 第{chapter_num}章格式异常，触发重试")
            retry_prompt = prompt + "\n\n⚠️ 上一次的返回格式不正确。请严格遵守以下格式：\n---标题---\n章节标题（8-14字）\n---正文---\n章节正文内容（2000-2500字）\n"
            response = self.api_client.generate_content_with_retry(
                content_type="chapter_content",
                user_prompt=retry_prompt,
                temperature=0.6,
                purpose=f"重试生成第{chapter_num}章"
            )
            result = self._parse_response(response)
        
        return result
    
    def _generate_title_from_content(self, content: str) -> str:
        """基于正文单独补生成标题"""
        if not self.api_client or not content or len(content) < 100:
            return "剧情推进"
        prompt = f"""请根据以下小说正文，生成一个8-14字的番茄风章节标题。标题要概括核心爽点，不要带"第X章"前缀。

正文片段（前800字）：
{content[:800]}

必须严格返回JSON格式：
{{"title": "章节标题"}}
"""
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="title_generation",
                user_prompt=prompt,
                temperature=0.5,
                purpose="补生成章节标题"
            )
            parsed = self._parse_response(response)
            title = parsed.get('title', '').strip()
            if title and title != '章节标题':
                return title
        except Exception as e:
            logger.warning(f"[BatchGenerator] 补生成标题失败: {e}")
        return "剧情推进"
    
    def _ensure_unique_title(self, title: str) -> str:
        """确保标题唯一，重复则加 (1), (2)..."""
        import re
        if not title:
            title = "剧情推进"
        clean_title = re.sub(r'^第\s*[一二三四五六七八九十百千万零\d]+\s*章\s*', '', title).strip()
        if not clean_title:
            clean_title = "剧情推进"
        original = clean_title
        counter = 1
        while clean_title in self._chapter_titles:
            clean_title = f"{original} ({counter})"
            counter += 1
        self._chapter_titles.add(clean_title)
        return clean_title
    
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
    
    def _extract_title(self, content: str) -> str:
        """从正文中尝试提取标题（仅作为最后一道备用）"""
        import re
        if not isinstance(content, str):
            return ""
        first_line = content.strip().split('\n')[0].strip()
        match = re.search(r'第\s*[一二三四五六七八九十百千万零\d]+\s*章[：:\s]*(.+)', first_line)
        if match:
            extracted = match.group(1).strip()
            if extracted and not extracted.startswith('【') and len(extracted) <= 40:
                return extracted
        return ""
    
    def _preload_characters_from_blueprint(self, blueprint: Dict) -> None:
        """
        从战术规划蓝图预加载新角色到 CharacterStateManager
        
        番茄细纲会话第3轮生成 character_plan，包含：
        - existing_characters: 已有角色
        - new_characters: 新角色（每批次最多2个）
        - chapter_assignments: 每章角色分配
        
        Args:
            blueprint: 战术规划蓝图
        """
        if not self.character_state_manager:
            return
        
        try:
            character_plan = blueprint.get('character_plan', {})
            if not character_plan:
                return
            
            # 1. 预加载已有角色（确保状态一致）
            existing_chars = character_plan.get('existing_characters', [])
            for char in existing_chars:
                if isinstance(char, dict) and char.get('name'):
                    self.character_state_manager.add_or_update_character(
                        char_info={
                            'name': char.get('name'),
                            'role': char.get('role', '未知'),
                            'description': char.get('description', ''),
                            'arc': char.get('arc', '')
                        },
                        char_type='neutral'  # 后续根据实际出场分类
                    )
            
            # 2. 预加载新角色（重点！）
            new_chars = character_plan.get('new_characters', [])
            for char in new_chars:
                if isinstance(char, dict) and char.get('name'):
                    char_name = char.get('name')
                    intro_chapter = char.get('intro_chapter', 0)
                    
                    self.character_state_manager.add_or_update_character(
                        char_info={
                            'name': char_name,
                            'role': char.get('role', '新角色'),
                            'description': char.get('description', f'第{intro_chapter}章出场的新角色'),
                            'introduced_chapter': intro_chapter
                        },
                        char_type='neutral'  # 初始为中立，后续根据行为分类
                    )
                    logger.info(f"[BatchGenerator] 预加载新角色: {char_name} (第{intro_chapter}章出场)")
            
            # 3. 从章节分配中提取所有涉及角色
            chapter_assignments = character_plan.get('chapter_assignments', [])
            for assignment in chapter_assignments:
                if not isinstance(assignment, dict):
                    continue
                ch_num = assignment.get('chapter', 0)
                
                # core, major, minor 都是角色列表
                for role_type in ['core', 'major', 'minor']:
                    char_names = assignment.get(role_type, [])
                    if isinstance(char_names, list):
                        for name in char_names:
                            if name and isinstance(name, str):
                                # 确保角色已注册
                                if not self.character_state_manager._find_character(name):
                                    self.character_state_manager.add_or_update_character(
                                        char_info={
                                            'name': name,
                                            'role': '规划角色',
                                            'introduced_chapter': ch_num
                                        },
                                        char_type='neutral'
                                    )
            
            if existing_chars or new_chars:
                logger.info(f"[BatchGenerator] 角色预加载完成: 已有{len(existing_chars)}个, 新增{len(new_chars)}个")
            
        except Exception as e:
            logger.error(f"[BatchGenerator] 预加载角色失败: {e}")
    
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
    
    def _repair_missing_chapters_in_range(self, novel_title: str, start_chapter: int, end_chapter: int,
                                          blueprint: Dict, tropes: Dict, novel_data: Dict,
                                          results: Dict) -> None:
        """
        🔥 批次生成结束后，扫描并自动修复缺失或损坏的章节
        """
        missing_chapters = []
        chapters_dir = self.project_path / "chapters" if self.project_path else Path("小说项目") / novel_title / "chapters"
        
        for ch_num in range(start_chapter, end_chapter + 1):
            chapter_valid = False
            for fname in [f"chapter_{ch_num:03d}.json", f"chapter_{ch_num}.json"]:
                fpath = chapters_dir / fname
                if fpath.exists():
                    try:
                        data = json.loads(fpath.read_text(encoding='utf-8'))
                        if data.get('word_count', 0) >= 100 and data.get('content', '').strip():
                            chapter_valid = True
                            break
                    except Exception:
                        pass
            if not chapter_valid:
                missing_chapters.append(ch_num)
        
        if not missing_chapters:
            return
        
        logger.warning(f"[BatchGenerator] 发现 {len(missing_chapters)} 个缺失/损坏章节: {missing_chapters}")
        
        for ch_num in missing_chapters:
            logger.info(f"[BatchGenerator] 开始修复第{ch_num}章...")
            try:
                # 尾章使用直接文本生成 fallback，避免 JSON 解析反复失败导致超时
                if ch_num >= 180:
                    chapter_plan = self._get_chapter_plan(ch_num, blueprint)
                    context = self._build_chapter_context(ch_num, novel_title, novel_data)
                    prompt = self._build_chapter_prompt(
                        chapter_num=ch_num,
                        chapter_plan=chapter_plan,
                        context=context,
                        novel_data=novel_data,
                        tropes=tropes
                    )
                    raw = self.api_client.call_api(
                        system_prompt="你是一个专业网文写手，严格按用户要求输出章节。",
                        user_prompt=prompt + "\n\n请直接以 ---标题--- 和 ---正文--- 格式返回，不需要JSON。",
                        temperature=0.7,
                        purpose=f"直接生成第{ch_num}章"
                    )
                    parsed = self._parse_response(raw)
                    if not parsed.get('title') and parsed.get('content'):
                        lines = parsed['content'].strip().split('\n')
                        parsed['title'] = lines[0].strip() if lines else f"第{ch_num}章"
                        parsed['content'] = '\n'.join(lines[1:]).strip() if len(lines) > 1 else parsed['content']
                    chapter = {
                        "chapter_number": ch_num,
                        "title": parsed.get('title', f"第{ch_num}章"),
                        "content": parsed.get('content', ''),
                        "word_count": len(parsed.get('content', '')),
                        "quality_score": 7.0,
                        "chapter_plan": chapter_plan,
                        "generated_at": datetime.now().isoformat()
                    }
                else:
                    chapter = self._generate_single_chapter(
                        chapter_num=ch_num,
                        novel_title=novel_title,
                        blueprint=blueprint,
                        tropes=tropes,
                        novel_data=novel_data
                    )
                
                self._save_chapter(novel_title, chapter)
                
                # 更新 results
                results["generated"].append({
                    "chapter_number": ch_num,
                    "chapter": ch_num,
                    "title": chapter.get("title", ""),
                    "word_count": chapter.get("word_count", 0),
                    "quality_score": chapter.get("quality_score", 8.0),
                })
                results["total_words"] += chapter.get("word_count", 0)
                
                # 移除之前标记的 failed
                results["failed"] = [f for f in results["failed"] if f.get("chapter") != ch_num]
                
                logger.info(f"[BatchGenerator] ✅ 第{ch_num}章修复完成 ({chapter.get('word_count', 0)}字)")
            except Exception as e:
                logger.error(f"[BatchGenerator] ❌ 第{ch_num}章修复失败: {e}", exc_info=True)
                if not any(f.get("chapter") == ch_num for f in results["failed"]):
                    results["failed"].append({
                        "chapter_number": ch_num,
                        "chapter": ch_num,
                        "error": str(e)
                    })
        
        # 重新计算平均质量
        if results["generated"]:
            results["avg_quality"] = sum(c.get("quality_score", 8.0) for c in results["generated"]) / len(results["generated"])
    
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
            tropes: 爆款分析
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
    
    # 🔥 金手指可能嵌套在 plan 中（对话模式产物结构）
    golden_finger = products.get("golden_finger") or products.get("plan", {}).get("golden_finger", {})
    
    novel_data = {
        "title": novel_title,
        "username": username,
        "_username": username,
        "genre": genre,
        "core_worldview": products.get("core_worldview", {}),
        "character_design": character_design,
        "faction_system": products.get("faction_system", {}),
        "plan": products.get("plan", {}),
        "golden_finger": golden_finger,
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
