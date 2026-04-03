# -*- coding: utf-8 -*-
"""
BatchSummarizer - 批次总结器
每6章生成一次总结报告，用于下一轮规划和状态跟踪
"""

import json
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BatchSummarizer:
    """
    批次总结器
    
    功能：
    1. 分析每批次生成的章节内容
    2. 提取关键事件、角色状态、剧情进展
    3. 生成结构化总结报告
    4. 支持多批次总结合并
    """
    
    # 配置路径
    CONFIG_PATH = "prompt_packages/default/market_driven/components/batch_summary_prompts.json"
    
    def __init__(self, api_client=None, analytics_service=None):
        self.api_client = api_client
        self.analytics_service = analytics_service  # 🔥 新增：接入真实质量分析服务
        self._config = self._load_config()
        self._emotion_quality_config = self._load_emotion_quality_config()
    
    def _load_config(self) -> Dict:
        """加载提示词配置"""
        try:
            from pathlib import Path
            config_path = Path(self.CONFIG_PATH)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"[BatchSummarizer] 无法加载配置: {e}")
            return {}
    
    def _load_emotion_quality_config(self) -> Dict:
        """🔥 加载情绪质量标准配置"""
        try:
            from pathlib import Path
            config_path = Path("prompt_packages/default/market_driven/components/emotion_quality_standards.json")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"[BatchSummarizer] 无法加载情绪质量标准配置: {e}")
            return {}
    
    def summarize_batch(
        self,
        chapters: List[Dict],
        stage_goal: Dict = None,
        previous_summary: Dict = None
    ) -> Dict:
        """
        总结批次内容（AI增强版）
        
        使用AI分析章节内容，生成深度总结，用于：
        1. 传递给下一批次的 TacticalPlanner
        2. 保持跨会话的剧情连贯性
        3. 追踪阶段目标完成度
        
        Args:
            chapters: 章节数据列表
            stage_goal: 当前阶段目标
            previous_summary: 前序总结（用于累积）
            
        Returns:
            总结字典
        """
        if not chapters:
            return self._empty_summary()
        
        # 🔥 过滤掉 None 元素
        chapters = [c for c in chapters if c is not None]
        if not chapters:
            logger.warning("[BatchSummarizer] 所有章节数据均为None")
            return self._empty_summary()
        
        try:
            # 🔥 修复：兼容两种字段名（chapter_number 和 chapter）
            chapter_nums = []
            for c in chapters:
                ch_num = c.get('chapter_number') or c.get('chapter') or 0
                if ch_num:
                    chapter_nums.append(ch_num)
            
            start_ch = min(chapter_nums) if chapter_nums else 0
            end_ch = max(chapter_nums) if chapter_nums else 0
            
            # 🔥 基础统计 - 使用真实质量数据（如果analytics_service可用）
            total_words = sum(c.get('word_count', 0) for c in chapters)
            
            # 尝试获取真实质量分析
            real_quality_metrics = self._analyze_real_quality(chapters)
            if real_quality_metrics:
                # 使用真实质量数据
                avg_quality = sum(m['tomato_score'] for m in real_quality_metrics) / len(real_quality_metrics)
                logger.info(f"[BatchSummarizer] 使用真实质量数据: 平均得分{avg_quality:.1f}")
            else:
                # 降级：使用章节自带的quality_score
                avg_quality = sum(c.get('quality_score', 0) for c in chapters) / len(chapters) if chapters else 0
                logger.warning(f"[BatchSummarizer] 使用章节自带质量分（可能不准确）: {avg_quality:.1f}")
            
            # 收集提取信息
            all_new_chars = []
            all_char_changes = []
            all_hooks = []
            key_events = []
            
            for ch in chapters:
                extracted = ch.get('extracted_info', {}) or {}
                
                # 新角色
                new_chars = extracted.get('new_characters') or []
                for char in new_chars:
                    if char not in all_new_chars:
                        all_new_chars.append(char)
                
                # 角色变化
                changes = extracted.get('character_changes') or []
                all_char_changes.extend(changes)
                
                # 钩子
                hooks = extracted.get('new_hooks') or []
                all_hooks.extend(hooks)
                
                # 关键事件
                key_event = extracted.get('key_event')
                if key_event:
                    key_events.append({
                        **key_event,
                        "chapter": ch.get('chapter_number')
                    })
            
            # 🔥 AI 深度分析
            ai_analysis = self._ai_analyze_batch(
                chapters, stage_goal, previous_summary,
                all_new_chars, all_char_changes, key_events
            )
            
            # 计算阶段目标进度
            goal_id = stage_goal.get('goal_id', 'G1') if stage_goal else 'G1'
            goal_name = stage_goal.get('name', '未知目标') if stage_goal else '未知'
            progress = self._calculate_goal_progress(chapters, stage_goal, previous_summary)
            
            summary = {
                "batch_range": f"{start_ch}-{end_ch}",
                "chapter_count": len(chapters),
                "total_words": total_words,
                "average_quality": round(avg_quality, 1),
                "generated_at": datetime.now().isoformat(),
                
                # 阶段目标进度
                "current_goal": {
                    "goal_id": goal_id,
                    "goal_name": goal_name,
                    "progress_percent": progress
                },
                "goal_progress": {goal_id: f"{progress}%"},
                
                # 内容摘要
                "content": {
                    "new_characters": all_new_chars,
                    "new_characters_count": len(all_new_chars),
                    "character_changes": all_char_changes,
                    "character_changes_count": len(all_char_changes),
                    "new_hooks": all_hooks,
                    "hooks_count": len(all_hooks),
                    "key_events": key_events,
                    "key_events_count": len(key_events)
                },
                
                # 🔥 AI 分析结果
                "ai_analysis": ai_analysis,
                
                # 角色状态快照
                "character_state": ai_analysis.get('character_states', {}) or self._extract_character_state(chapters),
                
                # 用于传递的关键信息
                "completed_events": ai_analysis.get('completed_events', []),
                "pending_hooks": ai_analysis.get('pending_hooks', all_hooks[:5]),
                "plot_direction": ai_analysis.get('plot_direction', ''),
                
                # 备注
                "notes": ai_analysis.get('summary_text', f"第{start_ch}-{end_ch}章批次总结完成")
            }
            
            logger.info(f"[BatchSummarizer] 批次总结完成: 第{start_ch}-{end_ch}章, "
                       f"新角色{len(all_new_chars)}人, 关键事件{len(key_events)}个, "
                       f"目标进度{progress}%")
            
            return summary
            
        except Exception as e:
            logger.error(f"[BatchSummarizer] 生成批次总结时出错: {e}")
            # 🔥 返回基础总结，确保不返回None
            return {
                "batch_range": f"{start_ch}-{end_ch}" if 'start_ch' in dir() else "unknown",
                "chapter_count": len(chapters),
                "total_words": sum(c.get('word_count', 0) for c in chapters),
                "average_quality": 0,
                "current_goal": {"goal_id": "", "goal_name": "", "progress_percent": 0},
                "goal_progress": {},
                "content": {
                    "new_characters": [],
                    "new_characters_count": 0,
                    "character_changes": [],
                    "character_changes_count": 0,
                    "new_hooks": [],
                    "hooks_count": 0,
                    "key_events": [],
                    "key_events_count": 0
                },
                "character_state": {},
                "notes": f"批次总结生成失败: {str(e)}",
                "error": str(e)
            }
    
    def _ai_analyze_batch(
        self,
        chapters: List[Dict],
        stage_goal: Dict,
        previous_summary: Dict,
        new_chars: List[Dict],
        char_changes: List[Dict],
        key_events: List[Dict]
    ) -> Dict:
        """
        使用AI深度分析批次内容
        
        生成用于下批次规划的关键信息。
        """
        if not self.api_client:
            return {
                "summary_text": "无API客户端，使用基础统计",
                "character_states": {},
                "completed_events": [],
                "pending_hooks": [],
                "plot_direction": ""
            }
        
        # 构建分析提示词
        start_ch = min(c.get('chapter_number', 0) for c in chapters)
        end_ch = max(c.get('chapter_number', 0) for c in chapters)
        
        # 提取关键内容（每章前500字）
        chapter_snippets = []
        for ch in chapters:
            content = ch.get('content', '')[:500]
            ch_num = ch.get('chapter_number', 0)
            chapter_snippets.append(f"第{ch_num}章摘要: {content}...")
        
        goal_desc = stage_goal.get('description', '完成当前阶段目标') if stage_goal else '推进剧情'
        
        # 🔥 从JSON配置加载模板
        template_config = self._config.get("summary_template", {})
        template = template_config.get("template", "")
        
        if not template:
            error_msg = """
❌ 错误：批次总结提示词配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/components/batch_summary_prompts.json
"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        prompt = template.format(
            start_ch=start_ch,
            end_ch=end_ch,
            goal_desc=goal_desc,
            chapter_snippets=chr(10).join(chapter_snippets),
            new_chars_count=len(new_chars),
            new_chars_list=', '.join(c.get('name', '') for c in new_chars[:3]),
            char_changes_count=len(char_changes),
            key_events_count=len(key_events)
        )
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="batch_summary_analysis",
                user_prompt=prompt,
                temperature=0.7,
                purpose=f"批次分析-{start_ch}-{end_ch}"
            )
            
            # 解析JSON响应
            import re
            if isinstance(response, dict):
                return response
            elif isinstance(response, str):
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    return json.loads(json_match.group())
            
            logger.warning("[BatchSummarizer] AI分析返回格式异常，使用基础数据")
            
        except Exception as e:
            logger.error(f"[BatchSummarizer] AI分析失败: {e}")
        
        # 返回默认结构
        return {
            "summary_text": f"第{start_ch}-{end_ch}章剧情推进完成",
            "character_states": {},
            "completed_events": key_events[:3],
            "pending_hooks": [],
            "plot_direction": "继续推进当前阶段目标",
            "stage_progress_assessment": "阶段进行中"
        }
    
    def _analyze_real_quality(self, chapters: List[Dict]) -> List[Dict]:
        """
        🔥 使用ChapterAnalyticsService分析真实质量
        
        Returns:
            各章节的真实质量指标列表
        """
        if not self.analytics_service:
            return []
        
        metrics_list = []
        for ch in chapters:
            ch_num = ch.get('chapter_number') or ch.get('chapter') or 0
            if not ch_num:
                continue
            
            try:
                # 调用真实质量分析
                metrics = self.analytics_service.analyze_chapter(ch_num)
                if metrics:
                    # 获取章节规划的情绪类型
                    chapter_plan = ch.get('chapter_plan', {})
                    planned_emotion = chapter_plan.get('emotion', '未知')
                    
                    # 对比规划情绪和实际质量
                    quality_check = self._check_emotion_quality(
                        planned_emotion, 
                        metrics,
                        ch.get('content', '')
                    )
                    
                    metrics_list.append({
                        'chapter_num': ch_num,
                        'title': ch.get('title', ''),
                        'tomato_score': metrics.get('tomato_score', 0),
                        'dialogue_ratio': metrics.get('dialogue_ratio', 0),
                        'shuang_density': metrics.get('shuang_density', 0),
                        'emotion_density': metrics.get('emotion_density', 0),
                        'has_cliffhanger': metrics.get('has_cliffhanger', False),
                        'planned_emotion': planned_emotion,
                        'quality_check': quality_check,
                        'passed': quality_check.get('passed', False)
                    })
            except Exception as e:
                logger.error(f"[BatchSummarizer] 分析第{ch_num}章质量失败: {e}")
        
        return metrics_list
    
    def _check_emotion_quality(self, emotion: str, metrics: Dict, content: str) -> Dict:
        """
        🔥 检查章节质量是否符合情绪类型的标准
        """
        standards = self._emotion_quality_config.get('emotion_standards', {})
        emotion_std = standards.get(emotion, {})
        
        if not emotion_std:
            return {'passed': True, 'issues': [], 'notes': '无该情绪类型标准'}
        
        issues = []
        
        # 检查对话比例
        min_dialogue = emotion_std.get('min_dialogue_ratio', 40)
        dialogue_ratio = metrics.get('dialogue_ratio', 0)
        if dialogue_ratio < min_dialogue:
            issues.append({
                'type': 'low_dialogue',
                'message': f"对话比例{dialogue_ratio:.1f}%低于标准{min_dialogue}%",
                'severity': 'warning'
            })
        
        # 检查番茄得分
        min_score = emotion_std.get('min_tomato_score', 60)
        tomato_score = metrics.get('tomato_score', 0)
        if tomato_score < min_score:
            issues.append({
                'type': 'low_score',
                'message': f"番茄得分{tomato_score:.1f}低于标准{min_score}",
                'severity': 'critical'
            })
        
        # 检查情绪密度
        min_emotion_density = emotion_std.get('min_emotion_density', 1.5)
        emotion_density = metrics.get('emotion_density', 0)
        if emotion_density < min_emotion_density:
            issues.append({
                'type': 'low_emotion_density',
                'message': f"情绪密度{emotion_density:.2f}低于标准{min_emotion_density}",
                'severity': 'warning'
            })
        
        # 检查爽点密度
        min_shuang = emotion_std.get('min_shuang_density', 1.0)
        shuang_density = metrics.get('shuang_density', 0)
        if shuang_density < min_shuang:
            issues.append({
                'type': 'low_shuang_density',
                'message': f"爽点密度{shuang_density:.2f}低于标准{min_shuang}",
                'severity': 'info'
            })
        
        # 检查必含元素
        required_elements = emotion_std.get('required_elements', [])
        missing_elements = []
        for element in required_elements:
            # 简化检查：在内容中查找关键词
            if element == '弹幕反应' and '【' not in content:
                missing_elements.append(element)
            elif element == '系统希望提示' and '系统提示' not in content:
                missing_elements.append(element)
        
        if missing_elements:
            issues.append({
                'type': 'missing_elements',
                'message': f"缺少必含元素: {', '.join(missing_elements)}",
                'severity': 'warning'
            })
        
        return {
            'passed': len([i for i in issues if i['severity'] == 'critical']) == 0,
            'issues': issues,
            'standards': {
                'min_dialogue': min_dialogue,
                'min_score': min_score,
                'min_emotion_density': min_emotion_density,
                'min_shuang': min_shuang
            }
        }
    
    def _empty_summary(self) -> Dict:
        """返回空总结"""
        return {
            "batch_range": "",
            "chapter_count": 0,
            "total_words": 0,
            "average_quality": 0,
            "current_goal": {"goal_id": "", "goal_name": "", "progress_percent": 0},
            "goal_progress": {},
            "content": {
                "new_characters": [],
                "new_characters_count": 0,
                "character_changes": [],
                "character_changes_count": 0,
                "new_hooks": [],
                "hooks_count": 0,
                "key_events": [],
                "key_events_count": 0
            },
            "character_state": {},
            "notes": "空总结"
        }
    
    def _calculate_goal_progress(
        self, 
        chapters: List[Dict], 
        stage_goal: Dict,
        previous_summary: Dict
    ) -> int:
        """
        计算阶段目标进度
        
        基于：
        1. 已生成章节数占总章节比例
        2. 关键事件完成情况
        3. 前序进度累积
        """
        if not chapters:
            return 0
        
        # 基础进度（基于章节数）
        chapter_nums = [c.get('chapter_number', 0) for c in chapters]
        max_ch = max(chapter_nums) if chapter_nums else 0
        
        # 估算该阶段覆盖的章节范围（假设每个阶段约30-50章）
        stage_estimate = 40  # 每阶段约40章
        base_progress = min(int(max_ch / stage_estimate * 100), 100)
        
        # 如果有前序总结，累积进度
        if previous_summary:
            prev_progress_str = previous_summary.get('goal_progress', {}).get(
                stage_goal.get('goal_id', 'G1'), '0%'
            )
            try:
                prev_progress = int(prev_progress_str.replace('%', ''))
                # 增量更新（每批约增加10-15%）
                progress = min(prev_progress + 10, base_progress)
            except:
                progress = base_progress
        else:
            progress = base_progress
        
        return min(progress, 100)
    
    def _extract_character_state(self, chapters: List[Dict]) -> Dict:
        """提取角色状态快照"""
        state = {
            "protagonist": {},
            "allies": [],
            "enemies": []
        }
        
        if not chapters:
            return state
        
        # 取最后一章的提取信息作为当前状态
        last_ch = chapters[-1]
        extracted = last_ch.get('extracted_info', {})
        
        # 从角色变化中提取主角状态
        char_changes = extracted.get('character_changes', [])
        for change in char_changes:
            # 假设第一个变化通常是主角
            state['protagonist'] = {
                "name": change.get('name', '主角'),
                "status": change.get('change', ''),
                "details": change.get('details', '')
            }
            break
        
        # 新角色分类
        new_chars = extracted.get('new_characters', [])
        for char in new_chars:
            role = char.get('role', '')
            char_info = {
                "name": char.get('name', ''),
                "role": role,
                "power_level": char.get('power_level', '')
            }
            
            if '敌' in role or '反' in role or 'villain' in role.lower():
                state['enemies'].append(char_info)
            elif '友' in role or '盟' in role or 'ally' in role.lower():
                state['allies'].append(char_info)
        
        return state
    
    def merge_summaries(self, old_summary: Dict, new_summary: Dict) -> Dict:
        """
        合并两个总结（累积多批次信息）
        
        Args:
            old_summary: 旧总结
            new_summary: 新总结
            
        Returns:
            合并后的总结
        """
        if not old_summary:
            return new_summary
        if not new_summary:
            return old_summary
        
        merged = old_summary.copy()
        
        # 更新批次范围
        old_range = old_summary.get('batch_range', '').split('-')
        new_range = new_summary.get('batch_range', '').split('-')
        
        if len(old_range) == 2 and len(new_range) == 2:
            try:
                start = min(int(old_range[0]), int(new_range[0]))
                end = max(int(old_range[1]), int(new_range[1]))
                merged['batch_range'] = f"{start}-{end}"
            except:
                merged['batch_range'] = new_summary.get('batch_range', '')
        
        # 累积统计
        merged['chapter_count'] = old_summary.get('chapter_count', 0) + new_summary.get('chapter_count', 0)
        merged['total_words'] = old_summary.get('total_words', 0) + new_summary.get('total_words', 0)
        
        # 平均质量（加权平均）
        old_count = old_summary.get('chapter_count', 0)
        new_count = new_summary.get('chapter_count', 0)
        total_count = old_count + new_count
        if total_count > 0:
            old_quality = old_summary.get('average_quality', 0) * old_count
            new_quality = new_summary.get('average_quality', 0) * new_count
            merged['average_quality'] = round((old_quality + new_quality) / total_count, 1)
        
        # 合并内容列表
        old_content = old_summary.get('content', {})
        new_content = new_summary.get('content', {})
        
        # 合并新角色（去重）
        all_chars = {c.get('name'): c for c in old_content.get('new_characters', [])}
        for char in new_content.get('new_characters', []):
            name = char.get('name')
            if name and name not in all_chars:
                all_chars[name] = char
        merged['content']['new_characters'] = list(all_chars.values())
        merged['content']['new_characters_count'] = len(all_chars)
        
        # 合并角色变化
        merged['content']['character_changes'] = (
            old_content.get('character_changes', []) + 
            new_content.get('character_changes', [])
        )
        merged['content']['character_changes_count'] = len(merged['content']['character_changes'])
        
        # 合并钩子
        merged['content']['new_hooks'] = (
            old_content.get('new_hooks', []) + 
            new_content.get('new_hooks', [])
        )
        merged['content']['hooks_count'] = len(merged['content']['new_hooks'])
        
        # 合并关键事件
        merged['content']['key_events'] = (
            old_content.get('key_events', []) + 
            new_content.get('key_events', [])
        )
        merged['content']['key_events_count'] = len(merged['content']['key_events'])
        
        # 合并进度（取最新）
        old_progress = old_summary.get('goal_progress', {})
        new_progress = new_summary.get('goal_progress', {})
        merged['goal_progress'] = {**old_progress, **new_progress}
        
        # 更新当前目标
        merged['current_goal'] = new_summary.get('current_goal', old_summary.get('current_goal', {}))
        
        # 更新时间
        merged['updated_at'] = datetime.now().isoformat()
        merged['notes'] = f"累积总结: 第{merged['batch_range']}章, 共{merged['chapter_count']}章"
        
        logger.info(f"[BatchSummarizer] 总结合并完成: 累积{merged['chapter_count']}章")
        
        return merged
